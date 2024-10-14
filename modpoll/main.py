import json
import logging
import re
import signal
import sys

from .arg_parser import get_parser
from .mqtt_task import MqttHandler
from .modbus_task import setup_modbus_handlers

from . import __version__
from .utils import set_threading_event, delay_thread, on_threading_event, get_utc_time


LOG_SIMPLE = "%(asctime)s | %(levelname).1s | %(name)s | %(message)s"
logger = None


def _signal_handler(signal, frame):
    logger.info(f"Exiting {sys.argv[0]}")
    set_threading_event()


def setup_logging(level, format):
    logging.basicConfig(level=level, format=format)


def app(name="modpoll"):
    mqtt_handler = None
    modbus_handlers = []

    print(
        f"\nModpoll v{__version__} - A New Command-line Tool for Modbus and MQTT\n",
        flush=True,
    )

    signal.signal(signal.SIGINT, _signal_handler)

    # parse args
    args = get_parser().parse_args()

    # get logger
    setup_logging(args.loglevel, LOG_SIMPLE)
    global logger
    logger = logging.getLogger(__name__)

    # Overwrite topic pattern if topic prefix is specified for backward compatibility
    if args.mqtt_topic_prefix:
        logger.warning(
            "(DEPRECATED): The `--mqtt-topic-prefix` argument is deprecated and will be removed in the future release. Use `--mqtt-publish-topic-pattern` and `--mqtt-subscribe-topic-pattern` instead. If both are used, `--mqtt-topic-prefix` argument will take precedence in order to keep backward compatibility."
        )
        if args.mqtt_topic_prefix.endswith("/"):
            args.mqtt_topic_prefix = args.mqtt_topic_prefix[:-1]
        args.mqtt_publish_topic_pattern = f"{args.mqtt_topic_prefix}/{{device_name}}"
        args.mqtt_subscribe_topic_pattern = f"{args.mqtt_topic_prefix}/#/set"

    # setup mqtt
    if not args.mqtt_host:
        logger.info("No MQTT host specified, skip MQTT setup.")
    else:
        logger.info(f"Setup MQTT connection to {args.mqtt_host}:{args.mqtt_port}")
        try:
            mqtt_handler = MqttHandler(
                "MqttHandler",
                args.mqtt_host,
                args.mqtt_port,
                args.mqtt_user,
                args.mqtt_pass,
                args.mqtt_clientid,
                args.mqtt_qos,
                subscribe_topics=[args.mqtt_subscribe_topic_pattern],
                log_level=args.loglevel,
            )
            if mqtt_handler.setup() and mqtt_handler.connect():
                logger.info("Connected to MQTT broker.")
            else:
                logger.error("Failed to connect with MQTT broker, exiting...")
                mqtt_handler.close()
                exit(1)
        except Exception as e:
            logger.error(f"Error setting up MQTT input: {e}, exiting...")
            mqtt_handler.close()
            exit(1)

    # setup modbus tasks
    modbus_handlers = setup_modbus_handlers(args, mqtt_handler)
    if modbus_handlers:
        logger.info(f"Loaded {len(modbus_handlers)} Modbus config(s).")
        delay_thread(args.delay)
    else:
        logger.error("No Modbus config(s) defined. Exiting...")
        if mqtt_handler:
            mqtt_handler.close()
        exit(1)

    # main loop
    last_check = 0
    last_diag = 0
    while not on_threading_event():
        now = get_utc_time()
        # routine check
        if now > last_check + args.rate:
            if last_check == 0:
                elapsed = args.rate
            else:
                elapsed = round(now - last_check, 6)
            last_check = now
            logger.info(
                f" === Modpoll is polling at rate:{args.rate}s, actual:{elapsed}s ==="
            )
            for modbus_handler in modbus_handlers:
                modbus_handler.poll()
                if on_threading_event():
                    break
                if args.mqtt_host:
                    if args.timestamp:
                        modbus_handler.publish_data(timestamp=now)
                    else:
                        modbus_handler.publish_data()
                if args.export:
                    if args.timestamp:
                        modbus_handler.export(args.export, timestamp=now)
                    else:
                        modbus_handler.export(args.export)
        if args.diagnostics_rate > 0 and now > last_diag + args.diagnostics_rate:
            last_diag = now
            for modbus_handler in modbus_handlers:
                modbus_handler.publish_diagnostics()
        if on_threading_event():
            break
        # Check if receive mqtt request
        if mqtt_handler:
            topic, payload = mqtt_handler.receive()
            if topic and payload:
                # extract device_name
                topic_regex = args.mqtt_subscribe_topic_pattern.replace(
                    "+", "([^/\n]*)"
                )
                match = re.search(topic_regex, topic)
                if match:
                    device_name = match.group(1)
                    logger.info(
                        f"Received request to write data for device {device_name}"
                    )
                    try:
                        reg = json.loads(payload)
                        object_type = reg["object_type"]
                        address = reg["address"]
                        value = reg["value"]

                        device_found = False
                        for modbus_handler in modbus_handlers:
                            if device_name in [
                                dev.name for dev in modbus_handler.get_device_list()
                            ]:
                                device_found = True
                                write_success = False
                                if object_type == "coil":
                                    write_success = modbus_handler.write_coil(
                                        device_name, address, value
                                    )
                                elif object_type == "holding_register":
                                    write_success = modbus_handler.write_register(
                                        device_name, address, value
                                    )

                                if write_success:
                                    logger.info(
                                        f"Successfully wrote {object_type}: device={device_name}, address={address}, value={value}"
                                    )
                                else:
                                    logger.warning(
                                        f"Failed to write {object_type}: device={device_name}, address={address}, value={value}"
                                    )
                                break

                        if not device_found:
                            logger.error(f"No device found with name: {device_name}")

                    except KeyError as e:
                        logger.error(f"Missing required key in payload: {e}")
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON message: {payload}")
                else:
                    logger.error(f"Failed to extract device name from topic: {topic}")
        if args.once:
            set_threading_event()
            break

        delay_thread(0.01)

    for modbus_handler in modbus_handlers:
        modbus_handler.close()
    if mqtt_handler:
        mqtt_handler.close()


if __name__ == "__main__":
    app()
