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


def test_csv_parser_reports_line_and_keeps_valid_rows(caplog):
    import csv
    from io import StringIO

    handler = ModbusHandler(FakeClient(), "unused.csv", daemon=True)
    rows = csv.reader(
        StringIO(
            "device,meter,1,description\n"
            "poll,holding_register,0,1,BE_BE\n"
            "ref,value,0,uint16,r\n"
            "poll,holding_register,not-an-address,1,BE_BE\n"
            "device,backup,2,description\n"
            "poll,holding_register,0,1,BE_BE\n"
            "ref,value,0,uint16,r\n"
        )
    )

    devices = handler._parse_config(rows)

    assert [device.name for device in devices] == ["meter", "backup"]
    assert "line 4" in caplog.text.lower()
    assert "start address" in caplog.text.lower()


def test_csv_parser_rejects_invalid_ranges_and_duplicate_devices(caplog):
    import csv
    from io import StringIO

    handler = ModbusHandler(FakeClient(), "unused.csv", daemon=True)
    rows = csv.reader(
        StringIO(
            "device,meter,1,description\n"
            "poll,holding_register,65535,2,BE_BE\n"
            "poll,holding_register,0,0,BE_BE\n"
            "poll,holding_register,0,1,BE_BE\n"
            "ref,value,0,uint16,r,,not-a-number\n"
            "device,meter,2,duplicate\n"
            "device,backup,256,invalid-id\n"
        )
    )

    devices = handler._parse_config(rows)

    assert [device.name for device in devices] == ["meter"]
    assert len(devices[0].pollerList) == 1
    assert not devices[0].references
    assert "address" in caplog.text.lower()
    assert "size" in caplog.text.lower()
    assert "duplicate" in caplog.text.lower()
    assert "device id" in caplog.text.lower()


def test_csv_parser_rejects_unsupported_dtype_and_invalid_rw_mode(caplog):
    import csv
    from io import StringIO

    handler = ModbusHandler(FakeClient(), "unused.csv", daemon=True)
    rows = csv.reader(
        StringIO(
            "device,meter,1,description\n"
            "poll,holding_register,0,2,BE_BE\n"
            "ref,bad_type,0,decimal128,r\n"
            "ref,bad_mode,1,uint16,readwrite\n"
        )
    )

    devices = handler._parse_config(rows)

    assert len(devices) == 1
    assert not devices[0].references
    assert "unsupported dtype" in caplog.text.lower()
    assert "read/write mode" in caplog.text.lower()
