Examples
========

Commandline
------------

- Connect to Modbus TCP device

  .. code-block:: shell
  
    modpoll --tcp modsim.topmaker.net --config examples/modsim.csv

- Connect to Modbus RTU device 

  .. code-block:: shell

    modpoll --rtu /dev/ttyUSB0 --rtu-baud 9600 --config examples/scpms6.csv


- Connect to Modbus TCP device and publish data to MQTT broker 

  .. code-block:: shell

    modpoll --tcp modsim.topmaker.net --config examples/modsim.csv --mqtt-host iot.topmaker.net


- Connect to Modbus TCP device and export data to local csv file

  .. code-block:: shell

    modpoll --tcp modsim.topmaker.net --config examples/modsim.csv --export data.csv


Run in docker
--------------

- Check app version (in docker)

  .. code-block:: shell

    docker run helloysd/modpoll modpoll --version


- Connect to our online Modbus TCP device simulator (in docker)

  To load the modbus register configure file, user may need to mount the volume to container, for example, if the child folder `examples` contains the config file `modsim.csv`, we can mount it using the following command,

  .. code-block:: shell

    docker run -v $(pwd)/examples:/app/examples helloysd/modpoll modpoll --tcp modsim.topmaker.net --config /app/examples/modsim.csv


Modbus Configuration File
--------------------------

In order to communicate with modbus devices, a proper modbus configure file is required. 
It is mainly to describe the device address and register mappings. 

Here is the basic structure of modbus configure file. 

.. literalinclude:: ../examples/example.csv
   :language: default
   :emphasize-lines: 8-10,23-25
   :linenos:


Example 1: Online Modbus Device Simulator (Modbus TCP)
--------------------------------------------------------

This online Modbus TCP device simulator is designed for user to quickly test our modpoll functions.

Here is an example of modbus configure file for modsim.

.. literalinclude:: ../examples/modsim.csv
   :language: default
   :linenos:


Example 2: SCPM-S6 Power Meter (Modbus RTU)
---------------------------------------------

SCPM-S6 is designed as a sub-circuit power meter to monitor multiple electrical circuit power consumptions. 

Here is an example of modbus configure file for SCPM-S6.

.. literalinclude:: ../examples/scpms6.csv
   :language: default
   :linenos:
