"""Load a bounded JSON document and validate its executable contract."""
import json
from dataclasses import dataclass
from pathlib import Path

from .acquisition import AcquisitionError, Group, parse_acquisition
from .validation import validate_standard

CONTEXT = "https://top-maker.github.io/modpoll/vocab/wot-modbus#"


@dataclass(frozen=True)
class Model:
    title: str
    kind: str
    groups: tuple[Group, ...]
    unit_id: int


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise AcquisitionError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_model(path, *, kind, unit_id=1):
    if type(unit_id) is not int or not 1 <= unit_id <= 254:
        raise AcquisitionError("unit_id: expected integer between 1 and 254")
    path = Path(path)
    try:
        with path.open('rb') as source:
            payload = source.read(1048577)
        if len(payload) > 1048576:
            raise AcquisitionError("configuration exceeds 1 MiB")
        document = json.loads(payload, object_pairs_hook=_pairs,
                              parse_constant=lambda value: (_ for _ in ()).throw(AcquisitionError(f"invalid number: {value}")))
        validate_standard(document, kind=kind)
        validate_standard(document, kind="acquisition")
        contexts = document.get('@context', [])
        if not isinstance(contexts, list) or not any(isinstance(c, dict) and c.get('modpoll') == CONTEXT for c in contexts):
            raise AcquisitionError("@context: missing supported modpoll vocabulary")
        if document.get('modpoll:version') != '0.1':
            raise AcquisitionError("modpoll:version: expected 0.1")
        if document.get('actions') or document.get('events') or document.get('links'):
            raise AcquisitionError("actions, events and links are not executable in version 0.1")
        return Model(document['title'], kind, parse_acquisition(document), unit_id)
    except (ValueError, OSError, RecursionError) as exc:
        raise AcquisitionError(f"{path}: {exc}") from exc
