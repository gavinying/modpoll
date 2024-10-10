import pytest
import time
from modpoll.mqtt_task import MqttHandler


def test_mqtt_task_setup():
    mqtt_task = MqttHandler(
        name="test_mqtt",
        host="mqtt.eclipseprojects.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client",
        qos=0,
        subscribe_topics=["test/topic"],
    )

    assert mqtt_task.mqttc_setup()

    # Test MQTT client properties
    assert mqtt_task.mqttc is not None
    assert mqtt_task.host == "mqtt.eclipseprojects.io"
    assert mqtt_task.port == 1883

    # Clean up
    mqtt_task.mqttc_close()


@pytest.mark.integration
def test_mqtt_task_connect():
    mqtt_task = MqttHandler(
        name="test_mqtt",
        host="mqtt.eclipseprojects.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client",
        qos=0,
    )

    assert mqtt_task.mqttc_setup()
    assert mqtt_task.mqttc_connect()

    # Add a short delay to allow the connection to establish
    time.sleep(1)

    # Test connection
    assert mqtt_task.mqttc_connected()

    # Clean up
    mqtt_task.mqttc_close()
