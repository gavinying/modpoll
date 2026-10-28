"""Version 0.1 acquisition contract; no transport or codec dependency."""
from dataclasses import dataclass
from decimal import Decimal
import math


class AcquisitionError(ValueError):
    """Invalid or unsupported acquisition semantics."""


@dataclass(frozen=True)
class Member:
    property: str
    offset: int
    data_type: str
    bit: int | None = None
    multiplier: Decimal | None = None
    readable: bool = True
    writable: bool = False
    unit: str | None = None


@dataclass(frozen=True)
class Group:
    table: str
    start: int
    quantity: int
    byte_order: str
    members: tuple[Member, ...]


WIDTHS = {"int16": 1, "uint16": 1, "float16": 1, "int32": 2,
          "uint32": 2, "float32": 2, "int64": 4, "uint64": 4,
          "float64": 4, "bool": 1, "bool8": 1, "bool16": 2}


def _integer(value, path):
    if type(value) is not int:
        raise AcquisitionError(f"{path}: expected integer")
    return value


def _fields(value, required, path, optional=frozenset()):
    if not isinstance(value, dict):
        raise AcquisitionError(f"{path}: expected object")
    if required - value.keys() or value.keys() - required - optional:
        raise AcquisitionError(f"{path}: missing or unsupported fields")


def parse_acquisition(document) -> tuple[Group, ...]:
    if not isinstance(document, dict):
        raise AcquisitionError("document: expected object")
    properties = document.get("properties")
    groups = document.get("modpoll:acquisition")
    if not isinstance(properties, dict) or not properties:
        raise AcquisitionError("properties: expected nonempty object")
    if not isinstance(groups, list) or not groups:
        raise AcquisitionError("modpoll:acquisition: expected nonempty array")
    parsed, seen = [], set()
    for i, group in enumerate(groups):
        path = f"modpoll:acquisition[{i}]"
        _fields(group, {"modpoll:table", "modpoll:start", "modpoll:quantity", "modpoll:byteOrder", "modpoll:members"}, path)
        table = group["modpoll:table"]
        if table not in ("coil", "discrete_input", "holding_register", "input_register"):
            raise AcquisitionError(f"{path}: unsupported table")
        bits = table in ("coil", "discrete_input")
        start = _integer(group["modpoll:start"], path + ".start")
        quantity = _integer(group["modpoll:quantity"], path + ".quantity")
        if not 0 <= start <= 65535 or not 1 <= quantity <= (2000 if bits else 125) or start + quantity > 65536:
            raise AcquisitionError(f"{path}: invalid range")
        order = group["modpoll:byteOrder"]
        if order not in ("BE_BE", "BE_LE", "LE_BE", "LE_LE"):
            raise AcquisitionError(f"{path}: invalid byte order")
        members = group["modpoll:members"]
        if not isinstance(members, list) or not members:
            raise AcquisitionError(f"{path}.members: expected nonempty array")
        result = []
        for j, member in enumerate(members):
            mp = f"{path}.members[{j}]"
            _fields(member, {"modpoll:property", "modpoll:offset", "modpoll:dataType"}, mp, {"modpoll:bit", "modpoll:multiplier"})
            name = member["modpoll:property"]
            if not isinstance(name, str) or name not in properties or name in seen:
                raise AcquisitionError(f"{mp}: unknown or duplicate property")
            prop = properties[name]
            if not isinstance(prop, dict):
                raise AcquisitionError(f"{mp}: invalid property schema")
            dtype = member["modpoll:dataType"]
            if not isinstance(dtype, str):
                raise AcquisitionError(f"{mp}: invalid data type")
            width = WIDTHS.get(dtype)
            if dtype.startswith("string") and dtype[6:].isdigit() and int(dtype[6:]) > 0:
                width = math.ceil(int(dtype[6:]) / 2)
            if width is None:
                raise AcquisitionError(f"{mp}: unsupported data type")
            offset = _integer(member["modpoll:offset"], mp + ".offset")
            # Legacy bit-table offsets count eight-bit groups, relative to poll start.
            if offset < 0 or offset + width > (math.ceil(quantity / 8) if bits else quantity):
                raise AcquisitionError(f"{mp}: member outside group")
            bit = member.get("modpoll:bit")
            if "modpoll:bit" in member and (bits or dtype != "bool" or type(bit) is not int or not 0 <= bit <= 15):
                raise AcquisitionError(f"{mp}: invalid register bit selector")
            for flag in ("readOnly", "writeOnly"):
                if flag in prop and type(prop[flag]) is not bool:
                    raise AcquisitionError(f"{mp}: invalid {flag}")
            if prop.get("readOnly") and prop.get("writeOnly"):
                raise AcquisitionError(f"{mp}: conflicting access flags")
            readable, writable = not prop.get("writeOnly", False), not prop.get("readOnly", False)
            if table in ("discrete_input", "input_register") and writable:
                raise AcquisitionError(f"{mp}: read-only table must declare readOnly")
            multiplier = None
            if "modpoll:multiplier" in member:
                value = member["modpoll:multiplier"]
                if type(value) not in (int, float, str):
                    raise AcquisitionError(f"{mp}: invalid multiplier")
                try:
                    multiplier = Decimal(str(value))
                except Exception as exc:
                    raise AcquisitionError(f"{mp}: invalid multiplier") from exc
                if not multiplier.is_finite():
                    raise AcquisitionError(f"{mp}: non-finite multiplier")
            result.append(Member(name, offset, dtype, bit, multiplier, readable, writable, prop.get("unit")))
            seen.add(name)
        parsed.append(Group(table, start, quantity, order, tuple(result)))
    if seen != properties.keys():
        raise AcquisitionError("properties: each property must have an acquisition member")
    return tuple(parsed)
