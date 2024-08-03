import datetime
import json
import logging
import re
import signal
import sys
import threading
from datetime import timezone

from modpoll.arg_parser import get_parser
from modpoll.modbus_task import (
    modbus_close,
    modbus_export,
    modbus_poll,
    modbus_publish,
    modbus_publish_diagnostics,
    modbus_setup,
    modbus_write_coil,
    modbus_write_register,
)
from modpoll.mqtt_task import mqttc_close, mqttc_receive, mqttc_setup

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
    print(
        f"\nModpoll v{__version__} - A New Command-line Tool for Modbus and MQTT\n",
        flush=True,
    )

    signal.signal(signal.SIGINT, _signal_handler)

    # parse args
    args = get_parser().parse_args()
    # sanity check
    if args.mqtt_topic_prefix.endswith("/"):
        args.mqtt_topic_prefix = args.mqtt_topic_prefix[:-1]

    # get logger
    setup_logging(args.loglevel, LOG_SIMPLE)
    global logger
    logger = logging.getLogger(__name__)

    # setup mqtt
    if args.mqtt_host:
        logger.info(f"Setup MQTT connection to {args.mqtt_host}")
        if not mqttc_setup(args):
            logger.error("Failed to setup MQTT client")
            mqttc_close()
            exit(1)
    else:
        logger.info("No MQTT host specified, skip MQTT setup.")

    # setup modbus
    if not modbus_setup(args, event_exit):
        logger.error("Failed to setup modbus client(master)")
        modbus_close()
        mqttc_close()
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
                f" ====== modpoll polling at rate:{args.rate}s, actual:{elapsed}s ======"
            )
            modbus_poll()
            if event_exit.is_set():
                break
            if args.mqtt_host:
                if args.timestamp:
                    modbus_publish(timestamp=now)
                else:
                    modbus_publish()
            if args.export:
                if args.timestamp:
                    modbus_export(args.export, timestamp=now)
                else:
                    modbus_export(args.export)
        if args.diagnostics_rate > 0 and now > last_diag + args.diagnostics_rate:
            last_diag = now
            modbus_publish_diagnostics()
        if event_exit.is_set():
            break
        # Check if receive mqtt request
        topic, payload = mqttc_receive()
        if topic and payload:
            device_name = re.search(
                f"^{args.mqtt_topic_prefix}([^/\n]*)/set", topic
            ).group(1)
            if device_name:
                try:
                    reg = json.loads(payload)
                    if "coil" == reg["object_type"]:
                        if modbus_write_coil(device_name, reg["address"], reg["value"]):
                            logger.info("")
                    elif "holding_register" == reg["object_type"]:
                        modbus_write_register(device_name, reg["address"], reg["value"])
                except json.decoder.JSONDecodeError:
                    logger.warning(f"Failed to parse json message: {payload}")
        if args.once:
            event_exit.set()
            break
    modbus_close()
    mqttc_close()


if __name__ == "__main__":
    app()
