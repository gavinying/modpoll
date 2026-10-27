import csv
import json
import logging
import math
import os
import tempfile
from pathlib import Path
from typing import List, Optional

import requests
from prettytable import PrettyTable
from pymodbus.client import ModbusSerialClient, ModbusTcpClient, ModbusUdpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.framer.ascii import FramerAscii as ModbusAsciiFramer
from pymodbus.framer.rtu import FramerRTU as ModbusRtuFramer
from pymodbus.framer.socket import FramerSocket as ModbusSocketFramer

from .utils import on_threading_event, delay_thread
from .mqtt_task import MqttHandler


FLOAT_TYPE_PRECISION = 3
CONFIG_DEVICE_COL_MIN = 3
CONFIG_POLL_COL_MIN = 5
CONFIG_REF_COL_MIN = 5


def export_modbus_handlers(handlers, file, timestamp=None) -> bool:
    """Write one complete, atomically replaced JSON snapshot for all handlers."""
    data = {}
    for handler in handlers:
        for dev in handler.deviceList:
            if dev.name in data:
                handler.logger.error("Cannot export duplicate device name %s", dev.name)
                return False
            dev_data = {
                ref.name: ref.val if ref.valid_this_poll else None
                for ref in dev.references.values()
            }
            if timestamp is not None:
                dev_data["timestamp"] = timestamp
            data[dev.name] = dev_data

    target = Path(file)
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(data, output, indent=2, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        return True
    except (OSError, TypeError, ValueError) as e:
        logging.getLogger(__name__).error("Error exporting data: %s", e)
        return False
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                logging.getLogger(__name__).warning(
                    "Unable to remove temporary snapshot %s", temporary
                )


class Device:
    def __init__(self, device_name: str, device_id: int):
        self.name = device_name
        self.devid = device_id
        self.pollerList: List[Poller] = []
        self.references: dict = {}
        self.errorCount = 0
        self.pollCount = 0
        self.pollSuccess = False

    def add_reference_mapping(self, ref):
        self.references[ref.name] = ref


class Poller:
    def __init__(
        self,
        device: Device,
        function_code: int,
        start_address: int,
        size: int,
        endian: str,
    ):
        self.device = device
        self.fc = function_code
        self.start_address = start_address
        self.size = size
        self.endian = endian.lower()
        self.readableReferences: List[Reference] = []
        self.disabled = False
        self.failcounter = 0
        self.logger = logging.getLogger(__name__)

    def poll(self, master) -> bool:
        try:
            result = None
            data = None
            decode_success = True

            def _call_read(method):
                # Prefer keyword-only signature (pymodbus 3.9+), fall back to positional for tests/fakes.
                try:
                    return method(
                        self.start_address, count=self.size, slave=self.device.devid
                    )
                except TypeError:
                    return method(self.start_address, self.size, self.device.devid)

            if self.fc == 1:
                result = _call_read(master.read_coils)
            elif self.fc == 2:
                result = _call_read(master.read_discrete_inputs)
            elif self.fc == 3:
                result = _call_read(master.read_holding_registers)
            elif self.fc == 4:
                result = _call_read(master.read_input_registers)

            if result and not result.isError():
                if self.fc in (1, 2):
                    data = result.bits
                    # CSV addresses for bit tables identify eight-bit groups,
                    # relative to the poll start, as in the documented examples.
                    group_count = math.ceil(self.size / 8)
                    for ref in self.readableReferences:
                        offset = ref.address - self.start_address
                        if (
                            offset < 0
                            or offset + ref.ref_width > group_count
                            or len(data) < min((offset + ref.ref_width) * 8, self.size)
                        ):
                            ref.update_value(None, valid=False)
                            decode_success = False
                            self.logger.error(
                                "Reference %s is outside the polled bit groups",
                                ref.name,
                            )
                            continue
                        try:
                            if (
                                ref.dtype in ("bool", "bool8", "bool16")
                                and ref.bit is None
                            ):
                                start = offset * 8
                                ref.update_value(
                                    list(
                                        data[
                                            start : min(
                                                start + ref.ref_width * 8, self.size
                                            )
                                        ]
                                    )
                                )
                            else:
                                decoder = self._get_decoder(data)
                                decoder.skip_bytes(offset)
                                self._decode_and_update_reference(ref, decoder)
                            if not ref.valid_this_poll:
                                decode_success = False
                        except Exception:
                            ref.update_value(None, valid=False)
                            decode_success = False
                            self.logger.exception(
                                "Failed to decode value for reference: %s", ref.name
                            )
                else:  # Function codes 3 and 4
                    data = result.registers
                    # Sort refs by address to ensure predictable decoding order
                    sorted_refs = sorted(
                        self.readableReferences, key=lambda r: r.address
                    )
                    for ref in sorted_refs:
                        # Create and position a new decoder for each reference for robustness
                        decoder = self._get_decoder(data)
                        offset_bytes = (ref.address - self.start_address) * 2
                        if offset_bytes < 0:
                            self.logger.warning(
                                f"Reference {ref.name} address {ref.address} is outside of poller range starting at {self.start_address}"
                            )
                            ref.update_value(None, valid=False)
                            decode_success = False
                            continue
                        decoder.skip_bytes(offset_bytes)
                        try:
                            self._decode_and_update_reference(ref, decoder)
                            if not ref.valid_this_poll:
                                decode_success = False
                        except Exception as e:
                            ref.update_value(None, valid=False)
                            decode_success = False
                            self.logger.error(
                                f"Failed to decode value for reference: {ref.name} - {e}"
                            )
                self.update_statistics(decode_success)
                return decode_success
        except ModbusException:
            self.logger.error(
                f"Modbus exception: {self.device.name} {self.fc} {self.start_address} {self.size}"
            )

        self.update_statistics(False)
        for ref in self.readableReferences:
            ref.update_value(None)
        return False

    def _get_decoder(self, data):
        if "BE_BE" == self.endian.upper():
            return (
                BinaryPayloadDecoder.fromRegisters(
                    data, byteorder=Endian.BIG, wordorder=Endian.BIG
                )
                if self.fc not in (1, 2)
                else BinaryPayloadDecoder.fromCoils(data, byteorder=Endian.BIG)
            )
        elif "LE_BE" == self.endian.upper():
            return (
                BinaryPayloadDecoder.fromRegisters(
                    data, byteorder=Endian.LITTLE, wordorder=Endian.BIG
                )
                if self.fc not in (1, 2)
                else BinaryPayloadDecoder.fromCoils(data, byteorder=Endian.LITTLE)
            )
        elif "LE_LE" == self.endian.upper():
            return (
                BinaryPayloadDecoder.fromRegisters(
                    data, byteorder=Endian.LITTLE, wordorder=Endian.LITTLE
                )
                if self.fc not in (1, 2)
                else BinaryPayloadDecoder.fromCoils(data, byteorder=Endian.LITTLE)
            )
        else:
            return (
                BinaryPayloadDecoder.fromRegisters(
                    data, byteorder=Endian.BIG, wordorder=Endian.LITTLE
                )
                if self.fc not in (1, 2)
                else BinaryPayloadDecoder.fromCoils(data, byteorder=Endian.BIG)
            )

    def _decode_and_update_reference(
        self, ref: "Reference", decoder: BinaryPayloadDecoder
    ):
        if ref.dtype == "bool" and ref.bit is not None:
            # Bit references read a 16-bit register and extract one bit.
            register_value = decoder.decode_16bit_uint()
            bit_value = (register_value >> ref.bit) & 1
            ref.update_value(bool(bit_value))
            return

        decode_methods = {
            "uint16": decoder.decode_16bit_uint,
            "int16": decoder.decode_16bit_int,
            "uint32": decoder.decode_32bit_uint,
            "int32": decoder.decode_32bit_int,
            "uint64": decoder.decode_64bit_uint,
            "int64": decoder.decode_64bit_int,
            "float16": decoder.decode_16bit_float,
            "float32": decoder.decode_32bit_float,
            "float64": decoder.decode_64bit_float,
            "bool8": decoder.decode_bits,
            "bool": decoder.decode_bits,
            "bool16": lambda: decoder.decode_bits() + decoder.decode_bits(),
        }

        if ref.dtype in decode_methods:
            ref.update_value(decode_methods[ref.dtype]())
        elif ref.dtype.startswith("string"):
            ref.update_value(
                decoder.decode_string(ref.ref_width * 2).decode("utf-8").rstrip("\x00")
            )

    def add_readable_reference(self, ref: "Reference"):
        if ref not in self.readableReferences:
            self.readableReferences.append(ref)

    def update_statistics(self, success: bool):
        self.device.pollCount += 1
        if success:
            self.failcounter = 0
            self.device.pollSuccess = True
        else:
            self.failcounter += 1
            self.device.errorCount += 1
            self.device.pollSuccess = False


class Reference:
    def __init__(
        self,
        device: Device,
        ref_name: str,
        ref_addr: str,
        dtype: str,
        rw: str,
        unit: str,
        scale: float,
    ):
        self.device = device
        self.name = ref_name
        self.bit: Optional[int] = None
        try:
            if ":" in ref_addr:
                addr, bit = ref_addr.split(":")
                self.address = int(addr, 0)
                self.bit = int(bit)
                if not 0 <= self.bit <= 15:
                    raise ValueError("Bit index must be between 0 and 15")
            else:
                self.address = int(ref_addr, 0)
        except ValueError as e:
            raise ValueError(f"Invalid address format for {ref_name}: {e}") from e
        self.dtype = dtype.lower()
        # Validate that bit syntax is only used with bool dtype
        if self.bit is not None and self.dtype != "bool":
            raise ValueError(
                f"Bit index syntax (address:bit) can only be used with dtype 'bool', "
                f"but reference {ref_name} has dtype '{self.dtype}'"
            )
        self.ref_width = self._get_ref_width()
        self.rw = rw.lower()
        self.unit = unit
        self.scale = scale
        self.val = None
        self.last_val = None
        self.valid_this_poll = False

    def __eq__(self, other):
        if isinstance(other, Reference):
            return self.address == other.address and self.bit == other.bit
        return False

    def __hash__(self):
        return hash((self.address, self.bit))

    def __repr__(self):
        addr = f"{self.address}:{self.bit}" if self.bit is not None else self.address
        return f"<Reference {self.name}@{addr}>"

    def _get_ref_width(self) -> int:
        width_map = {
            "int16": 1,
            "uint16": 1,
            "float16": 1,
            "bool8": 1,
            "bool": 1,
            "int32": 2,
            "uint32": 2,
            "float32": 2,
            "bool16": 2,
            "int64": 4,
            "uint64": 4,
            "float64": 4,
        }
        if self.dtype in width_map:
            return width_map[self.dtype]
        elif self.dtype.startswith("string"):
            try:
                width = int(self.dtype[6:])
            except ValueError as exc:
                raise ValueError(f"Invalid string dtype: {self.dtype}") from exc
            if width <= 0:
                raise ValueError(f"String length must be positive: {self.dtype}")
            return (width + 1) // 2
        else:
            raise ValueError(f"Unsupported dtype: {self.dtype}")

    def check_sanity(self, reference: int, size: int) -> bool:
        return self.address in range(
            reference, size + reference
        ) and self.address + self.ref_width - 1 in range(reference, size + reference)

    def update_value(self, v, valid=True):
        if self.scale is not None and not isinstance(v, bool):
            try:
                v = v * float(self.scale)
            except (ValueError, TypeError):
                pass
        if isinstance(v, float) and not math.isfinite(v):
            logging.getLogger(__name__).warning(
                "Non-finite value for reference %s on device %s",
                self.name,
                self.device.name,
            )
            v = None
            valid = False
        self.last_val = self.val
        self.val = v
        self.valid_this_poll = valid and v is not None


class _ConfigLogAdapter(logging.LoggerAdapter):
    def process(self, message, kwargs):
        return "[%s] %s" % (self.extra["config"], message), kwargs


class ModbusHandler:
    def __init__(
        self,
        modbus_client,
        config_file: str,
        mqtt_handler: Optional[MqttHandler] = None,
        timeout: float = 3.0,
        interval: float = 0.5,
        daemon: bool = False,
        mqtt_publish_topic_pattern: Optional[str] = None,
        mqtt_diagnostics_topic_pattern: Optional[str] = None,
        mqtt_single_publish: bool = False,
        autoremove: bool = False,
    ):
        self.modbus_client = modbus_client
        self.config_file = config_file
        self.mqtt_handler = mqtt_handler
        self.timeout = timeout
        self.interval = interval
        self.daemon = daemon
        self.mqtt_publish_topic_pattern = mqtt_publish_topic_pattern
        self.mqtt_diagnostics_topic_pattern = mqtt_diagnostics_topic_pattern
        self.mqtt_single_publish = mqtt_single_publish
        self.autoremove = autoremove
        self.connected = False
        self.deviceList: List[Device] = []
        self.logger = _ConfigLogAdapter(
            logging.getLogger(__name__), {"config": config_file}
        )

    def load_config(self) -> bool:
        self.logger.info(f"Loading config from: {self.config_file}")
        try:
            with requests.Session() as s:
                response = s.get(self.config_file, timeout=self.timeout)
                response.raise_for_status()
                decoded_content = response.content.decode("utf-8")
                csv_reader = csv.reader(decoded_content.splitlines(), delimiter=",")
                self.deviceList = self._parse_config(csv_reader)
        except requests.RequestException:
            try:
                with open(self.config_file, "r") as f:
                    csv_reader = csv.reader(f)
                    self.deviceList = self._parse_config(csv_reader)
            except IOError as e:
                self.logger.error(f"Error opening file: {e}")
                return False
        if self.deviceList:
            self.logger.info(f"Added {len(self.deviceList)} device(s)...")
            return True
        else:
            self.logger.error("No device found in the config file. Skipping.")
            return False

    def _parse_config(self, csv_reader) -> List[Device]:
        device_list = []
        current_device = None
        current_poller = None
        duplicate_devices = []
        for line_number, row in enumerate(csv_reader, start=1):
            if not row or all(cell.strip() == "" for cell in row):
                continue
            try:
                if "device" in row[0].lower():
                    if len(row) < CONFIG_DEVICE_COL_MIN:
                        self.logger.error(
                            "Config line %s: invalid device configuration", line_number
                        )
                        continue
                    device_name = row[1].strip()
                    if any(device.name == device_name for device in device_list):
                        self.logger.error(
                            "Config line %s: duplicate device name %s",
                            line_number,
                            device_name,
                        )
                        duplicate_devices.append((line_number, device_name))
                        current_device = None
                        current_poller = None
                        continue
                    try:
                        device_id = int(row[2], 0)
                    except ValueError:
                        self.logger.error(
                            "Config line %s: invalid device ID for %s",
                            line_number,
                            device_name,
                        )
                        current_device = None
                        current_poller = None
                        continue
                    if not 1 <= device_id <= 254:
                        self.logger.error(
                            "Config line %s: device ID out of range for %s",
                            line_number,
                            device_name,
                        )
                        current_device = None
                        current_poller = None
                        continue
                    current_device = Device(device_name, device_id)
                    device_list.append(current_device)
                    current_poller = None
                elif "poll" in row[0].lower():
                    if not current_device:
                        self.logger.error(
                            "Config line %s: no device to add poller", line_number
                        )
                        current_poller = None
                        continue
                    current_poller = self._create_poller(row, current_device)
                    if current_poller:
                        current_device.pollerList.append(current_poller)
                    else:
                        self.logger.error("Config line %s: poller ignored", line_number)
                elif "ref" in row[0].lower():
                    if not current_device or not current_poller:
                        self.logger.error(
                            "Config line %s: reference has no valid device/poller",
                            line_number,
                        )
                        continue
                    ref = self._create_reference(row, current_device)
                    if ref is None:
                        self.logger.error(
                            "Config line %s: reference ignored", line_number
                        )
                        continue
                    if ref.name in current_device.references:
                        self.logger.error(
                            "Config line %s: duplicate reference name %s",
                            line_number,
                            ref.name,
                        )
                        continue
                    if self._validate_reference(ref, current_poller):
                        if "r" in ref.rw.lower():
                            current_poller.add_readable_reference(ref)
                        current_device.add_reference_mapping(ref)
                    else:
                        self.logger.error(
                            "Config line %s: reference failed validation", line_number
                        )
                else:
                    self.logger.warning(
                        "Config line %s: unknown row type %r", line_number, row[0]
                    )
            except Exception as exc:
                self.logger.error(
                    "Config line %s: invalid row %r: %s", line_number, row, exc
                )
        if duplicate_devices:
            details = ", ".join(
                "%s (line %s)" % (name, line) for line, name in duplicate_devices
            )
            raise ValueError(
                "Duplicate device names in %s: %s" % (self.config_file, details)
            )
        return device_list

    def _create_poller(self, row, current_device):
        if len(row) < CONFIG_POLL_COL_MIN:
            self.logger.error("Invalid poller configuration")
            return None
        fc = row[1].lower()
        try:
            start_address = int(row[2], 0)
            size = int(row[3], 0)
        except ValueError:
            self.logger.error("Invalid start address or size for poller")
            return None
        endian = row[4].upper()
        if endian not in {"BE_BE", "BE_LE", "LE_BE", "LE_LE"}:
            self.logger.error("Invalid endian setting: %s", endian)
            return None
        function_code = self._get_function_code(fc)
        if function_code is None:
            return None
        if not 0 <= start_address <= 65535:
            self.logger.error("Invalid poller start address: %s", start_address)
            return None
        if not self._validate_poller_size(function_code, size):
            return None
        if start_address + size > 65536:
            self.logger.error("Poller address range exceeds Modbus address space")
            return None
        return Poller(current_device, function_code, start_address, size, endian)

    def _get_function_code(self, fc):
        fc_map = {
            "coil": 1,
            "discrete_input": 2,
            "holding_register": 3,
            "input_register": 4,
        }
        if fc in fc_map:
            return fc_map[fc]
        self.logger.warning(f"Unknown function code ({fc}) ignoring poller.")
        return None

    def _validate_poller_size(self, function_code, size):
        if size <= 0:
            self.logger.error("Poller size must be positive: %s", size)
            return False
        if function_code in (1, 2) and size > 2000:
            self.logger.error(
                f"Too many coils/discrete inputs (max. 2000): {size}. Ignoring poller."
            )
            return False
        if function_code in (3, 4) and size > 123:
            self.logger.error(
                f"Too many registers (max. 123): {size}. Ignoring poller."
            )
            return False
        return True

    def _create_reference(self, row, current_device):
        if len(row) < CONFIG_REF_COL_MIN:
            self.logger.error("Invalid reference configuration")
            return None
        ref_name = row[1].replace(" ", "_")
        try:
            address = row[2]
        except ValueError:
            self.logger.error(f"Invalid address for reference {ref_name}")
            return None
        dtype = row[3].lower()
        rw = (row[4] or "r").lower()
        if rw not in {"r", "w", "rw"}:
            self.logger.error("Invalid read/write mode for reference %s", ref_name)
            return None
        unit = row[5] if len(row) > 5 else None
        try:
            scale = float(row[6]) if len(row) > 6 and row[6] else None
            if scale is not None and not math.isfinite(scale):
                raise ValueError("scale must be finite")
        except ValueError:
            self.logger.error("Invalid scale for reference %s", ref_name)
            return None
        return Reference(current_device, ref_name, address, dtype, rw, unit, scale)

    def _validate_reference(self, ref, current_poller):
        if ref in current_poller.readableReferences:
            self.logger.warning(f"Reference {ref.name} is already added, ignoring it.")
            return False
        reference_size = (
            math.ceil(current_poller.size / 8)
            if current_poller.fc in (1, 2)
            else current_poller.size
        )
        if not ref.check_sanity(current_poller.start_address, reference_size):
            self.logger.warning(
                f"Reference {ref.name} failed to pass sanity check, ignoring it."
            )
            return False
        return True

    def connect(self) -> bool:
        if not self.connected:
            self.connected = self.modbus_client.connect()
        return self.connected

    def disconnect(self):
        if self.modbus_client and self.connected:
            self.modbus_client.close()
            self.connected = False

    def _record_poller_result(self, poller, success, previous_failures):
        poller.failcounter = 0 if success else previous_failures + 1
        if self.autoremove and poller.failcounter >= 3:
            poller.disabled = True
            self.logger.warning(
                "Disabled poller for %s at address %s after 3 consecutive failures; restart to retry",
                poller.device.name,
                poller.start_address,
            )

    def poll(self):
        for dev in self.deviceList:
            dev.pollSuccess = False
            for ref in dev.references.values():
                ref.valid_this_poll = False
        if not self.connect():
            self.logger.error("Failed to connect to Modbus client")
            for dev in self.deviceList:
                for ref in dev.references.values():
                    ref.update_value(None, valid=False)
                for poller in dev.pollerList:
                    if not poller.disabled:
                        self._record_poller_result(poller, False, poller.failcounter)
            return
        try:
            for dev in self.deviceList:
                self.logger.debug(f"Polling device {dev.name} ...")
                pollers = [p for p in dev.pollerList if not p.disabled]
                poll_success = bool(pollers)
                for p in pollers:
                    previous_failures = p.failcounter
                    try:
                        succeeded = p.poll(self.modbus_client)
                        poll_success = succeeded and poll_success
                    except Exception:
                        self.logger.exception("Unexpected polling error")
                        succeeded = False
                        poll_success = False
                        for ref in p.readableReferences:
                            ref.update_value(None, valid=False)
                    self._record_poller_result(p, succeeded, previous_failures)
                    if on_threading_event():
                        return
                    delay_thread(timeout=self.interval)
                dev.pollSuccess = poll_success
        finally:
            self.disconnect()
            if not self.daemon:
                self.print_results()

    def write_coil(self, device_name: str, address: int, value) -> bool:
        for dev in self.deviceList:
            if dev.name == device_name:
                try:
                    if not _valid_write_address(address):
                        self.logger.warning(f"Invalid coil address: {address}")
                        return False
                    if type(value) not in (bool, int) or value not in (0, 1):
                        self.logger.warning(f"Invalid coil value: {value}")
                        return False
                    if not self.connect():
                        return False
                    result = self.modbus_client.write_coil(
                        address, bool(value), slave=dev.devid
                    )
                    return not result.isError()
                except (
                    ModbusException,
                    OSError,
                    TypeError,
                    ValueError,
                    AttributeError,
                ) as e:
                    self.logger.error(f"Error writing coil: {e}")
                    return False
                finally:
                    self.disconnect()
        self.logger.error(f"Device {device_name} not found")
        return False

    def write_register(self, device_name, address: int, value) -> bool:
        for dev in self.deviceList:
            if dev.name == device_name:
                try:
                    if not _valid_write_address(address):
                        self.logger.warning(f"Invalid register address: {address}")
                        return False
                    if isinstance(value, list):
                        if (
                            not value
                            or len(value) > 123
                            or any(
                                type(item) is not int or not 0 <= item <= 65535
                                for item in value
                            )
                            or address + len(value) > 65536
                        ):
                            self.logger.warning(
                                "Invalid holding register values or span"
                            )
                            return False
                        write = self.modbus_client.write_registers
                        args = (address, value)
                    elif type(value) is int and 0 <= value <= 65535:
                        write = self.modbus_client.write_register
                        args = (address, value)
                    else:
                        self.logger.warning(f"Invalid holding register value: {value}")
                        return False
                    if not self.connect():
                        return False
                    result = write(*args, slave=dev.devid)
                    return not result.isError()
                except (
                    ModbusException,
                    OSError,
                    TypeError,
                    ValueError,
                    AttributeError,
                ) as e:
                    self.logger.error(f"Error writing register: {e}")
                    return False
                finally:
                    self.disconnect()
        self.logger.error(f"Device {device_name} not found")
        return False

    def print_results(self):
        for dev in self.deviceList:
            table = PrettyTable()
            table.field_names = ["Reference", "Value", "Unit"]
            table.align["Reference"] = "l"
            table.align["Value"] = "r"
            table.align["Unit"] = "l"
            for ref in dev.references.values():
                value = (
                    round(ref.val, FLOAT_TYPE_PRECISION)
                    if ref.valid_this_poll and isinstance(ref.val, float)
                    else ref.val
                )
                table.add_row(
                    [ref.name, value if ref.valid_this_poll else None, ref.unit or ""]
                )
            print(f"\nDevice: {dev.name}")
            print(table)

    def publish_data(self, timestamp=None, on_change=False):
        if not self.mqtt_handler or not self.mqtt_publish_topic_pattern:
            return

        for dev in self.deviceList:
            payload = {}
            for ref in dev.references.values():
                if not ref.valid_this_poll:
                    continue
                if not on_change or ref.val != ref.last_val:
                    ref_val = (
                        round(ref.val, FLOAT_TYPE_PRECISION)
                        if isinstance(ref.val, float)
                        else ref.val
                    )
                    key = f"{ref.name}|{ref.unit}" if ref.unit else ref.name
                    payload[key] = ref_val

                    if self.mqtt_single_publish:
                        topic = f"{self.mqtt_publish_topic_pattern.replace('{{device_name}}', dev.name)}/{ref.name}"
                        if isinstance(ref_val, list):
                            for i, entry in enumerate(ref_val):
                                self.mqtt_handler.publish(f"{topic}/{i}", entry)
                        else:
                            self.mqtt_handler.publish(topic, ref_val)

            if payload and not self.mqtt_single_publish:
                if timestamp is not None:
                    payload["timestamp"] = timestamp
                topic = self.mqtt_publish_topic_pattern.replace(
                    "{{device_name}}", dev.name
                )
                self.mqtt_handler.publish(topic, json.dumps(payload))

    def publish_diagnostics(self):
        if not self.mqtt_handler:
            return
        if not self.mqtt_diagnostics_topic_pattern:
            return
        for dev in self.deviceList:
            payload = {
                "poll_count": dev.pollCount,
                "error_count": dev.errorCount,
                "last_poll_success": dev.pollSuccess,
            }
            topic = self.mqtt_diagnostics_topic_pattern.replace(
                "{{device_name}}", dev.name
            )
            self.mqtt_handler.publish(topic, json.dumps(payload))

    def export(self, file, timestamp=None):
        return export_modbus_handlers([self], file, timestamp)

    def close(self):
        self.disconnect()
        self.modbus_client = None

    def get_device_list(self) -> List[Device]:
        return self.deviceList


def setup_modbus_handlers(args, mqtt_handler: Optional[MqttHandler] = None):
    modbus_handlers = []
    current_handler = None
    device_names = set()
    try:
        for config_file in args.config:
            current_handler = ModbusHandler(
                _create_modbus_client(args),
                config_file,
                mqtt_handler,
                timeout=args.timeout,
                interval=args.interval,
                daemon=args.daemon,
                mqtt_publish_topic_pattern=args.mqtt_publish_topic_pattern,
                mqtt_diagnostics_topic_pattern=args.mqtt_diagnostics_topic_pattern,
                mqtt_single_publish=args.mqtt_single,
                autoremove=args.autoremove,
            )
            if current_handler.load_config():
                names = {device.name for device in current_handler.get_device_list()}
                duplicates = names & device_names
                if duplicates:
                    raise ValueError(
                        "Duplicate device names across configurations: "
                        + ", ".join(sorted(duplicates))
                    )
                device_names.update(names)
                modbus_handlers.append(current_handler)
            else:
                current_handler.close()
            current_handler = None
    except Exception:
        for handler in (
            [current_handler] if current_handler is not None else []
        ) + modbus_handlers:
            try:
                handler.close()
            except Exception:
                logging.getLogger(__name__).exception(
                    "Failed to close handler after setup error"
                )
        raise
    return modbus_handlers


def _valid_write_address(address) -> bool:
    return type(address) is int and 0 <= address <= 65535


def _create_modbus_client(args):
    transport = _determine_transport(args)

    if transport == "serial":
        framer = _resolve_framer("serial", args.framer)
        return _create_serial_client(args, args.serial, framer)

    if transport == "tcp":
        framer = _resolve_framer("tcp", args.framer)
        return _create_tcp_client(args, framer)

    if transport == "udp":
        framer = _resolve_framer("udp", args.framer)
        return _create_udp_client(args, framer)

    raise ValueError("No communication method specified.")


def _create_serial_client(args, port, framer):
    if not port:
        raise ValueError("Serial port/URL must be provided for serial transports.")
    parity = _get_parity(args.serial_parity)
    client_args = {
        "port": port,
        "baudrate": int(args.serial_baud),
        "bytesize": 8,
        "parity": parity,
        "stopbits": 1,
        "timeout": args.timeout,
    }
    if framer:
        client_args["framer"] = framer
    return ModbusSerialClient(**client_args)


def _create_tcp_client(args, framer):
    client_args = {
        "host": args.tcp,
        "port": args.tcp_port,
        "timeout": args.timeout,
    }
    if framer:
        client_args["framer"] = framer
    return ModbusTcpClient(**client_args)


def _create_udp_client(args, framer):
    client_args = {
        "host": args.udp,
        "port": args.udp_port,
        "timeout": args.timeout,
    }
    if framer:
        client_args["framer"] = framer
    return ModbusUdpClient(**client_args)


def _get_parity(serial_parity):
    if serial_parity == "odd":
        return "O"
    elif serial_parity == "even":
        return "E"
    else:
        return "N"


def _determine_transport(args):
    transports = []
    if args.serial:
        transports.append("serial")
    if args.tcp:
        transports.append("tcp")
    if args.udp:
        transports.append("udp")

    if not transports:
        raise ValueError("No communication method specified.")
    if len(transports) > 1:
        raise ValueError(
            "Multiple communication methods specified; pick one of --serial/--tcp/--udp (alias: --rtu)."
        )
    return transports[0]


def _resolve_framer(transport, framer_name):
    """Resolve the requested framer to a concrete class."""

    if framer_name == "default":
        # Let pymodbus choose its transport defaults:
        # Serial -> RTU framer; TCP/UDP -> socket framer.
        return None

    framer_map = {
        "rtu": ModbusRtuFramer,
        "ascii": ModbusAsciiFramer,
        "socket": ModbusSocketFramer,
    }
    allowed = {
        "serial": {"rtu", "ascii"},
        "tcp": {"socket"},
        "udp": {"socket"},
    }

    if transport in ("tcp", "udp"):
        transport_key = transport
    else:
        transport_key = "serial"

    if framer_name not in allowed[transport_key]:
        raise ValueError(
            f"Framer '{framer_name}' is not valid for transport '{transport_key}'."
        )

    framer_cls = framer_map.get(framer_name)
    if framer_cls is None:
        raise ValueError(
            f"Framer '{framer_name}' is not available with the installed pymodbus version."
        )
    return framer_cls
