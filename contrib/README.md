# Contributed device references

This directory retains vendor register documentation and contributed mappings.
CSV files are v1 migration sources; modpoll 2.x accepts TM/TD JSON only. Use the
[migration guide and AI prompt](../docs/csv-migration.rst), then validate the new
file with `python -m modpoll_wot MODEL` and compare known device readings.

The maintainer confirmed successful polling of an Eastron meter over physical
RS485 on 2026-10-28. This is manual hardware evidence in addition to automated
simulator and virtual-serial tests. The Eastron directory contains the contributed
SDM72D-M TD and vendor reference documents; validate a mapping for your device
model and selected Unit ID before use.

Contributed configurations are examples, not a required configuration library or
release gate. See the [validation record](../docs/validation.rst) for scope.
