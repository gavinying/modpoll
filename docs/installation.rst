Installation
============

This program is tested on python 3.8+.

Install with pip
-----------------

The package is available in the Python Package Index::

    pip install modpoll

Run the following command to check if there is new version available::

    pip install -U modpoll


Uninstall with pip
-------------------

The program can be uninstalled by the following command::

    pip uninstall modpoll


Run in docker
-------------------------------------

- Check app version

  .. code-block:: shell

    docker run helloysd/modpoll


- Connect to Modbus TCP device

  In order to quickly explore the functions of *modpoll*, we deployed a dummy Modbus TCP device at `<modsim.topmaker.net:502>`_, you can connect via the following command,

  .. code-block:: shell

    docker run helloysd/modpoll modpoll --tcp modsim.topmaker.net --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
