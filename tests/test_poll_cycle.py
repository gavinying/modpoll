import json

from modpoll import modbus_task
from modpoll.modbus_task import (
    Device,
    ModbusHandler,
    Reference,
    export_modbus_handlers,
)


class FakeResponse:
    def isError(self):
        return False


class FakeClient:
    def __init__(self, connected=True):
        self.connected = connected

    def connect(self):
        return self.connected

    def close(self):
        pass


class FakePoller:
    def __init__(self, succeeds, refs):
        self.succeeds = succeeds
        self.readableReferences = refs
        self.disabled = False
        self.failcounter = 0

    def poll(self, master):
        for ref in self.readableReferences:
            ref.update_value(ref.val if self.succeeds else None, valid=self.succeeds)
        return self.succeeds


class FakeMqtt:
    def __init__(self):
        self.messages = []

    def publish(self, topic, payload, **kwargs):
        self.messages.append((topic, payload))


def make_ref(device, name, value):
    ref = Reference(device, name, "0", "uint16", "r", None, None)
    ref.update_value(value)
    return ref


def test_failed_connection_invalidates_old_sample(monkeypatch):
    device = Device("meter", 1)
    ref = make_ref(device, "voltage", 230)
    device.add_reference_mapping(ref)
    handler = ModbusHandler(FakeClient(connected=False), "unused.csv", daemon=True)
    handler.deviceList = [device]

    handler.poll()

    assert ref.val is None
    assert not ref.valid_this_poll
    assert not device.pollSuccess


def test_partial_poll_does_not_publish_a_stale_reference(monkeypatch):
    device = Device("meter", 1)
    fresh = make_ref(device, "fresh", 12)
    stale = make_ref(device, "stale", 34)
    device.add_reference_mapping(fresh)
    device.add_reference_mapping(stale)
    device.pollerList = [FakePoller(True, [fresh]), FakePoller(False, [stale])]
    handler = ModbusHandler(FakeClient(), "unused.csv", daemon=True)
    handler.deviceList = [device]
    mqtt = FakeMqtt()
    handler.mqtt_handler = mqtt
    handler.mqtt_publish_topic_pattern = "modpoll/{{device_name}}/data"
    monkeypatch.setattr(modbus_task, "delay_thread", lambda timeout=0: None)
    monkeypatch.setattr(modbus_task, "on_threading_event", lambda: False)

    handler.poll()
    handler.publish_data(timestamp=123)

    assert not device.pollSuccess
    assert fresh.valid_this_poll and fresh.val == 12
    assert not stale.valid_this_poll
    assert mqtt.messages == [
        ("modpoll/meter/data", json.dumps({"fresh": 12, "timestamp": 123}))
    ]


def test_snapshot_marks_invalid_sample_null_and_preserves_zero_timestamp(tmp_path):
    device = Device("meter", 1)
    ref = make_ref(device, "voltage", 230)
    device.add_reference_mapping(ref)
    ref.valid_this_poll = False
    handler = ModbusHandler(FakeClient(), "unused.csv")
    handler.deviceList = [device]
    path = tmp_path / "snapshot.json"

    handler.export(path, timestamp=0)

    assert json.loads(path.read_text()) == {"meter": {"voltage": None, "timestamp": 0}}


def test_zero_scale_is_applied_to_nonzero_register_value():
    device = Device("meter", 1)
    ref = Reference(device, "zeroed", "0", "uint16", "r", None, 0)

    ref.update_value(123)

    assert ref.val == 0


def test_export_merges_multiple_handlers_and_preserves_old_file_on_failure(
    monkeypatch, tmp_path
):
    first_device = Device("first", 1)
    second_device = Device("second", 2)
    first_ref = make_ref(first_device, "value", 1)
    second_ref = make_ref(second_device, "value", 2)
    first_device.add_reference_mapping(first_ref)
    second_device.add_reference_mapping(second_ref)
    handlers = [
        ModbusHandler(FakeClient(), "first.csv"),
        ModbusHandler(FakeClient(), "second.csv"),
    ]
    handlers[0].deviceList = [first_device]
    handlers[1].deviceList = [second_device]
    path = tmp_path / "snapshot.json"

    assert export_modbus_handlers(handlers, path, timestamp=10)
    assert json.loads(path.read_text()) == {
        "first": {"value": 1, "timestamp": 10},
        "second": {"value": 2, "timestamp": 10},
    }

    def fail_replace(*args):
        raise OSError("disk error")

    monkeypatch.setattr(modbus_task.os, "replace", fail_replace)
    assert not export_modbus_handlers(handlers, path, timestamp=11)
    assert json.loads(path.read_text()) == {
        "first": {"value": 1, "timestamp": 10},
        "second": {"value": 2, "timestamp": 10},
    }
    assert list(tmp_path.glob(".snapshot.json.*.tmp")) == []


