import csv
import json
import logging
import math
import time

import requests
from prettytable import PrettyTable
from pymodbus.client import ModbusSerialClient, ModbusTcpClient, ModbusUdpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder

from modpoll.mqtt_task import mqttc_publish

args = None
log = None
master = None
deviceList = []
event_exit = None


class Device:
    def __init__(self, device_name: str, device_id: int):
        self.name = device_name
        self.devid = device_id
        self.pollerList = []
        self.references = {}
        self.errorCount = 0
        self.pollCount = 0
        self.pollSuccess = False
        log.info(f"Adding new device {self.name}")

    def add_reference_mapping(self, ref):
        self.references[ref.name] = ref

    def update_reference(self, ref):
        self.references[ref.name].last_val = ref.last_val
        self.references[ref.name].val = ref.val


class Poller:
    def __init__(
        self, device, function_code: int, start_address: int, size: int, endian: str
    ):
        self.device = device
        self.fc = function_code
        self.start_address = start_address
        self.size = size
        self.endian = endian.lower()
        self.readableReferences = []
        self.disabled = False
        self.failcounter = 0

    def poll(self):
        if self.disabled or not master:
            return
        try:
            result = None
            data = None
            if self.fc == 1:
                result = master.read_coils(
                    self.start_address, self.size, slave=self.device.devid
                )
                if not result.isError():
                    data = result.bits
            elif self.fc == 2:
                result = master.read_discrete_inputs(
                    self.start_address, self.size, slave=self.device.devid
                )
                if not result.isError():
                    data = result.bits
            elif self.fc == 3:
                result = master.read_holding_registers(
                    self.start_address, self.size, slave=self.device.devid
                )
                if not result.isError():
                    data = result.registers
            elif self.fc == 4:
                result = master.read_input_registers(
                    self.start_address, self.size, slave=self.device.devid
                )
                if not result.isError():
                    data = result.registers
            if not data:
                self.update_statistics(False)
                log.error(
                    f"Reading device:{self.device.name}, FuncCode:{self.fc}, "
                    f"Start_address:{self.start_address}, Size:{self.size}... ERROR"
                )
                log.debug(result)
                return
            if "BE_BE" == self.endian.upper():
                if self.fc == 1 or self.fc == 2:
                    decoder = BinaryPayloadDecoder.fromCoils(data, byteorder=Endian.BIG)
                else:
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        data, byteorder=Endian.BIG, wordorder=Endian.BIG
                    )
            elif "LE_BE" == self.endian.upper():
                if self.fc == 1 or self.fc == 2:
                    decoder = BinaryPayloadDecoder.fromCoils(
                        data, byteorder=Endian.LITTLE
                    )
                else:
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        data, byteorder=Endian.LITTLE, wordorder=Endian.BIG
                    )
            elif "LE_LE" == self.endian.upper():
                if self.fc == 1 or self.fc == 2:
                    decoder = BinaryPayloadDecoder.fromCoils(
                        data, byteorder=Endian.LITTLE
                    )
                else:
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        data, byteorder=Endian.LITTLE, wordorder=Endian.LITTLE
                    )
            else:
                if self.fc == 1 or self.fc == 2:
                    decoder = BinaryPayloadDecoder.fromCoils(data, byteorder=Endian.BIG)
                else:
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        data, byteorder=Endian.BIG, wordorder=Endian.LITTLE
                    )
            cur_ref = self.start_address
            for ref in self.readableReferences:
                if self.fc == 1 or self.fc == 2:
                    ref_count = math.ceil(self.size / 8)
                else:
                    ref_count = self.size
                # skip all registers before current reference address
                while cur_ref < ref.address:
                    if self.fc == 1 or self.fc == 2:
                        decoder.skip_bytes(1)
                    else:
                        decoder.skip_bytes(2)
                    cur_ref += 1
                if cur_ref >= self.start_address + ref_count:
                    break
                if "uint16" == ref.dtype:
                    ref.update_value(decoder.decode_16bit_uint())
                    cur_ref += ref.ref_width
                elif "int16" == ref.dtype:
                    ref.update_value(decoder.decode_16bit_int())
                    cur_ref += ref.ref_width
                elif "uint32" == ref.dtype:
                    ref.update_value(decoder.decode_32bit_uint())
                    cur_ref += ref.ref_width
                elif "int32" == ref.dtype:
                    ref.update_value(decoder.decode_32bit_int())
                    cur_ref += ref.ref_width
                elif "uint64" == ref.dtype:
                    ref.update_value(decoder.decode_64bit_uint())
                    cur_ref += ref.ref_width
                elif "int64" == ref.dtype:
                    ref.update_value(decoder.decode_64bit_int())
                    cur_ref += ref.ref_width
                elif "float32" == ref.dtype:
                    ref.update_value(decoder.decode_32bit_float())
                    cur_ref += ref.ref_width
                elif "float64" == ref.dtype:
                    ref.update_value(decoder.decode_64bit_float())
                    cur_ref += ref.ref_width
                elif "bool8" == ref.dtype or "bool" == ref.dtype:
                    v = decoder.decode_bits()
                    ref.update_value(v)
                    cur_ref += ref.ref_width
                elif "bool16" == ref.dtype:
                    ref.update_value(decoder.decode_bits() + decoder.decode_bits())
                    cur_ref += ref.ref_width
                elif ref.dtype.startswith("string"):
                    ref.update_value(decoder.decode_string())
                    cur_ref += ref.ref_width
                else:
                    decoder.decode_16bit_uint()
                    cur_ref += 1
            self.device.update_reference(ref)
            self.update_statistics(True)
            log.info(
                f"Reading device:{self.device.name}, FuncCode:{self.fc}, "
                f"Start_address:{self.start_address}, Size:{self.size}... SUCCESS"
            )
            return True
        except ModbusException as ex:
            self.update_statistics(False)
            log.warning(
                f"Reading device:{self.device.name}, FuncCode:{self.fc}, "
                f"Start_address:{self.start_address}, Size:{self.size}... FAILED"
            )
            log.debug(ex)
            return False

    def add_readable_reference(self, ref):
        if ref not in self.readableReferences:
            self.readableReferences.append(ref)

    def update_statistics(self, success):
        self.device.pollCount += 1
        if success:
            self.failcounter = 0
            self.device.pollSuccess = True
        else:
            self.failcounter += 1
            self.device.errorCount += 1
            self.device.pollSuccess = False
            if args.autoremove and self.failcounter >= 3:
                self.disabled = True
                log.info(
                    f"Poller {self.name} disabled (functioncode: {self.fc}, "
                    f"start_address: {self.start_address}, size: {self.size})."
                )


