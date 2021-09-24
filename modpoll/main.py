import logging
import time
import sys
import signal

from modpoll.arg_parser import get_parser
from modpoll.mqtt_task import mqttc_setup, mqttc_close
from modpoll.modbus_task import modbus_setup, modbus_poll, modbus_export, modbus_close

# global objects
run_loop = True

# logging format
LOG_SIMPLE = "%(asctime)s | %(levelname).1s | %(name)s | %(message)s"
LOG_PROCESS = "%(asctime)s | %(levelname).1s | %(processName)s | %(name)s | %(message)s"
LOG_THREAD = "%(asctime)s | %(levelname).1s | %(threadName)s | %(name)s | %(message)s"
log = None


def _signal_handler(signal, frame):
    print('Exiting ' + sys.argv[0])
    _shutdown()


def app(name="modpoll"):
    # log.info(f"Starting {name} v{__version__}")
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
    if not modbus_setup(args):
        log.error("fail to setup modbus client(master)")
        modbus_close()
        mqttc_close()
        exit(1)

    # main loop
    last_check = 0
    while run_loop:
        now = time.time()
        # routine check
        if now > last_check + args.rate:
            if last_check == 0:
                elapsed = args.rate
            else:
                elapsed = now - last_check
            last_check = now
            log.info(f"looping at rate:{args.rate}, actual:{elapsed}")
            modbus_poll()
            if args.export:
                modbus_export(args.export)
    modbus_close()
    mqttc_close()


def _shutdown():
    global run_loop
    run_loop = False


if __name__ == "__main__":
    app()
