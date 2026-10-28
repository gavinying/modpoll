# modpoll-wot-modbus (experimental)

An independently packaged TM/TD configuration interpreter under development.
See CONTRACT.md for the executable 0.1 subset and 1.x field mapping.

The loader validates bundled W3C TM/TD 1.1 schemas, the project extension
schema, and acquisition semantics. It does not execute Modbus requests.

```python
from modpoll_wot_modbus.loading import load_model
model = load_model("tests/fixtures/modsim.tm.json", kind="tm", unit_id=1)
```

Run checks from the repository root:

```sh
PYTHONPATH=packages/modpoll-wot-modbus python -m unittest discover -s packages/modpoll-wot-modbus/tests
```

The bundled W3C schemas identify themselves as 1.1-12-March-2025, retrieved from
https://www.w3.org/2022/wot/td-schema/v1.1 and
https://www.w3.org/2022/wot/tm-schema/v1.1. Standard validation does not
establish device correctness.
