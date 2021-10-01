import logging
import threading
import time
import sys
import signal

from modpoll.arg_parser import get_parser
from modpoll.mqtt_task import mqttc_setup, mqttc_close
from modpoll.modbus_task import modbus_setup, modbus_poll, modbus_publish, modbus_publish_diagnostics, modbus_export, modbus_close

# global objects
event_exit = threading.Event()

# logging format
LOG_SIMPLE = "%(asctime)s | %(levelname).1s | %(name)s | %(message)s"
log = None


def _signal_handler(signal, frame):
    log.info(f'Exiting {sys.argv[0]}')
    event_exit.set()


def app(name="modpoll"):
    signal.signal(signal.SIGINT, _signal_handler)

    # parse args
    args = get_parser().parse_args()

    # get logger
    logging.basicConfig(level=args.loglevel, format=LOG_SIMPLE)
    global log
    log = logging.getLogger(__name__)

    # setup mqtt
    if args.mqtt_host:
        log.info(f"Setup MQTT connection to {args.mqtt_host}")
        if not mqttc_setup(args):
            log.error("fail to setup MQTT client")
            mqttc_close()
            exit(1)
    else:
        log.info("No MQTT host specified, skip MQTT setup.")

    # setup modbus
    if not modbus_setup(args, event_exit):
        log.error("fail to setup modbus client(master)")
        modbus_close()
        mqttc_close()
        exit(1)

    # main loop
    last_check = 0
    last_diag = 0
    while not event_exit.is_set():
        now = time.time()
        # routine check
        if now > last_check + args.rate:
            if last_check == 0:
                elapsed = args.rate
            else:
                elapsed = round(now - last_check, 6)
            last_check = now
            log.info(f"looping at rate:{args.rate}, actual:{elapsed}")
            modbus_poll()
            if args.mqtt_host:
                modbus_publish()
            if args.export:
                modbus_export(args.export)
        if args.diagnostics_rate > 0 and now > last_diag + args.diagnostics_rate:
            last_diag = now
            modbus_publish_diagnostics()
    modbus_close()
    mqttc_close()


if __name__ == "__main__":
    app()
