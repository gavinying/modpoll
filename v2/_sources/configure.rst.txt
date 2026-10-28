WoT TM/TD configuration
=======================

The 2.x development branch accepts JSON configurations using WoT TM/TD 1.1.
It rejects CSV input. The bundled ``examples/modsim.tm.json`` and
``examples/modsim.td.json`` describe the same four blocks and 37 output properties.

Each file describes one device. Its ``title`` is the output device name;
``--unit-id`` overrides the instance Unit ID (range 1–254). Without it, each file
uses its optional root ``modv:unitID`` default, falling back to 1. Different files
can therefore address different Unit IDs in one process.
Multiple files may be supplied to ``--config``; titles must be unique.
The existing transport CLI arguments explicitly select the connection endpoint.
A concrete TD's form Unit IDs, addresses and quantities must agree with the model.

The interpreter validates the official, locally bundled TD/TM 1.1 schema,
the project extension schema and cross-field acquisition semantics. It does not
fetch context files or schemas. The local/URL input limit is 1 MiB and the JSON
nesting limit is 64. Duplicate JSON keys and non-finite numbers are rejected.

A model uses ``modpoll:version`` equal to ``0.1`` and an ordered
``modpoll:acquisition`` array. Groups reuse the Modbus draft's ``modv:entity``,
``modv:address``, ``modv:quantity``, ``modv:mostSignificantByte`` and
``modv:mostSignificantWord`` vocabulary. ``modpoll:members`` describes decoded
properties, offsets, precise types, optional register bit selectors and optional
multipliers. These acquisition semantics are a project extension, not a W3C
standard. The selected subset does not execute arbitrary TD protocol bindings.

Migration from CSV
------------------

* Copy the device name to ``title`` and pass its Unit ID through ``--unit-id``.
* Preserve every poll's table, literal start address, quantity and byte/word order.
* Map references to property keys and group members. Register member offsets are
  relative register offsets. Bit-table offsets count eight-bit groups, matching
  the old CSV behavior; counts still specify physical bits.
* Express read-only and write-only references through ``readOnly`` and
  ``writeOnly``. Neither flag means read/write. DI and IR are read-only tables;
  their historical ``rw`` sample flags must become ``readOnly: true``.
* Copy units unchanged and express the old scale as ``modpoll:multiplier``.
  Multipliers retain the existing floating-point execution behavior; they are
  not interpreted as divisors. Zero and negative multipliers are valid.
* Preserve effective reference names: the old loader replaced spaces with
  underscores. Unknown types or ambiguous fields require review.

The executable contract and test vectors live under
``packages/modpoll-wot``. Strings, bit selectors, four tables and all four
byte/word orders are represented by the contract. Model inheritance, optional members, URI templates, non-Modbus forms,
and security schemes other than ``nosec`` are rejected in this preview subset.
The interpreter records access flags; raw MQTT write commands retain the existing
1.x behavior and are not property-based writes.

Standard schema validity alone does not establish device correctness or prove
that a general WoT consumer will implement the project's acquisition/transform
extensions. This change adds no HTTP/cache service. See :doc:`v1-compatibility` for intentional
fixes and :doc:`csv-migration` for the reusable AI conversion prompt.
