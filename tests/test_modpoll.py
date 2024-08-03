from modpoll.arg_parser import get_parser
from modpoll.modbus_task import modbus_setup
from modpoll.mqtt_task import mqttc_setup
import threading


def test_modbus_task_modbus_setup():
    parser = get_parser()
    args = parser.parse_args(
        ["-f", "examples/modsim.csv", "--tcp", "modsim.topmaker.net"]
    )
    event = threading.Event()
    assert modbus_setup(args, event) == True


def test_mqtt_task_mqttc_setup():
    parser = get_parser()
    args = parser.parse_args(
        [
            "-f",
            "examples/modsim.csv",
            "--tcp",
            "modsim.topmaker.net",
            "--mqtt-host",
            "mqtt.eclipseprojects.io",
        ]
    )
    assert mqttc_setup(args) == True
