import datetime
import json
import logging
import re
import signal
import sys
import threading
import time
from datetime import timezone

from .arg_parser import get_parser
from .mqtt_task import MqttHandler
from .modbus_task import ModbusMaster

from . import __version__

LOG_SIMPLE = "%(asctime)s | %(levelname).1s | %(name)s | %(message)s"
logger = None
event_exit = threading.Event()


def setup_logging(level, format):
    logging.basicConfig(level=level, format=format)


def _signal_handler(signal, frame):
    logger.info(f"Exiting {sys.argv[0]}")
    event_exit.set()


def get_utc_time():
    dt = datetime.datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    return utc_time.timestamp()


def app(name="modpoll"):
    mqtt_handler = None
    modbus_masters = []

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
        args.mqtt_publish_topic_pattern = f"{args.mqtt_topic_prefix}/<device_name>"
        args.mqtt_subscribe_topic_pattern = f"{args.mqtt_topic_prefix}/#/set"

    # setup mqtt
    if not args.mqtt_host:
        logger.info("No MQTT host specified, skip MQTT setup.")
    else:
        logger.info(f"Setup MQTT connection to {args.mqtt_host}:{args.mqtt_port}")
        try:
            mqtt_handler = MqttHandler(
                "MQTT_TASK",
                args.mqtt_host,
                args.mqtt_port,
                args.mqtt_user,
                args.mqtt_pass,
                args.mqtt_clientid,
                args.mqtt_qos,
                subscribe_topics=args.mqtt_subscribe_topic_pattern,
            )
            if mqtt_handler.mqttc_setup() and mqtt_handler.mqttc_connect():
                logger.info("Setup MQTT client.")
            else:
                logger.error("Failed to setup MQTT client, exiting...")
                mqtt_handler.mqttc_close()
                exit(1)
        except Exception as e:
            logger.error(f"Error setting up MQTT input: {e}, exiting...")
            mqtt_handler.mqttc_close()
            exit(1)

    # setup modbus tasks
    for config_file in args.config:
        modbus_master = ModbusMaster(args, event_exit, config_file, mqtt_handler)
        if modbus_master.setup():
            modbus_masters.append(modbus_master)
        else:
            modbus_master.close()
    if modbus_masters:
        logger.info(f"Start polling devices after {args.delay} second(s) delay.")
        time.sleep(args.delay)
    else:
        logger.error("No Modbus master (client) defined. Exiting...")
        if mqtt_handler:
            mqtt_handler.mqttc_close()
        exit(1)

    # main loop
    last_check = 0
    last_diag = 0
    while not event_exit.is_set():
        now = get_utc_time()
        # routine check
        if now > last_check + args.rate:
            if last_check == 0:
                elapsed = args.rate
            else:
                elapsed = round(now - last_check, 6)
            last_check = now
            logger.info(
                f" ====== Modpoll is polling at rate:{args.rate}s, actual:{elapsed}s ======"
            )
            for modbus_master in modbus_masters:
                modbus_master.poll()
                if event_exit.is_set():
                    break
                if args.mqtt_host:
                    if args.timestamp:
                        modbus_master.publish(timestamp=now)
                    else:
                        modbus_master.publish()
                if args.export:
                    if args.timestamp:
                        modbus_master.export(args.export, timestamp=now)
                    else:
                        modbus_master.export(args.export)
        if args.diagnostics_rate > 0 and now > last_diag + args.diagnostics_rate:
            last_diag = now
            for modbus_master in modbus_masters:
                modbus_master.publish_diagnostics()
        if event_exit.is_set():
            break
        # Check if receive mqtt request
        if mqtt_handler:
            topic, payload = mqtt_handler.mqttc_receive()
            if topic and payload:
                # extract device_name
                topic_regex = args.mqtt_subscribe_topic_pattern.replace(
                    "#", "([^/\n]*)"
                )
                device_name = re.search(topic_regex, topic).group(1)
                if device_name:
                    logger.info(
                        f"Received request to write data for device {device_name}"
                    )
                    try:
                        reg = json.loads(payload)
                        object_type = reg["object_type"]
                        address = reg["address"]
                        value = reg["value"]
                        for modbus_master in modbus_masters:
                            if device_name in [
                                dev.name for dev in modbus_master.get_device_list()
                            ]:
                                if "coil" == object_type:
                                    if modbus_master.write_coil(
                                        device_name, address, value
                                    ):
                                        logger.info(
                                            f"Successfully write coil(s): device={device_name}, address={address}, value={value}"
                                        )
                                    else:
                                        logger.warning(
                                            f"Failed to write coil(s): device={device_name}, address={address}, value={value}"
                                        )
                                elif "holding_register" == object_type:
                                    if modbus_master.write_register(
                                        device_name, address, value
                                    ):
                                        logger.info(
                                            f"Successfully write register(s): device={device_name}, address={address}, value={value}"
                                        )
                                    else:
                                        logger.warning(
                                            f"Failed to write register(s): device={device_name}, address={address}, value={value}"
                                        )
                                break
                    except KeyError:
                        logger.error(f"No required key found: {payload}")
                    except json.decoder.JSONDecodeError:
                        logger.error(f"Failed to parse json message: {payload}")
        if args.once:
            event_exit.set()
            break

        time.sleep(0.01)

    for modbus_master in modbus_masters:
        modbus_master.close()
    if mqtt_handler:
        mqtt_handler.mqttc_close()


if __name__ == "__main__":
    app()
