Examples
========

Commandline Examples
---------------------

- Connect to Modbus TCP device

  .. code-block:: shell
  
    modpoll --tcp 192.168.0.10 --config examples/scpms6.csv

- Connect to Modbus RTU device 

  .. code-block:: shell

    modpoll --rtu /dev/ttyUSB0 --rtu-baud 9600 --config examples/scpms6.csv


- Connect to Modbus TCP device and publish data to MQTT broker 

  .. code-block:: shell

    modpoll --tcp 192.168.0.10 --config examples/scpms6.csv --mqtt-host iot.eclipse.org


- Connect to Modbus TCP device and export data to local csv file

  .. code-block:: shell

    modpoll --tcp 192.168.0.10 --config examples/scpms6.csv --export data.csv


Modbus Configuration File
--------------------------

In order to communicate with modbus devices, a proper modbus configure file is required. 
It is mainly to describe the device address and register mappings. 

Here is the basic structure of modbus configure file. 

.. literalinclude:: ../examples/example.csv
   :language: default
   :emphasize-lines: 8-10,23-25
   :linenos:


Configuration Example 1: SCPM-S6 Power Meter
---------------------------------------------

SCPM-S6 is designed as a sub-circuit power meter to monitor multiple electrical circuit power consumptions. 

Here is an example of modbus configure file for SCPM-S6.

.. literalinclude:: ../examples/scpms6.csv
   :language: default
   :linenos:
