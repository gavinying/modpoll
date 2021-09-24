Examples
========

Modbus Device Simulator
------------------------
In order to quickly explore the functions of *modpoll*, we deployed a dummy Modbus TCP device at `<modsim.topmaker.net:5020>`_, you can simply connect it through the following command, 

  .. code-block:: shell

    modpoll --tcp modsim.topmaker.net --tcp-port 5020 --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv

or run modpoll in docker,

  .. code-block:: shell

    docker run helloysd/modpoll --tcp modsim.topmaker.net --tcp-port 5020 --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv


However, if the online service is down or you simply prefer a local test, then you can always launch your own device through the following command, 

  .. code-block:: shell

    docker run -p 5020:5020 helloysd/modsim

It will simulate a Modbus TCP device at `<localhost:5020>`_, and you shall be able to connect it through the following command, 

  .. code-block:: shell

    modpoll --tcp localhost --tcp-port 5020 --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv


Commandline Usage
------------------

- Connect to Modbus TCP device

  .. code-block:: shell
  
    modpoll --tcp modsim.topmaker.net --tcp-port 5020 --config examples/modsim.csv

- Connect to Modbus RTU device 

  .. code-block:: shell

    modpoll --rtu /dev/ttyUSB0 --rtu-baud 9600 --config examples/scpms6.csv

- Connect to Modbus TCP device and publish data to MQTT broker 

  .. code-block:: shell

    modpoll --tcp modsim.topmaker.net --config examples/modsim.csv --mqtt-host iot.topmaker.net

- Connect to Modbus TCP device and export data to local csv file

  .. code-block:: shell

    modpoll --tcp modsim.topmaker.net --config examples/modsim.csv --export data.csv
