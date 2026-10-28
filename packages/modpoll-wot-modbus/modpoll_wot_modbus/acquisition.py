"""Parse the experimental register acquisition subset.

This module does not validate a WoT TM/TD or execute Modbus operations.
Addresses and offsets are zero-based literal register addresses.
"""

from dataclasses import dataclass
from typing import Mapping


class AcquisitionError(ValueError):
    """An acquisition group cannot be interpreted safely."""


@dataclass(frozen=True)
class Member:
    property: str
    offset: int
    data_type: str


@dataclass(frozen=True)
class Group:
    table: str
    start: int
    quantity: int
    byte_order: str
    members: tuple[Member, ...]


_WIDTH = {"int16": 1, "uint16": 1, "float16": 1,
          "int32": 2, "uint32": 2, "float32": 2,
          "int64": 4, "uint64": 4, "float64": 4}


def _integer(value, path):
    if type(value) is not int:
        raise AcquisitionError(f"{path}: expected integer")
    return value


def _fields(value, fields, path):
    if not isinstance(value, dict):
        raise AcquisitionError(f"{path}: expected object")
    missing = fields - value.keys()
    extra = value.keys() - fields
    if missing or extra:
        raise AcquisitionError(f"{path}: missing {sorted(missing)}, unknown {sorted(extra)}")


def parse_acquisition(document: Mapping) -> tuple[Group, ...]:
    """Parse only the experimental register subset; reject unsupported data."""
    if not isinstance(document, dict):
        raise AcquisitionError("document: expected object")
    properties = document.get("properties")
    groups = document.get("modpoll:acquisition")
    if not isinstance(properties, dict) or not properties:
        raise AcquisitionError("properties: expected nonempty object")
    if not isinstance(groups, list) or not groups:
        raise AcquisitionError("modpoll:acquisition: expected nonempty array")
    parsed = []
    seen = set()
    for i, group in enumerate(groups):
        path = f"modpoll:acquisition[{i}]"
        _fields(group, {"modpoll:table", "modpoll:start", "modpoll:quantity", "modpoll:byteOrder", "modpoll:members"}, path)
        table = group["modpoll:table"]
        if table not in ("holding_register", "input_register"):
            raise AcquisitionError(f"{path}: unsupported register table")
        start = _integer(group["modpoll:start"], path + ".start")
        quantity = _integer(group["modpoll:quantity"], path + ".quantity")
        if not 0 <= start <= 65535 or not 1 <= quantity <= 125 or start + quantity > 65536:
            raise AcquisitionError(f"{path}: invalid register range")
        order = group["modpoll:byteOrder"]
        if order not in ("BE_BE", "BE_LE", "LE_BE", "LE_LE"):
            raise AcquisitionError(f"{path}: invalid byte order")
        members = group["modpoll:members"]
        if not isinstance(members, list) or not members:
            raise AcquisitionError(f"{path}.members: expected nonempty array")
        parsed_members = []
        for j, member in enumerate(members):
            mp = f"{path}.members[{j}]"
            _fields(member, {"modpoll:property", "modpoll:offset", "modpoll:dataType"}, mp)
            name = member["modpoll:property"]
            if not isinstance(name, str) or name not in properties:
                raise AcquisitionError(f"{mp}: unknown property")
            if name in seen:
                raise AcquisitionError(f"{mp}: duplicate property {name!r}")
            dtype = member["modpoll:dataType"]
            if not isinstance(dtype, str) or dtype not in _WIDTH:
                raise AcquisitionError(f"{mp}: unsupported data type")
            offset = _integer(member["modpoll:offset"], mp + ".offset")
            if offset < 0 or offset + _WIDTH[dtype] > quantity:
                raise AcquisitionError(f"{mp}: member outside group")
            seen.add(name)
            parsed_members.append(Member(name, offset, dtype))
        parsed.append(Group(table, start, quantity, order, tuple(parsed_members)))
    return tuple(parsed)
