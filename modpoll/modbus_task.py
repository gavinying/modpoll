import csv
import json
import logging
import math
import time
import requests

from pymodbus.client.sync import ModbusSerialClient
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from prettytable import PrettyTable

from modpoll.mqtt_task import mqttc_publish

# global objects
args = None
log = None
master = None
deviceList = []
referenceList = []
pollers = []


class Device:
    def __init__(self, name, devid):
        self.name = name
        self.devid = devid
        self.occupiedTopics = []
        self.writableReferences = []
        self.errorCount = 0
        self.pollCount = 0
        self.next_due = time.time() + args.diagnostics_rate
        log.info(f"Added new device {self.name}")

    def publish_diagnostics(self):
        if args.diagnostics_rate > 0:
            now = time.time()
            if now > self.next_due:
                self.next_due = now + args.diagnostics_rate
                try:
                    error_rate = float(self.errorCount) / float(self.pollCount)
                except ValueError:
                    error_rate = 0
                mqttc_publish(
                    f"{args.mqtt_topic_prefix}{self.name}/diagnostics/error_rate", str(error_rate))
                mqttc_publish(
                    f"{args.mqtt_topic_prefix}{self.name}/diagnostics/total_poll", str(self.pollCount))
                self.pollCount = 0
                self.errorCount = 0


class Poller:
    def __init__(self, name, devid, reference, size, functioncode, endian):
        self.name = name
        self.devid = int(devid)
        self.reference = int(reference)
        self.size = int(size)
        self.functioncode = int(functioncode)
        self.endian = endian
        self.device = None
        self.readableReferences = []
        self.disabled = False
        self.failcounter = 0

        for myDev in deviceList:
            if myDev.name == self.name:
                self.device = myDev
                break
        if not self.device:
            device = Device(self.name, devid)
            deviceList.append(device)
            self.device = device

    def count_success(self, success):
        self.device.pollCount += 1
        if success:
            self.failcounter = 0
        else:
            self.failcounter += 1
            self.device.errorCount += 1
            if self.failcounter >= 3:
                if args.autoremove:
                    self.disabled = True
                    log.info(f"Poller {self.name} disabled (functioncode: {self.functioncode}, "
                             f"reference: {self.reference}, size: {self.size}).")
                # else:
                #     if master.connect():
                #         self.failcounter = 0
                #         log.info("Reconnecting to device... SUCCESS")
                #     else:
                #         log.info("Reconnecting to device... FAILED")

    def poll(self):
        if self.disabled or not master:
            return
        try:
            result = None
            data = None
            if self.functioncode == 1:
                result = master.read_coils(
                    self.reference, self.size, unit=self.devid)
                if not result.isError():
                    data = result.bits
            elif self.functioncode == 2:
                result = master.read_discrete_inputs(
                    self.reference, self.size, unit=self.devid)
                if not result.isError():
                    data = result.bits
            elif self.functioncode == 3:
                result = master.read_holding_registers(
                    self.reference, self.size, unit=self.devid)
                if not result.isError():
                    data = result.registers
            elif self.functioncode == 4:
                result = master.read_input_registers(
                    self.reference, self.size, unit=self.devid)
                if not result.isError():
                    data = result.registers
            if not data:
                self.count_success(False)
                log.warning(f"Reading device:{self.devid}, FuncCode:{self.functioncode}, "
                            f"Ref:{self.reference}, Size:{self.size}... ERROR")
                log.debug(result)
                return
            if "BE_BE" == self.endian.upper():
                decoder = BinaryPayloadDecoder.fromRegisters(
                    data, Endian.Big, wordorder=Endian.Big)
            elif "LE_BE" == self.endian.upper():
                decoder = BinaryPayloadDecoder.fromRegisters(
                    data, Endian.Little, wordorder=Endian.Big)
            elif "LE_LE" == self.endian.upper():
                decoder = BinaryPayloadDecoder.fromRegisters(
                    data, Endian.Little, wordorder=Endian.Little)
            else:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    data, Endian.Big, wordorder=Endian.Little)
            cur_ref = self.reference
            for ref in self.readableReferences:
                while cur_ref < ref.reference and cur_ref < self.reference + self.size:
                    decoder.skip_bytes(2)
                    cur_ref += 1
                if cur_ref >= self.reference + self.size:
                    break
                if "uint16" == ref.dtype:
                    ref.update_value(decoder.decode_16bit_uint())
                    cur_ref += 1
                elif "int16" == ref.dtype:
                    ref.update_value(decoder.decode_16bit_int())
                    cur_ref += 1
                elif "uint32" == ref.dtype:
                    ref.update_value(decoder.decode_32bit_uint())
                    cur_ref += 2
                elif "int32" == ref.dtype:
                    ref.update_value(decoder.decode_32bit_int())
                    cur_ref += 2
                elif "float32" == ref.dtype:
                    ref.update_value(decoder.decode_32bit_float())
                    cur_ref += 2
                # elif "bool" == ref.dtype:
                #     ref.update_value(decoder.decode_bits())
                #     cur_ref += ref.length
                # elif ref.dtype.startswith("string"):
                #     ref.update_value(decoder.decode_string())
                #     cur_ref += ref.length
                else:
                    decoder.decode_16bit_uint()
                    cur_ref += 1
            self.count_success(True)
            log.info(f"Reading device:{self.devid}, FuncCode:{self.functioncode}, "
                     f"Ref:{self.reference}, Size:{self.size}... SUCCESS")
            return True
        except ModbusException as ex:
            self.count_success(False)
            log.warning(f"Reading device:{self.devid}, FuncCode:{self.functioncode}, "
                        f"Ref:{self.reference}, Size:{self.size}... FAILED")
            log.debug(ex)
            return False

    def add_readable_reference(self, ref):
        if ref.name not in self.device.occupiedTopics:
            self.device.occupiedTopics.append(ref.name)
            ref.device = self.device
            log.debug(f"Added new reference {ref.name} to poller {self.name}")
            if ref.check_sanity(self.reference, self.size):
                self.readableReferences.append(ref)
                referenceList.append(ref)
            else:
                log.warning(
                    f"Reference name {ref.name} failed to pass sanity check, therefore ignoring it.")
        else:
            log.warning(
                f"Reference name ({ref.name}) is already occupied, therefore ignoring it.")

    def publish_data(self, timestamp=None, on_change=False):
        payload = {}
        for ref in self.readableReferences:
            if on_change and ref.val == ref.last_val:
                continue
            if ref.unit:
                payload[f'{ref.name}|{ref.unit}'] = ref.val
            else:
                payload[f'{ref.name}'] = ref.val
        if timestamp:
            payload['timestamp'] = timestamp
        topic = f"{args.mqtt_topic_prefix}{self.device.name}"
        mqttc_publish(topic, json.dumps(payload))


class Reference:
    def __init__(self, name, unit, reference, dtype, scale):
        self.name = name
        self.unit = unit
        self.reference = int(reference)
        self.dtype = dtype
        if "int16" in dtype:
            self.length = 1
        elif "uint16" in dtype:
            self.length = 1
        elif "int32" in dtype:
            self.length = 2
        elif "uint32" in dtype:
            self.length = 2
        elif "float32" == dtype:
            self.length = 2
        elif "bool" == dtype:
            self.length = 1
        elif dtype.startswith("string"):
            try:
                self.length = int(dtype[6:9])
            except ValueError:
                self.length = 2
            if self.length > 100:
                log.warning("Data type string: length too long")
                self.length = 100
            if math.fmod(self.length, 2) != 0:
                self.length = self.length - 1
                log.warning("Data type string: length must be divisible by 2")
        else:
            log.error(f"unknown data type: {dtype}")
        self.scale = scale
        self.val = None
        self.lastval = None
        self.device = None

    def check_sanity(self, reference, size):
        if self.reference in range(reference, size + reference) \
                and self.reference + self.length - 1 in range(reference, size + reference):
            return True
        return False

    def update_value(self, v):
        if self.scale:
            try:
                v = v * float(self.scale)
            except ValueError:
                pass
        self.lastval = self.val
        self.val = v


def parse_config(csv_reader):
    current_poller = None
    for row in csv_reader:
        if not row or len(row) == 0:
            continue
        if "poll" in row[0]:
            name = row[1]
            devid = int(row[2])
            reference = int(row[3])
            size = int(row[4])
            endian = row[6]
            if "coil" == row[5]:
                functioncode = 1
                if size > 2000:  # some implementations don't seem to support 2008 coils/inputs
                    current_poller = None
                    log.error(
                        "Too many coils (max. 2000). Ignoring poller " + row[1] + ".")
                    continue
            elif "input_status" == row[5]:
                functioncode = 2
                if size > 2000:
                    current_poller = None
                    log.error(
                        "Too many inputs (max. 2000). Ignoring poller " + row[1] + ".")
                    continue
            elif "holding_register" == row[5]:
                functioncode = 3
                if size > 123:  # applies to TCP, RTU should support 125 registers. But let's be safe.
                    current_poller = None
                    log.error(
                        "Too many registers (max. 123). Ignoring poller " + row[1] + ".")
                    continue
            elif "input_register" == row[5]:
                functioncode = 4
                if size > 123:
                    current_poller = None
                    log.error(
                        "Too many registers (max. 123). Ignoring poller " + row[1] + ".")
                    continue
            else:
                log.warning("Unknown function code (" +
                            row[5] + " ignoring poller " + row[1] + ".")
                current_poller = None
                continue
            current_poller = Poller(
                name, devid, reference, size, functioncode, endian)
            pollers.append(current_poller)
            log.info(f"Added new poller {current_poller.name}, {current_poller.devid}, "
                     f"{current_poller.reference}, {current_poller.size}")
        elif "ref" in row[0]:
            name = row[1].replace(" ", "_")
            unit = row[2]
            ref = row[3]
            dtype = row[4]
            scale = row[5]
            if current_poller:
                current_poller.add_readable_reference(
                    Reference(name, unit, ref, dtype, scale))
            else:
                log.debug(f"No poller for reference {name}.")


def load_config(file):
    try:
        with requests.Session() as s:
            response = s.get(file)
            decoded_content = response.content.decode('utf-8')
            csv_reader = csv.reader(decoded_content.splitlines(), delimiter=',')
            parse_config(csv_reader)
    except requests.RequestException as exception:
        with open(file, "r") as f:
            f.seek(0)
            csv_reader = csv.reader(f)
            parse_config(csv_reader)


def modbus_setup(config):
    global args
    args = config
    global log
    log = logging.getLogger(__name__)
    global master

    log.info(f"Loading config from: {args.config}")
    load_config(args.config)
    if args.rtu:
        if args.rtu_parity == "odd":
            parity = "O"
        elif args.rtu_parity == "even":
            parity = "E"
        else:
            parity = "N"
        master = ModbusSerialClient(method="rtu", port=args.rtu, stopbits=1, bytesize=8, parity=parity,
                                    baudrate=int(args.rtu_baud), reset_socket=True)
    elif args.tcp:
        master = ModbusTcpClient(args.tcp, args.tcp_port, timeout=args.timeout, reset_socket=True)
    else:
        log.error("You must specify a modbus access method, either --rtu or --tcp")
        return False
    return True


def modbus_poll():
    global master
    if not master:
        return
    master.connect()
    for p in pollers:
        if not p.disabled:
            ret = p.poll()
            t = time.time()
            if ret:
                p.publish_data()
            while time.time() < t + args.interval:
                time.sleep(0.001)
    master.close()
    # print out result
    modbus_print()
    for d in deviceList:
        d.publish_diagnostics()


def modbus_print():
    table = PrettyTable(['name', 'unit', 'reference', 'value'])
    for r in referenceList:
        row = [r.name, r.unit, r.reference, r.val]
        table.add_row(row)
    print(table)


def modbus_export(file):
    with open(file, 'w') as f:
        writer = csv.writer(f)
        header = ['name', 'unit', 'reference', 'value']
        writer.writerow(header)
        for r in referenceList:
            row = [r.name, r.unit, r.reference, r.val]
            writer.writerow(row)
    log.info(f"Saved references/registers to {file}")


def modbus_close():
    global master
    if master:
        master.close()
