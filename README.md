[![pipeline status](https://gitlab.com/helloysd/modpoll/badges/master/pipeline.svg)](https://gitlab.com/helloysd/modpoll/-/commits/master)
[![License](https://img.shields.io/pypi/l/modpoll)](https://gitlab.com/helloysd/modpoll/-/blob/master/LICENSE)

---

# Modpoll

A command line tool to communicate with modbus devices.

> Learn more about `modpoll` usage at [documentation](https://helloysd.gitlab.io/modpoll) site. 


## Motivation

The initial idea of creating this tool is to help myself debugging and troubleshooting new modbus devices during site survey. A typical site survey usually has limited time and space, working on-site also pile up some pressures. During that time, a portable swiss-knife toolkit is our best friend.

This program can be easily deployed to Raspberry Pi or similar embedded devices, continuously polling data from the connected modbus devices, you can choose to save data locally or forward uplink to a MQTT broker for easy debugging, the MQTT broker can be setup on the same Raspberry Pi or on the cloud. On the other hand, a smart phone (Android/Iphone) can be used to visualize collected data and control the devices remotely via the same MQTT broker. 

However, beside the above recommended setup, you can actually run this program on any PC or server with Python 3 support. One popular use case is to deploy the program onto a server and keep it running as a gateway to bridge between traditional industrial network and modern IoT edge/cloud infrustructure. 

> This program is designed as a standalone tool, if you are looing for a python library to communicate with modbus devices, please consider the following two great open source projects, [pymodbus](https://github.com/riptideio/pymodbus) or [minimalmodbus](https://github.com/pyhys/minimalmodbus)

## Installation

This program is tested on python 3.6+.

- Install with pip

  The package is available in the Python Package Index, 

  ```bash
  pip install modpoll
  ```

  Upgrade the tool via pip by the following command,

  ```bash
  pip install -U modpoll
  ```

- Install with docker

  (To be added...)


## Examples

Please refer to [documentation](https://helloysd.gitlab.io/modpoll) site for more configures and examples.

## Credits

The implementation of this project is heavily inspired by the following two projects:
- https://github.com/owagner/modbus2mqtt (MIT license)
- https://github.com/mbs38/spicierModbus2mqtt (MIT license)
Thanks to Max Brueggemann and Oliver Wagner for their great work. 

## License

MIT © [Ying Shaodong](helloysd@foxmail.com)
