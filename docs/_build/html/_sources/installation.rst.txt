Installation
============

This program is tested on python 3.8+.

Install with pip or pipx
-------------------------

The package is available in the `Python Package Index <https://pypi.org/>`_,

.. code-block:: shell

    pip install modpoll

Optionally, pyserial library can be installed for Modbus-RTU communication,

.. code-block:: shell

    pip install 'modpoll[serial]'

Run the following command to check if there is new version available,

.. code-block:: shell

    pip install -U modpoll

On Windows, it's recommended to use ``pipx`` for installing *modpoll*. Refer to `pipx <https://pypa.github.io/pipx/installation/>`_ installation guide for detailed instructions.

To install *modpoll*, open a Command Prompt terminal and run:

.. code-block:: shell

    pipx install modpoll

To upgrade *modpoll* to the latest version, use the following command:

.. code-block:: shell

    pipx upgrade modpoll


Uninstall
-------------------

The program can be uninstalled by the following command,

.. code-block:: shell

    pip uninstall modpoll

or,

.. code-block:: shell

    pipx uninstall modpoll


Run with docker
---------------

A docker image has been provided for user to directly use the tool
without the local installation,

.. code-block:: shell

    docker run --rm helloysd/modpoll

It shows the version of the tool by default.
