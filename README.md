# ModPoll - A new modpoll tool for modbus communication

[![pipeline status](https://gitlab.com/helloysd/modpoll/badges/master/pipeline.svg)](https://gitlab.com/helloysd/modpoll/-/commits/master)
[![License](https://img.shields.io/pypi/l/modpoll)](https://gitlab.com/helloysd/modpoll/-/blob/master/LICENSE)
[![Downloads](http://pepy.tech/badge/modpoll)](http://pepy.tech/project/modpoll)

> Learn more about `modpoll` usage at [documentation](https://helloysd.gitlab.io/modpoll) site. 

## Motivation

The initial idea of creating this tool is to help myself debugging new devices during site survey. A site survey usually has limited time and space, working on-site also piles up some pressures. At that time, a portable swiss-knife toolkit is our best friend.

This program can be easily deployed to Raspberry Pi or similar embedded devices, continuously polling data from the connected modbus devices, you can choose to save data locally or forward uplink to a MQTT broker for easy debugging, the MQTT broker can be setup on the same Raspberry Pi or on the cloud. On the other hand, a smart phone (Android/Iphone) can be used to visualize collected data and control the devices remotely via the same MQTT broker. 

Moreover, you can also run this program on any PC or server with Python 3 support. One common use case is to deploy the program onto a server and keep it running as a gateway, i.e. polling data from local Modbus devices and forward to a centralized cloud server. In that sense, this program helps to bridge between the traditional world of fieldbus network and the modern world of IoT edge/cloud infrustructure. 

> This program is designed to be a standalone tool, it shall work out-of-the-box. If you are looing for a modbus python library, please consider the following two great open source projects, [pymodbus](https://github.com/riptideio/pymodbus) or [minimalmodbus](https://github.com/pyhys/minimalmodbus)

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

## Basic Usage

- Connect to Modbus TCP device

  ```bash
  modpoll --tcp 192.168.1.10 --config examples/modsim.csv

  ```

- Connect to Modbus RTU device 

  ```bash
  modpoll --rtu /dev/ttyUSB0 --rtu-baud 9600 --config examples/scpms6.csv

  ```

- Connect to Modbus TCP device and publish data to MQTT broker 

  ```bash
  modpoll --tcp modsim.topmaker.net --tcp-port 5020 --config examples/modsim.csv --mqtt-host iot.topmaker.net

  ```

- Connect to Modbus TCP device and export data to local csv file

  ```bash
  modpoll --tcp modsim.topmaker.net --tcp-port 5020 --config examples/modsim.csv --export data.csv

  ```

Please refer to [documentation](https://helloysd.gitlab.io/modpoll) site for more configures and examples.

> Notes: some of the examples use our online modbus simulator at `modsim.topmaker.net` with standard `502` port, it helps user to quickly test the functions of `modpoll` tool. 


## Run in docker

A docker image has been provided for user to directly run the program, 

  ```bash
  docker run helloysd/modpoll --help
  ```

To load local configure file, you need to mount a local folder to the container volume, 
for example, if the child folder `examples` contains the config file `modsim.csv`, we can mount it using the following command, 

  ```bash
  docker run -v $(pwd)/examples:/app/examples helloysd/modpoll --tcp modsim.topmaker.net --config /app/examples/modsim.csv
  ```

The other way is to load configure file from a remote URL, for example, 

  ```bash
  docker run helloysd/modpoll --tcp modsim.topmaker.net --tcp-port 5020 --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
  ```


## Credits

The implementation of this project is heavily inspired by the following two projects:
- https://github.com/owagner/modbus2mqtt (MIT license)
- https://github.com/mbs38/spicierModbus2mqtt (MIT license)
Thanks to Max Brueggemann and Oliver Wagner for their great work. 

## License

MIT © [Ying Shaodong](helloysd@foxmail.com)
