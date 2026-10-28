from modpoll.modbus_task import Device, Poller, Reference


class FakeResult:
    def __init__(self, *, bits=None, registers=None):
        self.bits = bits
        self.registers = registers

    def isError(self):
        return False


def test_poller_uses_discrete_inputs_for_fc2():
    device = Device("dev", 1)
    poller = Poller(device, 2, 0, 2, "BE_BE")
    ref = Reference(device, "di0", "0", "bool", "r", None, None)
    poller.add_readable_reference(ref)

    class FakeMaster:
        def __init__(self):
            self.called = None

        def read_discrete_inputs(self, start_address, *, count, slave=None):
            self.called = ("di", start_address, count)
            return FakeResult(bits=[1, 0])

        def read_coils(self, *args, **kwargs):  # pragma: no cover - should not be used
            raise AssertionError("read_coils should not be called for fc=2")

    master = FakeMaster()

    assert poller.poll(master) is True
    assert master.called == ("di", 0, 2)
    # Value decoding path should have set a value for the reference
    assert ref.val is not None


def test_bit_reference_decodes_multiple_bits_same_register():
    device = Device("dev", 1)
    poller = Poller(device, 4, 40000, 1, "BE_BE")
    ref_msb = Reference(device, "bit15", "40000:15", "bool", "r", None, None)
    ref_lsb = Reference(device, "bit0", "40000:0", "bool", "r", None, None)
    poller.add_readable_reference(ref_msb)
    poller.add_readable_reference(ref_lsb)

    class FakeMaster:
        def __init__(self):
            self.called = None

        def read_input_registers(self, start_address, *, count, slave=None):
            self.called = ("ir", start_address, count)
            return FakeResult(registers=[0x8001])  # 1000 0000 0000 0001

    master = FakeMaster()

    assert poller.poll(master) is True
    assert master.called == ("ir", 40000, 1)
    assert ref_msb.val is True
    assert ref_lsb.val is True


def test_bit_reference_respects_endianness():
    device = Device("dev", 1)
    poller = Poller(device, 4, 0, 1, "LE_BE")
    ref_bit15 = Reference(device, "bit15", "0:15", "bool", "r", None, None)
    ref_bit7 = Reference(device, "bit7", "0:7", "bool", "r", None, None)
    poller.add_readable_reference(ref_bit15)
    poller.add_readable_reference(ref_bit7)

    class FakeMaster:
        def __init__(self):
            self.called = None

        def read_input_registers(self, start_address, *, count, slave=None):
            self.called = ("ir", start_address, count)
            return FakeResult(registers=[0x8001])  # raw register value

    master = FakeMaster()

    assert poller.poll(master) is True
    assert master.called == ("ir", 0, 1)
    # LE byte order swaps bytes: 0x8001 -> 0x0180 (bit7 set, bit15 clear)
    assert ref_bit15.val is False
    assert ref_bit7.val is True


def test_bit_syntax_only_allowed_with_bool_dtype():
    import pytest

    device = Device("dev", 1)

    # Should work: bool dtype with bit syntax
    ref_bool = Reference(device, "bit_ref", "40000:5", "bool", "r", None, None)
    assert ref_bool.bit == 5

    # Should fail: uint16 dtype with bit syntax
    with pytest.raises(ValueError, match="can only be used with dtype 'bool'"):
        Reference(device, "uint_ref", "40000:5", "uint16", "r", None, None)

    # Should fail: int32 dtype with bit syntax
    with pytest.raises(ValueError, match="can only be used with dtype 'bool'"):
        Reference(device, "int_ref", "40000:0", "int32", "r", None, None)

    # Should work: uint16 dtype without bit syntax
    ref_uint = Reference(device, "uint_ref", "40000", "uint16", "r", None, None)
    assert ref_uint.bit is None


def test_coil_groups_decode_independently_in_any_reference_order():
    device = Device("dev", 1)
    poller = Poller(device, 1, 100, 16, "BE_BE")
    second = Reference(device, "second", "101", "bool8", "r", None, None)
    first = Reference(device, "first", "100", "bool8", "r", None, None)
    poller.add_readable_reference(second)
    poller.add_readable_reference(first)
    bits = [
        True,
        False,
        False,
        True,
        False,
        False,
        True,
        False,
        False,
        True,
        True,
        False,
        True,
        False,
        False,
        True,
    ]

    class Client:
        def read_coils(self, address, count, slave):
            return FakeResult(bits=bits)

    assert poller.poll(Client())
    assert first.val == bits[:8]
    assert second.val == bits[8:]


def test_coil_group_reports_only_requested_bits_and_rejects_short_response():
    device = Device("dev", 1)
    poller = Poller(device, 1, 0, 10, "BE_BE")
    ref = Reference(device, "tail", "1", "bool8", "r", None, None)
    poller.add_readable_reference(ref)

    class Client:
        bits = [True, False] * 8

        def read_coils(self, address, count, slave):
            return FakeResult(bits=self.bits)

    client = Client()
    assert poller.poll(client)
    assert ref.val == [True, False]
    client.bits = [True] * 9
    assert not poller.poll(client)
    assert not ref.valid_this_poll
