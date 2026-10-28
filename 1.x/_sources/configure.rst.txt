Configuration
====================

Modbus Configure File
----------------------

In order to communicate with modbus devices, a proper modbus configure file is required.
It is mainly to describe the device address and register mappings.

Here is the basic structure of modbus configure file.

The parser checks device IDs (1–254), unique device and reference names, positive poll sizes within the function-code limits, address ranges, endian settings, data types, read/write modes, and numeric scales. Configuration errors include the CSV line number; invalid rows are skipped while later rows continue to be checked.


.. literalinclude:: ../examples/config_template.csv
   :language: default
   :emphasize-lines: 8-10
   :linenos:


Example 1: Modsim device (Modbus TCP device)
--------------------------------------------------------

This online Modbus TCP device simulator is designed for user to quickly test the modpoll functions.

Here is an example of modbus configure file for reading modsim device.

.. literalinclude:: ../examples/modsim.csv
   :language: default
   :linenos:


Example 2: SCPM-S6 Power Meter (Modbus RTU device)
---------------------------------------------------

SCPM-S6 is designed as a sub-circuit power meter to monitor multiple electrical circuit power consumptions.

Here is an example of modbus configure file for SCPM-S6.

.. literalinclude:: ../contrib/eniwise/scpms6.csv
   :language: default
   :linenos:
