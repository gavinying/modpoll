"""Adapt validated WoT configuration to the existing Modpoll execution engine."""

import modpoll_wot
from modpoll_wot.loading import load_model, loads_model, MAX_BYTES
import requests


def read_model(location, *, timeout, unit_id, host=None, port=None, parameters=None):
    # Released 0.1 consumers remain usable until the producer candidate is
    # published and installed. Connection metadata is interpreted by 0.2 only.
    if parameters and not hasattr(modpoll_wot, "instantiate"):
        raise ValueError("TM parameters require the profile 0.2 interpreter")
    instance = (
        {"host": host, "port": port, "parameters": parameters}
        if hasattr(modpoll_wot, "instantiate")
        else {}
    )
    if location.startswith(("http://", "https://")):
        with requests.get(location, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError(f"{location}: configuration exceeds 1 MiB")
                chunks.append(chunk)
        return loads_model(
            b"".join(chunks), source=location, unit_id=unit_id, **instance
        )
    return load_model(location, unit_id=unit_id, **instance)


def create_devices(model):
    # The shared interpreter has no dependency on the application or PyModbus.
    from .modbus_task import Device, Poller, Reference

    device = Device(model.title, model.unit_id)
    function_codes = {
        "coil": 1,
        "discrete_input": 2,
        "holding_register": 3,
        "input_register": 4,
    }
    for group in model.groups:
        poller = Poller(
            device,
            function_codes[group.table],
            group.start,
            group.quantity,
            group.byte_order,
        )
        for member in group.members:
            address = str(group.start + member.offset)
            if member.bit is not None:
                address += ":" + str(member.bit)
            access = ("r" if member.readable else "") + ("w" if member.writable else "")
            reference = Reference(
                device,
                member.property,
                address,
                member.data_type,
                access,
                member.unit,
                None if member.multiplier is None else float(member.multiplier),
            )
            reference.endian = getattr(member, "byte_order", None)
            reference.physical_bits = getattr(member, "physical_bits", False)
            reference.bit_count = getattr(member, "bit_count", None)
            reference.scalar = getattr(member, "scalar", False)
            if member.readable:
                poller.add_readable_reference(reference)
            device.add_reference_mapping(reference)
        device.pollerList.append(poller)
    return [device]
