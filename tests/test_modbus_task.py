import threading
from modpoll.arg_parser import get_parser
from modpoll.modbus_task import ModbusHandler


def test_modbus_task_modbus_setup():
    parser = get_parser()
    args = parser.parse_args(["--config", "examples/modsim.csv"])
    event_exit = threading.Event()
    for config_file in args.config:
        modbus_handler = ModbusHandler(args, event_exit, config_file)
        assert modbus_handler.load_config(config_file)