class Reference:
    def __init__(
        self, device, ref_name: str, address: int, dtype: str, rw: str, unit, scale
    ):
        self.device = device
        self.name = ref_name
        self.address = address
        self.dtype = dtype.lower()
        if "int16" == dtype:
            self.ref_width = 1
        elif "uint16" == dtype:
            self.ref_width = 1
        elif "int32" == dtype:
            self.ref_width = 2
        elif "uint32" == dtype:
            self.ref_width = 2
        elif "int64" == dtype:
            self.ref_width = 4
        elif "uint64" == dtype:
            self.ref_width = 4
        elif "float32" == dtype:
            self.ref_width = 2
        elif "float64" == dtype:
            self.ref_width = 4
        elif "bool8" == dtype or "bool" == dtype:
            self.ref_width = 1
        elif "bool16" == dtype:
            self.ref_width = 2
        elif dtype.startswith("string"):
            try:
                self.ref_width = int(dtype[6:9])
            except ValueError:
                self.ref_width = 2
            if self.ref_width > 100:
                log.warning("Data type string: length must be less than 100")
                self.ref_width = 100
            if math.fmod(self.ref_width, 2) != 0:
                self.ref_width = self.ref_width - 1
                log.warning("Data type string: length must be divisible by 2")
        else:
            log.error(f"Unknown data type: {dtype}")
        self.rw = rw.lower()
        self.unit = unit
        self.scale = scale
        self.val = None
        self.last_val = None

    def check_sanity(self, reference, size):
        if self.address not in range(reference, size + reference):
            return False
        if self.address + self.ref_width - 1 not in range(reference, size + reference):
            return False
        return True

    def update_value(self, v):
        if self.scale:
            try:
                v = v * float(self.scale)
            except ValueError:
                pass
        self.last_val = self.val
        self.val = v

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Reference):
            return self.address == other.address
        return False


