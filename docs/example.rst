Examples
========

Modbus Configuration File
--------------------------

In order to communicate with modbus devices, a proper modbus configure file is required. 
It is mainly to describe the device address and register mappings. 

Here is the basic structure of modbus configure file. 

.. literalinclude:: ../examples/example.csv
   :language: default
   :emphasize-lines: 8-10,23-25
   :linenos:


Example 1: SCPM-S6 Power Meter
-------------------------------

SCPM-S6 is designed as a sub-circuit power meter to monitor multiple electrical circuit power consumptions. 

Here is an example of modbus configure file for SCPM-S6.

.. literalinclude:: ../examples/scpms6.csv
   :language: default
   :linenos:
