"""Offline W3C TM/TD JSON Schema validation."""

import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft7Validator


class ModelValidationError(ValueError):
    """The supplied JSON document does not match the selected schema."""


@lru_cache(maxsize=3)
def _validator(kind):
    if kind not in ("tm", "td", "acquisition"):
        raise ValueError("kind must be 'tm' or 'td'")
    schema = json.loads(files("modpoll_wot_modbus").joinpath("schemas", ("acquisition-0.1.json" if kind == "acquisition" else f"{kind}-1.1.json")).read_text(encoding="utf-8"))
    return Draft7Validator(schema)


def validate_standard(document, *, kind):
    """Validate standard structure; project semantics require separate checks."""
    error = next(_validator(kind).iter_errors(document), None)
    if error is not None:
        path = "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in error.absolute_path)
        raise ModelValidationError(f"{path}: {error.message}")
