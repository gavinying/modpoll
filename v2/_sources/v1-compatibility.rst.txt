v1 compatibility and M3 acceptance
===================================

The v2 change replaces CSV loading with the executable TM/TD profile. The existing
transport, decoder, output and raw write paths remain. This table compares the
pinned v1 baseline ``0b42099`` with the v2 implementation; it is not a claim that
all WoT documents or every operating system has been validated.

.. list-table:: Capability and evidence
   :header-rows: 1
   :widths: 24 38 38

   * - Capability
     - v2 disposition
     - Evidence / limit
   * - Existing CLI
     - Existing transport, rate, interval, output and MQTT arguments retained;
       ``--unit-id`` adds an explicit override.
     - ``test_framer_validation.py`` and existing CLI tests. No ``--model`` or
       automatic connection from TD Forms is introduced.
   * - Multiple devices/configurations
     - One Thing per file; split an old multi-device CSV into several JSON files.
       Per-file Unit IDs and unique titles are retained.
     - ``test_modbus_task.py`` and ``test_wot_reading_interop.py``. An invalid file
       is closed while other valid files continue, matching the existing policy.
   * - Poll blocks, gaps and addressing
     - Ordered groups, literal PDU addresses, quantities and gaps preserved.
     - ``verify_modsim_equivalence.py`` compares exact requests and 37 values.
   * - Numeric/register bit/string types
     - Register integer/float widths, bit selectors, odd strings, units and
       multipliers retained; unscaled large integers remain Python integers.
     - Independent struct vectors in all four byte/word orders. Multiplied values
       still use the existing floating-point execution semantics.
   * - Numeric/string references in bit tables
     - Restored for complete payload bytes. Offsets remain eight-bit groups;
       numeric width counts bytes, stringN counts N bytes.
     - ``test_m3_compatibility.py`` and actual v1/TM numeric-bit parity tests.
       Incomplete numeric/string spans now fail validation, rather than decoding
       protocol padding or failing later. As in v1, bit-table numeric assembly
       reverses bit order within a byte; word order is not applied to bit tables.
   * - Aliases and overlapping views
     - Distinct property names can decode the same address; every alias is kept.
       Duplicate property membership is still rejected.
     - v1 could silently omit same-address aliases. This is an intentional fix;
       ``test_aliases_decode_every_property_from_one_read`` checks both views
       from one physical request.
   * - Read/write metadata
     - Readable properties are decoded; writeOnly properties are omitted from
       telemetry and remain null in snapshots. Declared blocks still get read.
     - DI/IR are read-only. Raw MQTT address writes do not inherit property-level
       authorization or engineering-value inverse transforms.
   * - UDP
     - Existing socket transport retained; explicit socket framer fixed.
     - Real simulator comparison of v1 CSV, TM and TD output.
   * - Serial RTU / ASCII
     - Serial and ``--rtu`` alias retained, explicit framer uses the actual
       PyModbus enum API instead of rejected class arguments.
     - POSIX PTY tests verify the full outputs and independently computed CRC/LRC
       request bytes. Default RTU matches v1. The pinned v1 explicit ASCII path
       fails construction, so ASCII is checked against independent wire/data
       expectations rather than claiming false v1 equivalence.
   * - MQTT protocol/output/commands
     - 3.1.1 and 5.0, grouped JSON, individual topics, diagnostics and existing
       FC5/6/16 commands retained.
     - Private-broker CSV/TM/TD matrix for QoS0/1; TLS/QoS2 CLI tests cover both
       protocols, both output styles, and command readback.
   * - MQTT TLS / authentication
     - Existing TLS version, CA, credentials and explicit insecure option retained.
     - Disposable CA/server certificates verify trusted success, unknown CA,
       hostname mismatch and bad-password refusal. Insecure bypass is explicit.
   * - Failures, counts and snapshots
     - Short responses invalidate missing values; connect/transport failures count
       once per active group. Disabled autoremove groups do not add attempts.
     - Real stop/restart and short-response cases. Invalid values are omitted from
       MQTT and null in atomic JSON snapshots; existing fsync/replace failure
       tests remain.
   * - One-shot exit status
     - A failed group or JSON export makes ``--once`` exit nonzero after cleanup.
     - Intentional correction: v1 could report exit 0 despite failed sampling or
       export. Signal-driven shutdown remains graceful.
   * - MQTT shutdown / outbound queue
     - Accepted publications get a bounded flush window (default five seconds),
       then disconnect precedes joining the network loop. Outstanding messages
       are reported; the outgoing queue is bounded to 1000 entries.
     - A real peer withholding PUBACK verifies shutdown cannot wait indefinitely.
       QoS handshakes do not make raw Modbus writes idempotent.

Current boundaries
------------------

CSV runtime support is intentionally removed; use :doc:`csv-migration`. Strings
and bit arrays carrying meaningless numeric scales, invalid rw modes, unknown
types and incomplete payload spans require review rather than silent conversion.
Profile inheritance/templates/actions and new property-based writes are separate
features, not requirements for preserving the old tool.

Automated serial evidence uses POSIX virtual terminals, not RS485 electrical
hardware. Windows/macOS serial devices, parity wiring and real device timing must
be reported separately when tested. The CI support matrix remains Python
3.10–3.12 on Linux. A passing development environment does not imply an application
wheel with a local dependency path is ready for public distribution; release
engineering is tracked separately.
