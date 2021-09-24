Installation
============

This program is tested on python 3.6+.

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


Run in docker (without installation)
-------------------------------------

- Check app version

  .. code-block:: shell

    docker run helloysd/modpoll --version


- Connect to Modbus TCP device

  To load the modbus register configure file, user may need to mount the volume to container, for example, if the child folder `examples` contains the config file `modsim.csv`, we can mount it using the following command,

  .. code-block:: shell

    docker run -v $(pwd)/examples:/app/examples helloysd/modpoll --tcp modsim.topmaker.net --config /app/examples/modsim.csv
