import pytest
from modpoll.arg_parser import get_parser
from modpoll.modbus_task import setup_modbus_handlers


def test_modbus_task_modbus_setup():
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
    modbus_handlers = setup_modbus_handlers(args)
    assert len(modbus_handlers) == 2


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
    modbus_handlers = setup_modbus_handlers(args)
    modbus_handler = modbus_handlers[0]

    assert modbus_handler.connect()

    modbus_handler.poll()

    # Check if any data was collected
    assert len(modbus_handler.deviceList) > 0
    assert len(modbus_handler.deviceList[0].references) > 0

    # Check if at least one reference has a non-None value
    assert any(
        ref.val is not None for ref in modbus_handler.deviceList[0].references.values()
    )

    modbus_handler.disconnect()
    modbus_handler.close()