def test_autoremove_requires_three_consecutive_failures_and_restart(monkeypatch):
    from modpoll.modbus_task import Poller

    monkeypatch.setattr(modbus_task, "delay_thread", lambda timeout=0: None)
    monkeypatch.setattr(modbus_task, "on_threading_event", lambda: False)
    device = Device("meter", 1)
    poller = Poller(device, 3, 0, 1, "BE_BE")
    outcomes = iter([False, False, True, False, False, False])
    poller.poll = lambda client: next(outcomes)
    device.pollerList = [poller]
    handler = ModbusHandler(FakeClient(), "unused.csv", daemon=True, autoremove=True)
    handler.deviceList = [device]

    for expected in (1, 2, 0, 1, 2):
        handler.poll()
        assert poller.failcounter == expected
        assert not poller.disabled
    handler.poll()
    assert poller.failcounter == 3
    assert poller.disabled
    handler.poll()
    assert poller.disabled


def test_connection_failures_count_for_autoremove():
    from modpoll.modbus_task import Poller

    device = Device("meter", 1)
    poller = Poller(device, 3, 0, 1, "BE_BE")
    device.pollerList = [poller]
    handler = ModbusHandler(
        FakeClient(connected=False), "unused.csv", daemon=True, autoremove=True
    )
    handler.deviceList = [device]
    for _ in range(3):
        handler.poll()
    assert poller.disabled


def test_failure_and_recovery_never_publish_old_samples(monkeypatch, tmp_path):
    from modpoll.modbus_task import Poller

    monkeypatch.setattr(modbus_task, "delay_thread", lambda timeout=0: None)
    monkeypatch.setattr(modbus_task, "on_threading_event", lambda: False)
    device = Device("meter", 1)
    ref = Reference(device, "value", "0", "uint16", "r", None, None)
    device.add_reference_mapping(ref)
    poller = Poller(device, 3, 0, 1, "BE_BE")
    poller.add_readable_reference(ref)
    device.pollerList = [poller]

    class Client(FakeClient):
        response = 7

        def read_holding_registers(self, address, count, slave):
            if self.response is None:
                return None
            return type(
                "Response",
                (),
                {"registers": [self.response], "isError": lambda self: False},
            )()

    client = Client()
    mqtt = FakeMqtt()
    handler = ModbusHandler(
        client,
        "unused.csv",
        mqtt,
        daemon=True,
        mqtt_publish_topic_pattern="data/{{device_name}}",
    )
    handler.deviceList = [device]
    path = tmp_path / "snapshot.json"
    handler.poll()
    handler.publish_data(timestamp=1)
    assert json.loads(mqtt.messages[-1][1]) == {"value": 7, "timestamp": 1}
    client.response = None
    handler.poll()
    handler.publish_data(timestamp=2)
    assert len(mqtt.messages) == 1
    assert handler.export(path, timestamp=2)
    assert json.loads(path.read_text()) == {"meter": {"value": None, "timestamp": 2}}
    client.response = 9
    handler.poll()
    handler.publish_data(timestamp=3)
    assert json.loads(mqtt.messages[-1][1]) == {"value": 9, "timestamp": 3}
    assert handler.export(path, timestamp=3)
    assert json.loads(path.read_text()) == {"meter": {"value": 9, "timestamp": 3}}
    handler.mqtt_single_publish = True
    client.response = None
    handler.poll()
    before = len(mqtt.messages)
    handler.publish_data(timestamp=4)
    assert len(mqtt.messages) == before


def test_nonfinite_scale_is_rejected_and_nonfinite_sample_is_invalid(caplog):
    device = Device("meter", 1)
    ref = Reference(device, "temperature", "0", "float32", "r", None, None)
    ref.update_value(float("inf"))
    assert ref.val is None and not ref.valid_this_poll


def test_nonfinite_register_sample_marks_poll_failed(monkeypatch):
    from modpoll.modbus_task import Poller

    device = Device("meter", 1)
    ref = Reference(device, "temperature", "0", "float32", "r", None, None)
    poller = Poller(device, 3, 0, 2, "BE_BE")
    poller.add_readable_reference(ref)

    class Client:
        def read_holding_registers(self, address, count, slave):
            return type(
                "Response",
                (),
                {"registers": [0x7F80, 0], "isError": lambda self: False},
            )()

    assert not poller.poll(Client())
    assert not ref.valid_this_poll
    assert device.errorCount == 1


def test_snapshot_rejects_nonstandard_nan_without_damaging_existing_file(tmp_path):
    device = Device("meter", 1)
    ref = make_ref(device, "value", 1)
    ref.val = float("nan")
    ref.valid_this_poll = True
    device.add_reference_mapping(ref)
    handler = ModbusHandler(FakeClient(), "unused.csv")
    handler.deviceList = [device]
    path = tmp_path / "snapshot.json"
    path.write_text('{"previous": true}')
    assert not handler.export(path)
    assert path.read_text() == '{"previous": true}'
    assert list(tmp_path.glob(".snapshot.json.*.tmp")) == []


def test_odd_length_string_does_not_include_padding_byte():
    from modpoll.modbus_task import Poller

    device = Device("meter", 1)
    ref = Reference(device, "label", "0", "string3", "r", None, None)
    poller = Poller(device, 3, 0, 2, "BE_BE")
    poller.add_readable_reference(ref)

    class Client:
        def read_holding_registers(self, address, count, slave):
            return type(
                "Response",
                (),
                {"registers": [0x4142, 0x4358], "isError": lambda self: False},
            )()

    assert poller.poll(Client())
    assert ref.val == "ABC"
