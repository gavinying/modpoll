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

from .mqtt_task import MqttHandler


FLOAT_TYPE_PRECISION = 3


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

    def update_reference(self, ref):
        if ref.name in self.references:
            existing_ref = self.references[ref.name]
            existing_ref.last_val = existing_ref.val
            existing_ref.val = ref.val


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

    def poll(self, master) -> bool:
        if self.disabled or not master:
            return False
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

            if result is None or result.isError():
                self.update_statistics(False)
                return False

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
                self._decode_and_update_reference(ref, decoder)
                cur_ref += ref.ref_width
                self.device.update_reference(ref)
            self.update_statistics(True)
            return True
        except ModbusException:
            self.update_statistics(False)
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
        else:
            decoder.skip_bytes(2)  # Skip unknown types

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

    def __eq__(self, other):
        if isinstance(other, Reference):
            return self.address == other.address
        return False


class ModbusMaster:
    def __init__(
        self, args, event, config_file: str, mqtt_handler: Optional[MqttHandler] = None
    ):
        self.args = args
        self.config_file = config_file
        self.mqtt_handler = mqtt_handler
        self.logger = logging.getLogger(__name__)
        self.event_exit = event
        self.master = None
        self.connected = False
        self.deviceList: List[Device] = []

    def load_config(self, file) -> bool:
        try:
            with requests.Session() as s:
                response = s.get(file)
                response.raise_for_status()
                decoded_content = response.content.decode("utf-8")
                csv_reader = csv.reader(decoded_content.splitlines(), delimiter=",")
                self.deviceList = self.parse_config(csv_reader)
        except requests.RequestException:
            try:
                with open(file, "r") as f:
                    csv_reader = csv.reader(f)
                    self.deviceList = self.parse_config(csv_reader)
            except IOError as e:
                self.logger.error(f"Error opening file: {e}")
                return False
        return bool(self.deviceList)

    def parse_config(self, csv_reader) -> List[Device]:
        device_list = []
        current_device = None
        current_poller = None
        try:
            for row in csv_reader:
                if not row:
                    continue
                if "device" in row[0].lower():
                    device_name = row[1]
                    device_id = int(row[2])
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
                        self.logger.debug(f"No device/poller for reference {row[1]}.")
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
        if len(row) < 5:
            self.logger.error("Invalid poller configuration")
            return None
        fc = row[1].lower()
        try:
            start_address = int(row[2])
            size = int(row[3])
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
        if len(row) < 5:
            self.logger.error("Invalid reference configuration")
            return None
        ref_name = row[1].replace(" ", "_")
        try:
            address = int(row[2])
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

    def setup(self) -> bool:
        self.logger.info(f"Loading config from: {self.config_file}")
        if self.load_config(self.config_file):
            self.logger.info(f"Added {len(self.deviceList)} device(s)...")
        else:
            self.logger.error("No device found in the config file. Skipping.")
            return False
        if self.args.rtu:
            parity = self._get_parity()
            self.master = self._create_rtu_client(parity)
        elif self.args.tcp:
            self.master = self._create_tcp_client()
        elif self.args.udp:
            self.master = self._create_udp_client()
        else:
            self.logger.error("No communication method specified.")
            return False
        return True

    def _get_parity(self):
        if self.args.rtu_parity == "odd":
            return "O"
        elif self.args.rtu_parity == "even":
            return "E"
        else:
            return "N"

    def _create_rtu_client(self, parity):
        client_args = {
            "port": self.args.rtu,
            "baudrate": int(self.args.rtu_baud),
            "bytesize": 8,
            "parity": parity,
            "stopbits": 1,
            "timeout": self.args.timeout,
        }
        if self.args.framer != "default":
            client_args["framer"] = self.args.framer
        return ModbusSerialClient(**client_args)

    def _create_tcp_client(self):
        client_args = {
            "host": self.args.tcp,
            "port": self.args.tcp_port,
            "timeout": self.args.timeout,
        }
        if self.args.framer != "default":
            client_args["framer"] = self.args.framer
        return ModbusTcpClient(**client_args)

    def _create_udp_client(self):
        client_args = {
            "host": self.args.udp,
            "port": self.args.udp_port,
            "timeout": self.args.timeout,
        }
        if self.args.framer != "default":
            client_args["framer"] = self.args.framer
        return ModbusUdpClient(**client_args)

    def connect(self) -> bool:
        self.connected = self.master.connect()
        return self.connected

    def disconnect(self):
        if self.master:
            self.master.close()
            self.connected = False

    def poll(self):
        self.connect()
        for dev in self.deviceList:
            self.logger.debug(f"Polling device {dev.name} ...")
            for p in dev.pollerList:
                if not p.disabled:
                    p.poll(self.master)
                    if self.event_exit.is_set():
                        self.disconnect()
                        return
                    self.event_exit.wait(timeout=self.args.interval)
        self.disconnect()
        if not self.args.daemon:
            self.print_results()

    def write_coil(self, device_name: str, address: int, value) -> bool:
        for dev in self.deviceList:
            if dev.name == device_name:
                try:
                    self.connect()
                    result = self.master.write_coil(address, value, slave=dev.devid)
                    self.disconnect()
                    return not result.isError()
                except ModbusException as e:
                    self.logger.error(f"Error writing coil: {e}")
                    return False
        return False

    def write_register(self, device_name, address: int, value) -> bool:
        for dev in self.deviceList:
            if dev.name == device_name:
                try:
                    self.connect()
                    result = self.master.write_register(address, value, slave=dev.devid)
                    self.disconnect()
                    return not result.isError()
                except ModbusException as e:
                    self.logger.error(f"Error writing register: {e}")
                    return False
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
        if not self.mqtt_handler:
            return
        if not self.args.mqtt_publish_topic_pattern:
            return
        for dev in self.deviceList:
            payload = {}
            for ref in dev.references.values():
                if not on_change or ref.val != ref.last_val:
                    value = (
                        round(ref.val, FLOAT_TYPE_PRECISION)
                        if isinstance(ref.val, float)
                        else ref.val
                    )
                    payload[ref.name] = value
            if payload:
                if timestamp:
                    payload["timestamp"] = timestamp
                topic = self.args.mqtt_publish_topic_pattern.replace(
                    "<device_name>", dev.name
                )
                self.mqtt_handler.mqttc_publish(topic, json.dumps(payload))

    def publish_diagnostics(self):
        if not self.mqtt_handler:
            return
        if not self.args.mqtt_diagnostics_topic_pattern:
            return
        for dev in self.deviceList:
            payload = {
                "poll_count": dev.pollCount,
                "error_count": dev.errorCount,
                "last_poll_success": dev.pollSuccess,
            }
            topic = self.args.mqtt_diagnostics_topic_pattern.replace(
                "<device_name>", dev.name
            )
            self.mqtt_handler.mqttc_publish(topic, json.dumps(payload))

    def export(self, file, timestamp=None):
        data = {}
        for dev in self.deviceList:
            dev_data = {}
            for ref in dev.references.values():
                dev_data[ref.name] = ref.val
            if timestamp:
                dev_data["timestamp"] = timestamp
            data[dev.name] = dev_data
        with open(file, "w") as f:
            json.dump(data, f, indent=2)

    def close(self):
        if self.master:
            self.master.close()
            self.connected = False
            self.master = None

    def get_device_list(self) -> List[Device]:
        return self.deviceList
