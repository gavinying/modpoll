# modpoll-wot-modbus (experimental)

This initial package parses a deliberately small experimental acquisition-group
subset. It does not validate WoT TM/TD, fetch contexts, decode registers, read
or write devices, or integrate with modpoll. It is not ready for release.

The supported subset describes holding and input register groups with numeric
members and four byte/word orders. Coils, discrete inputs, bit selectors,
strings, scaling and write behavior are not implemented. Unknown member and
group fields are rejected. The vocabulary and format may change.

Run the local unit checks from the repository root:

```
PYTHONPATH=packages/modpoll-wot-modbus python -m unittest discover -s packages/modpoll-wot-modbus/tests
```
