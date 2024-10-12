import pytest
import threading
from modpoll.arg_parser import get_parser
from modpoll.modbus_task import ModbusMaster


def test_modbus_task_modbus_setup():
    modbus_masters = []
    parser = get_parser()
    args = parser.parse_args(
        [
            "--config",
            "examples/modsim.csv",
            "examples/modsim2.csv",
            "--tcp",
            "modsim.topmaker.net",
        ]
    )
    event_exit = threading.Event()
    for config_file in args.config:
        modbus_master = ModbusMaster(args, event_exit, config_file)
        if modbus_master.setup():
            modbus_masters.append(modbus_master)
        else:
            modbus_master.close()
    assert len(modbus_masters) == 2


@pytest.mark.integration
def test_modbus_task_poll_modsim():
    parser = get_parser()
    args = parser.parse_args(
        [
            "--config",
            "examples/modsim.csv",
            "--tcp",
            "modsim.topmaker.net",
        ]
    )
    event_exit = threading.Event()
    modbus_master = ModbusMaster(args, event_exit, args.config[0])

    assert modbus_master.setup()
    assert modbus_master.connect()

    modbus_master.poll()

    # Check if any data was collected
    assert len(modbus_master.deviceList) > 0
    assert len(modbus_master.deviceList[0].references) > 0

    # Check if at least one reference has a non-None value
    assert any(
        ref.val is not None for ref in modbus_master.deviceList[0].references.values()
    )

    modbus_master.disconnect()
    modbus_master.close()