def parse_config(csv_reader):
    current_device = None
    current_poller = None
    try:
        for row in csv_reader:
            if not row or len(row) == 0:
                continue
            if "device" in row[0].lower():
                device_name = row[1]
                device_id = int(row[2])
                current_device = Device(device_name, device_id)
                deviceList.append(current_device)
            elif "poll" in row[0].lower():
                fc = row[1].lower()
                start_address = int(row[2])
                size = int(row[3])
                endian = row[4]
                current_poller = None
                if not current_device:
                    log.error("No device to add poller.")
                    continue
                if "coil" == fc:
                    function_code = 1
                    if (
                        size > 2000
                    ):  # some implementations don't seem to support 2008 coils/inputs
                        log.error("Too many coils (max. 2000). Ignoring poller.")
                        continue
                elif "discrete_input" == fc:
                    function_code = 2
                    if size > 2000:
                        log.error(
                            "Too many discrete inputs (max. 2000). Ignoring poller."
                        )
                        continue
                elif "holding_register" == fc:
                    function_code = 3
                    if (
                        size > 123
                    ):  # applies to TCP, RTU should support 125 registers. But let's be safe.
                        log.error(
                            "Too many holding registers (max. 123). Ignoring poller."
                        )
                        continue
                elif "input_register" == fc:
                    function_code = 4
                    if size > 123:
                        log.error(
                            f"Too many input registers (max. 123): {size}. Ignoring poller."
                        )
                        continue
                else:
                    log.warning(f"Unknown function code ({fc}) ignoring poller.")
                    continue
                current_poller = Poller(
                    current_device, function_code, start_address, size, endian
                )
                current_device.pollerList.append(current_poller)
                log.info(
                    f"Add poller (start_address={current_poller.start_address}, size={current_poller.size}) "
                    f"to device {current_device.name}"
                )
            elif "ref" in row[0].lower():
                ref_name = row[1].replace(" ", "_")
                address = int(row[2])
                dtype = row[3].lower()
                rw = row[4] or "r"
                try:
                    unit = row[5]
                except IndexError:
                    unit = None
                try:
                    scale = float(row[6])
                except Exception:
                    scale = None
                if not current_device or not current_poller:
                    log.debug(f"No device/poller for reference {ref_name}.")
                    continue
                ref = Reference(
                    current_poller.device, ref_name, address, dtype, rw, unit, scale
                )
                if ref in current_poller.readableReferences:
                    log.warning(f"Reference {ref.name} is already added, ignoring it.")
                    continue
                if not ref.check_sanity(
                    current_poller.start_address, current_poller.size
                ):
                    log.warning(
                        f"Reference {ref.name} failed to pass sanity check, ignoring it."
                    )
                    continue
                if "r" in rw.lower():
                    current_poller.add_readable_reference(ref)
                current_device.add_reference_mapping(ref)
                log.debug(f"Add reference {ref.name} to device {current_device.name}")
    except Exception:
        log.error("Failed to parse the config file. Exiting.")
        exit(1)


def load_config(file):
    try:
        with requests.Session() as s:
            response = s.get(file)
            decoded_content = response.content.decode("utf-8")
            csv_reader = csv.reader(decoded_content.splitlines(), delimiter=",")
            parse_config(csv_reader)
    except requests.RequestException:
        with open(file, "r") as f:
            f.seek(0)
            csv_reader = csv.reader(f)
            parse_config(csv_reader)


def modbus_setup(config, event):
    global args
    args = config
    global log
    log = logging.getLogger(__name__)
    global event_exit
    event_exit = event
    global master

    log.info(f"Loading config from: {args.config}")
    load_config(args.config)
    if len(deviceList) > 0:
        log.info(f"Polling {len(deviceList)} device(s)...")
    else:
        log.error("No device found in the config file. Exiting.")
        exit(1)
    if args.rtu:
        if args.rtu_parity == "odd":
            parity = "O"
        elif args.rtu_parity == "even":
            parity = "E"
        else:
            parity = "N"
        master = ModbusSerialClient(
            method="rtu",
            port=args.rtu,
            stopbits=1,
            bytesize=8,
            parity=parity,
            baudrate=int(args.rtu_baud),
            timeout=args.timeout,
            reset_socket=True,
        )
    elif args.tcp:
        master = ModbusTcpClient(
            args.tcp, args.tcp_port, timeout=args.timeout, reset_socket=True
        )
    elif args.udp:
        master = ModbusUdpClient(
            args.udp, args.udp_port, timeout=args.timeout, reset_socket=True
        )
    else:
        log.error(
            "You must specify a modbus access method, either --rtu, --tcp or --udp"
        )
        return False
    return True


