Installation
============

This documentation describes the 2.x functional preview. Install the exact version::

    pip install "modpoll[serial]==2.0.0a1"

For existing CSV installations use ``pip install "modpoll<2"`` and the
`1.x documentation <https://top-maker.github.io/modpoll/1.x/>`_.
The preview image is ``topmaker/modpoll:2.0.0a1``; stable ``latest`` stays on 1.x.
See :doc:`v1-compatibility` for tested platforms and hardware limitations.

This program is tested on python 3.10+ (Ubuntu 22.04+ or equivalent). Ubuntu 20.04 and python 3.8 are no longer supported.

Install with pip or pipx
-------------------------

The package is available in the `Python Package Index <https://pypi.org/>`_,

.. code-block:: shell

    pip install "modpoll==2.0.0a1"

Optionally, pyserial library can be installed for Modbus-RTU communication,

.. code-block:: shell

    pip install 'modpoll[serial]==2.0.0a1'

Run the following command to check if there is new version available,

.. code-block:: shell

    pip install -U --pre "modpoll<3"

On Windows, it's recommended to use ``pipx`` for installing *modpoll*. Refer to `pipx <https://pypa.github.io/pipx/installation/>`_ installation guide for detailed instructions.

To install *modpoll*, open a Command Prompt terminal and run:

.. code-block:: shell

    pipx install "modpoll==2.0.0a1"

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

    docker run --rm topmaker/modpoll:2.0.0a1

It shows the version of the tool by default.
