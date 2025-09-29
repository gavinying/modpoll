import csv
import json
import logging
import math
from typing import List, Optional

import requests
from prettytable import PrettyTable
from pymodbus.client import ModbusSerialClient, ModbusTcpClient, ModbusUdpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder

from .utils import on_threading_event, delay_thread
from .mqtt_task import MqttHandler


FLOAT_TYPE_PRECISION = 3
CONFIG_DEVICE_COL_MIN = 3
CONFIG_POLL_COL_MIN = 5
CONFIG_REF_COL_MIN = 5


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
            if self.fc == 1:
                result = master.read_coils(
                    self.start_address, self.size, slave=self.device.devid
                )
            elif self.fc == 2:
                result = master.read_discrete_inputs(
                    self.start_address, self.size, slave=self.device.devid
                )
            elif self.fc == 3:
                result = master.read_holding_registers(
                    self.start_address, self.size, slave=self.device.devid
                )
            elif self.fc == 4:
                result = master.read_input_registers(
                    self.start_address, self.size, slave=self.device.devid
                )

            if result and not result.isError():
                data = result.bits if self.fc in (1, 2) else result.registers
                decoder = self._get_decoder(data)
                cur_ref = self.start_address
                for ref in self.readableReferences:
                    if self.fc in (1, 2):
                        ref_count = math.ceil(self.size / 8)
                    else:
                        ref_count = self.size
                    # skip all registers before current reference address
                    while cur_ref < ref.address:
                        if self.fc in (1, 2):
                            decoder.skip_bytes(1)
                        else:
                            decoder.skip_bytes(2)
                        cur_ref += 1
                    if cur_ref >= self.start_address + ref_count:
                        break
                    try:
                        self._decode_and_update_reference(ref, decoder)
                    except UnicodeDecodeError:
                        self.logger.error(
                            f"Failed to decode unicode string for reference: {ref.name}, check the reference address or length of string in configuration file"
                        )
                    except:
                        self.logger.error(
                            f"Failed to decode value for reference: {ref.name}"
                        )
                    cur_ref += ref.ref_width
                self.update_statistics(True)
                return True
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
        address: int,
        dtype: str,
        rw: str,
        unit: str,
        scale: float,
    ):
        self.device = device
        self.name = ref_name
        self.address = address
        self.dtype = dtype.lower()
        self.ref_width = self._get_ref_width()
        self.rw = rw.lower()
        self.unit = unit
        self.scale = scale
        self.val = None
        self.last_val = None

    def __eq__(self, other):
        if isinstance(other, Reference):
            return self.address == other.address
        return False

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
                return (width + 1) // 2
            except ValueError:
                return 1
        else:
            return 1

    def check_sanity(self, reference: int, size: int) -> bool:
        return self.address in range(
            reference, size + reference
        ) and self.address + self.ref_width - 1 in range(reference, size + reference)

    def update_value(self, v):
        if self.scale:
            try:
                v = v * float(self.scale)
            except (ValueError, TypeError):
                pass
        self.last_val = self.val
        self.val = v


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
        self.connected = False
        self.deviceList: List[Device] = []
        self.logger = logging.getLogger(__name__)

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
        try:
            for row in csv_reader:
                if not row or all(cell.strip() == "" for cell in row):
                    continue
                if "device" in row[0].lower():
                    if len(row) < CONFIG_DEVICE_COL_MIN:
                        self.logger.error("Invalid device configuration")
                        continue
                    device_name = row[1].strip()
                    try:
                        device_id = int(row[2], 0)
                    except ValueError:
                        self.logger.error(f"Invalid device ID for {device_name}")
                        continue
                    current_device = Device(device_name, device_id)
                    device_list.append(current_device)
                elif "poll" in row[0].lower():
                    if not current_device:
                        self.logger.error("No device to add poller.")
                        continue
                    current_poller = self._create_poller(row, current_device)
                    if current_poller:
                        current_device.pollerList.append(current_poller)
                elif "ref" in row[0].lower():
                    if not current_device or not current_poller:
                        self.logger.debug(
                            f"No device/poller for reference {row[1] if len(row) > 1 else 'unknown'}."
                        )
                        continue
                    ref = self._create_reference(row, current_device)
                    if ref and self._validate_reference(ref, current_poller):
                        if "r" in ref.rw.lower():
                            current_poller.add_readable_reference(ref)
                        current_device.add_reference_mapping(ref)
                        self.logger.debug(
                            f"Add reference {ref.name} to device {current_device.name}"
                        )
            return device_list
        except Exception as e:
            self.logger.error(f"Error parsing config: {e}")
            return []

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
        endian = row[4]
        function_code = self._get_function_code(fc)
        if function_code is None:
            return None
        if not self._validate_poller_size(function_code, size):
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
            address = int(row[2], 0)
        except ValueError:
            self.logger.error(f"Invalid address for reference {ref_name}")
            return None
        dtype = row[3].lower()
        rw = row[4] or "r"
        unit = row[5] if len(row) > 5 else None
        try:
            scale = float(row[6]) if len(row) > 6 else None
        except ValueError:
            scale = None
        return Reference(current_device, ref_name, address, dtype, rw, unit, scale)

    def _validate_reference(self, ref, current_poller):
        if ref in current_poller.readableReferences:
            self.logger.warning(f"Reference {ref.name} is already added, ignoring it.")
            return False
        if not ref.check_sanity(current_poller.start_address, current_poller.size):
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

    def poll(self):
        if not self.connect():
            self.logger.error("Failed to connect to Modbus client")
            return
        try:
            for dev in self.deviceList:
                self.logger.debug(f"Polling device {dev.name} ...")
                for p in dev.pollerList:
                    if not p.disabled:
                        p.poll(self.modbus_client)
                        if on_threading_event():
                            return
                        delay_thread(timeout=self.interval)
        finally:
            self.disconnect()
            if not self.daemon:
                self.print_results()

    def write_coil(self, device_name: str, address: int, value) -> bool:
        for dev in self.deviceList:
            if dev.name == device_name:
                try:
                    if not self.connect():
                        return False
                    result = self.modbus_client.write_coil(
                        address, value, slave=dev.devid
                    )
                    return not result.isError()
                except ModbusException as e:
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
                    if not self.connect():
                        return False
                    result = self.modbus_client.write_register(
                        address, value, slave=dev.devid
                    )
                    return not result.isError()
                except ModbusException as e:
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
                    if isinstance(ref.val, float)
                    else ref.val
                )
                table.add_row([ref.name, value, ref.unit or ""])
            print(f"\nDevice: {dev.name}")
            print(table)

    def publish_data(self, timestamp=None, on_change=False):
        if not self.mqtt_handler or not self.mqtt_publish_topic_pattern:
            return

        for dev in self.deviceList:
            if not dev.pollSuccess:
                self.logger.debug(
                    f"Skip publishing for disconnected device: {dev.name}"
                )
                continue

            payload = {}
            for ref in dev.references.values():
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
        data = {}
        for dev in self.deviceList:
            dev_data = {}
            for ref in dev.references.values():
                dev_data[ref.name] = ref.val
            if timestamp:
                dev_data["timestamp"] = timestamp
            data[dev.name] = dev_data
        try:
            with open(file, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            self.logger.error(f"Error exporting data: {e}")

    def close(self):
        self.disconnect()
        self.modbus_client = None

    def get_device_list(self) -> List[Device]:
        return self.deviceList


def setup_modbus_handlers(args, mqtt_handler: Optional[MqttHandler] = None):
    modbus_handlers = []
    modbus_client = _create_modbus_client(args)
    for config_file in args.config:
        modbus_handler = ModbusHandler(
            modbus_client,
            config_file,
            mqtt_handler,
            timeout=args.timeout,
            interval=args.interval,
            daemon=args.daemon,
            mqtt_publish_topic_pattern=args.mqtt_publish_topic_pattern,
            mqtt_diagnostics_topic_pattern=args.mqtt_diagnostics_topic_pattern,
            mqtt_single_publish=args.mqtt_single,
        )
        if modbus_handler.load_config():
            modbus_handlers.append(modbus_handler)
        else:
            modbus_handler.close()
    return modbus_handlers


def _create_modbus_client(args):
    if args.rtu:
        return _create_rtu_client(args)
    elif args.tcp:
        return _create_tcp_client(args)
    elif args.udp:
        return _create_udp_client(args)
    else:
        raise ValueError("No communication method specified.")


def _create_rtu_client(args):
    parity = _get_parity(args.rtu_parity)
    client_args = {
        "port": args.rtu,
        "baudrate": int(args.rtu_baud),
        "bytesize": 8,
        "parity": parity,
        "stopbits": 1,
        "timeout": args.timeout,
    }
    if args.framer != "default":
        client_args["framer"] = args.framer
    return ModbusSerialClient(**client_args)


def _create_tcp_client(args):
    client_args = {
        "host": args.tcp,
        "port": args.tcp_port,
        "timeout": args.timeout,
    }
    if args.framer != "default":
        client_args["framer"] = args.framer
    return ModbusTcpClient(**client_args)


def _create_udp_client(args):
    client_args = {
        "host": args.udp,
        "port": args.udp_port,
        "timeout": args.timeout,
    }
    if args.framer != "default":
        client_args["framer"] = args.framer
    return ModbusUdpClient(**client_args)


def _get_parity(rtu_parity):
    if rtu_parity == "odd":
        return "O"
    elif rtu_parity == "even":
        return "E"
    else:
        return "N"