def modbus_poll():
    if not master:
        return
    master.connect()
    time.sleep(args.delay)
    log.debug(f"Master connected. Delay of {args.delay} seconds.")
    for dev in deviceList:
        log.debug(f"Polling device {dev.name} ...")
        for p in dev.pollerList:
            if not p.disabled:
                p.poll()
                if event_exit.is_set():
                    master.close()
                    return
                event_exit.wait(timeout=args.interval)
    master.close()
    # printout result, if -p or --print-result are set
    if args.print_result:
        modbus_print()


def modbus_write_coil(device_name, address: int, value):
    if not master:
        return False
    master.connect()
    time.sleep(args.delay)
    log.debug(f"Master connected. Delay of {args.delay} seconds.")
    for d in deviceList:
        if d.name == device_name:
            log.info(
                f"Writing coil(s): device={device_name}, address={address}, value={value}"
            )
            if isinstance(value, int):
                result = master.write_coil(address, value, slave=d.devid)
            elif isinstance(value, list):
                result = master.write_coils(address, value, slave=d.devid)
            return result.function_code < 0x80
    master.close()
    return False


def modbus_write_register(device_name, address: int, value):
    if not master:
        return False
    master.connect()
    time.sleep(args.delay)
    log.debug(f"Master connected. Delay of {args.delay} seconds.")
    for d in deviceList:
        if d.name == device_name:
            log.info(
                f"Writing register(s): device={device_name}, address={address}, value={value}"
            )
            if isinstance(value, int):
                result = master.write_register(address, value, slave=d.devid)
            elif isinstance(value, list):
                result = master.write_registers(address, value, slave=d.devid)
            return result.function_code < 0x80
    master.close()
    return False


def modbus_print():
    for dev in deviceList:
        print(f"===== references from device: {dev.name} =====")
        if not dev.pollSuccess:
            print(f"Failed to poll device: {dev.name}")
            continue
        table = PrettyTable(["name", "unit", "address", "value"])
        for ref in dev.references.values():
            if isinstance(ref.val, float):
                value = f"{ref.val:g}"
            else:
                value = ref.val
            row = [ref.name, ref.unit, ref.address, value]
            table.add_row(row)
        print(table)
    print("Done.\n")


def modbus_publish(timestamp=None, on_change=False):
    for dev in deviceList:
        if not dev.pollSuccess:
            log.debug(f"Skip publishing for disconnected device: {dev.name}")
            continue
        log.debug(f"Publishing data for device: {dev.name} ...")
        payload = {}
        for ref in dev.references.values():
            if on_change and ref.val == ref.last_val:
                continue
            if ref.unit:
                payload[f"{ref.name}|{ref.unit}"] = ref.val
            else:
                payload[f"{ref.name}"] = ref.val
            if args.mqtt_single:
                topic = f"{args.mqtt_topic_prefix}{dev.name}/{ref.name}"
                if isinstance(ref.val, list):
                    for i, ref_val_entry in enumerate(ref.val):
                        mqttc_publish(
                            topic + "/" + str(i), ref_val_entry, qos=args.mqtt_qos
                        )
                else:
                    mqttc_publish(topic, ref.val, qos=args.mqtt_qos)
        if timestamp:
            payload["timestamp_ms"] = int(timestamp * 1000)
        if not args.mqtt_single:
            topic = f"{args.mqtt_topic_prefix}{dev.name}"
            mqttc_publish(topic, json.dumps(payload), qos=args.mqtt_qos)


def modbus_publish_diagnostics():
    for dev in deviceList:
        log.debug(f"Publishing diagnostics for device {dev.name} ...")
        payload = {"pollCount": dev.pollCount, "errorCount": dev.errorCount}
        topic = f"{args.mqtt_topic_prefix}diagnostics/{dev.name}"
        mqttc_publish(topic, json.dumps(payload), qos=args.mqtt_qos)


def modbus_export(file, timestamp=None):
    if timestamp:
        if file.endswith(".csv"):
            file = file[:-4]
        file += "_" + str(int(timestamp * 1000))
        file += ".csv"
    else:
        if not file.endswith(".csv"):
            file += ".csv"
    with open(file, "w") as f:
        writer = csv.writer(f)
        for dev in deviceList:
            log.info(f"Exporting data for device {dev.name} ...")
            header = ["name", "unit", "address", "value"]
            writer.writerow(header)
            for ref in dev.references.values():
                row = [ref.name, ref.unit, ref.address, ref.val]
                writer.writerow(row)
    log.info(f"Saved references/registers to {file}")


def modbus_close():
    if master:
        master.close()
