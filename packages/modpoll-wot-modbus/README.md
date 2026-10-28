# modpoll-wot-modbus (experimental)

This initial package parses a deliberately small experimental acquisition-group
subset. It validates TM/TD against bundled W3C 1.1 schemas but does not fetch contexts, decode registers, read
or write devices, or integrate with modpoll. It is not ready for release.

The supported subset describes holding and input register groups with numeric
members and four byte/word orders. Coils, discrete inputs, bit selectors,
strings, scaling and write behavior are not implemented. Unknown member and
group fields are rejected. The vocabulary and format may change.

Run the local unit checks from the repository root:

```
PYTHONPATH=packages/modpoll-wot-modbus python -m unittest discover -s packages/modpoll-wot-modbus/tests
```

The bundled W3C schemas identify themselves as version 1.1-12-March-2025 and were retrieved from the W3C TD and TM schema URLs. Standard schema validation and acquisition semantic checks are separate; neither establishes device correctness.
