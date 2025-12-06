import pytest
import time
from modpoll.mqtt_task import MqttHandler


def test_mqtt_task_setup():
    mqtt_handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client_13579",
        qos=0,
        subscribe_topics=["test/topic"],
    )

    assert mqtt_handler.setup()

    # Test MQTT client properties
    assert mqtt_handler.mqtt_client is not None
    assert mqtt_handler.host == "broker.emqx.io"
    assert mqtt_handler.port == 1883

    # Clean up
    mqtt_handler.close()


def test_receive_empty_queue_returns_none():
    handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client_13579",
        qos=0,
    )

    topic, payload = handler.receive()

    assert topic is None
    assert payload is None


def test_receive_returns_message_when_available():
    handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client_13579",
        qos=0,
    )

    class FakeQueue:
        def get(self, block=False):
            return ("some/topic", b"payload")

    handler.rx_queue = FakeQueue()

    topic, payload = handler.receive()

    assert topic == "some/topic"
    assert payload == b"payload"


def test_publish_when_connected_calls_client_publish():
    handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client_13579",
        qos=1,
    )

    class StubClient:
        def __init__(self):
            self.calls = []

        def is_connected(self):
            return True

        def publish(self, topic, msg, qos, retain):
            self.calls.append((topic, msg, qos, retain))

            class PubInfo:
                rc = 0

            return PubInfo()

    stub = StubClient()
    handler.mqtt_client = stub

    result = handler.publish("topic", "message", qos=2, retain=True)

    assert result.rc == 0
    assert stub.calls == [("topic", "message", 2, True)]


def test_setup_respects_tls_option(monkeypatch):
    called = {}
    handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=8883,
        user=None,
        password=None,
        clientid="client",
        qos=0,
        subscribe_topics=["secure/topic"],
        use_tls=True,
        tls_version="tlsv1.2",
        mqtt_version="3.1.1",
    )

    def fake_setup_tls():
        called["tls"] = True

    monkeypatch.setattr(handler, "_setup_tls", fake_setup_tls)

    assert handler.setup()
    assert called.get("tls") is True
    assert handler.mqtt_client is not None


def test_publish_skips_when_disconnected_qos0(monkeypatch):
    handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client_13579",
        qos=0,
    )

    class StubClient:
        def is_connected(self):
            return False

    handler.mqtt_client = StubClient()

    result = handler.publish("topic", "msg")

    assert result is None


def test_publish_attempts_reconnect_when_disconnected_qos1(monkeypatch):
    handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client_13579",
        qos=1,
    )

    class StubClient:
        def is_connected(self):
            return False

    handler.mqtt_client = StubClient()

    called = {}

    def fake_connect():
        called["connect"] = True
        return False

    monkeypatch.setattr(handler, "connect", fake_connect)

    result = handler.publish("topic", "msg")

    assert result is None
    assert called.get("connect") is True


@pytest.mark.integration
def test_mqtt_task_connect():
    mqtt_handler = MqttHandler(
        name="test_mqtt",
        host="broker.emqx.io",
        port=1883,
        user=None,
        password=None,
        clientid="test_client_13579",
        qos=0,
    )

    assert mqtt_handler.setup()
    assert mqtt_handler.connect()

    # Add a short delay to allow the connection to establish
    time.sleep(1)

    # Test connection
    assert mqtt_handler.is_connected()

    # Clean up
    mqtt_handler.close()
