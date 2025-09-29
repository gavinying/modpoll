# Modpoll - A New Command-line Tool for Modbus and MQTT

[![Release](https://img.shields.io/github/v/release/gavinying/modpoll)](https://img.shields.io/github/v/release/gavinying/modpoll)
[![Build status](https://img.shields.io/github/actions/workflow/status/gavinying/modpoll/main.yml?branch=main)](https://github.com/gavinying/modpoll/actions/workflows/main.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/gavinying/modpoll)](https://img.shields.io/github/license/gavinying/modpoll)
[![Downloads](https://static.pepy.tech/badge/modpoll/week)](https://pepy.tech/project/modpoll)

> 📢 **Announcement:** Since the release of v1.3.0, our official dockerhub namespace has been changed to `topmaker`, you can pull the latest images from [topmaker/modpoll](https://hub.docker.com/repository/docker/topmaker/modpoll) at dockerhub.

> Learn more about *modpoll* usage at [documentation](https://gavinying.github.io/modpoll) site.

## Motivation

The idea for creating this tool originated from my need to efficiently check new devices during site surveys. These surveys are often time-constrained and space-limited, with on-site work adding to the pressure. In such situations, a portable Swiss Army knife toolkit becomes a valuable companion.

This tool can be easily deployed on a Raspberry Pi or similar embedded devices, polling data from a Modbus network or connected devices. Users can choose to log the data locally or publish it to an MQTT broker for further troubleshooting.

The MQTT broker can be set up either on the same Raspberry Pi or in the cloud. Once data is successfully published, users can subscribe to the relevant MQTT topics and conveniently view the data on their smartphones.

<p align="center">
  <img src="docs/assets/modpoll-usage.png">
</p>

Moreover, you can also run this tool continuously on a server as a Modbus-MQTT gateway, i.e. polling from local Modbus devices and forwarding data to a centralized cloud service.

In fact, *modpoll* helps to bridge between the traditional field-bus world and the new IoT world.

> 💡 **Tips:** This tool is designed to be a standalone executable application, which works out-of-the-box on Linux/macOS/Windows. If you are looking for a Modbus python library, please consider the following great open-source projects, [pymodbus](https://github.com/riptideio/pymodbus) or [minimalmodbus](https://github.com/pyhys/minimalmodbus)


## Feature

- Support Modbus RTU/TCP/UDP devices
- Show polling data for local debugging, like a typical modpoll tool
- Publish polling data to MQTT broker for remote debugging, especially on smart phone
- Export polling data to local storage for further investigation
- Provide docker solution for continuous data polling use case


## Installation

This tool tested on Python 3.8+, the package is available in the [Python Package Index](https://pypi.org/), users can easily install it using `pip` or `pipx`.

### Using PIP

Install *modpoll* using the following command,

```bash
pip install modpoll
```

Optionally, [pyserial](https://pyserial.readthedocs.io/) library can be installed for Modbus-RTU communication,

```bash
pip install 'modpoll[serial]'
```

Upgrade the tool via the following command,

```bash
pip install -U modpoll
```

### On Windows

It is recommended to use `pipx` for installing *modpoll* on Windows, refer to [here](https://pypa.github.io/pipx/installation/) for more information about `pipx`.

Once `pipx` installed, you can run the following command in a Command Prompt terminal.

```PowerShell
pipx install modpoll
```

Upgrade the tool via the following command,

```PowerShell
pipx upgrade modpoll
```

## Quickstart

*modpoll* is a python tool for communicating with Modbus devices, so ideally it makes more sense if you have a real Modbus device on hand for the following test, but it is OK if you don't, we provide a virtual Modbus TCP device deployed at `modsim.topmaker.net:502` for your quick testing purpose.

Let's start exploring *modpoll* with *modsim* device, run the following command to get a first glimpse,

```bash
modpoll --once \
  --tcp modsim.topmaker.net \
  --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
```

<p align="center">
  <img src="docs/assets/screenshot-modpoll.png">
</p>

> the modsim code is also available [here](https://github.com/gavinying/modsim)

### Prepare Modbus configure file

The reason we can magically poll data from the online device *modsim* is because we have already provided the [Modbus configure file](https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv) for *modsim* device as following,

```CSV
device,modsim01,1,,
poll,coil,0,16,BE_BE
ref,coil01-08,0,bool8,rw
ref,coil09-16,1,bool8,rw
poll,discrete_input,10000,16,BE_BE
ref,di01-08,10000,bool8,rw
ref,di09-16,10001,bool8,rw
poll,input_register,30000,20,BE_BE
ref,input_reg01,30000,uint16,rw
ref,input_reg02,30001,uint16,rw
ref,input_reg03,30002,uint16,rw
ref,input_reg04,30003,uint16,rw
ref,input_reg05,30004,int16,rw
ref,input_reg06,30005,int16,rw
ref,input_reg07,30006,int16,rw
ref,input_reg08,30007,int16,rw
ref,input_reg09,30008,uint32,rw
ref,input_reg10,30010,uint32,rw
ref,input_reg11,30012,int32,rw
ref,input_reg12,30014,int32,rw
ref,input_reg13,30016,float32,rw
ref,input_reg14,30018,float32,rw
poll,holding_register,40000,44,BE_BE
ref,holding_reg01,40000,uint16,rw
ref,holding_reg02,40001,uint16,rw
ref,holding_reg03,40002,uint16,rw
ref,holding_reg04,40003,uint16,rw
ref,holding_reg05,40004,int16,rw
ref,holding_reg06,40005,int16,rw
ref,holding_reg07,40006,int16,rw
ref,holding_reg08,40007,int16,rw
ref,holding_reg09,40008,uint32,rw
ref,holding_reg10,40010,uint32,rw
ref,holding_reg11,40012,int32,rw
ref,holding_reg12,40014,int32,rw
ref,holding_reg13,40016,float32,rw
ref,holding_reg14,40018,float32,rw
ref,holding_reg15,40020,uint64,rw
ref,holding_reg16,40024,int64,rw
ref,holding_reg17,40028,float64,rw
ref,holding_reg18,40032,float64,rw
ref,holding_reg19,40036,string16,rw
```

This configuration tells *modpoll* to do the following for each poll,

- Read `16` coils from the address starting from `0` and parse the response as two 8-bits boolean values;
- Read `16` discrete inputs from the address starting from `10000` and parse the response as two 8-bits boolean values;
- Read `20` input registers from the address starting from `30000` and parse data accordingly;
- Read `44` holding registers from the address starting from `40000` and parse data accordingly;

> Notice the holding registers contain a 16-byte long string, which counts as 8 registers in poll size, because Modbus protocol defines a holding register as 2-byte width.

In practical, you usually need to customize a Modbus configuration file for your own device before running *modpoll* tool, which defines the optimal polling patterns and register mappings according to device vendor's documents.

You can also take a look at [contrib](https://github.com/gavinying/modpoll/tree/master/contrib) folder, which collects a few types of device configuration shared by contributors.

The configuration can be either a local file or a remote public URL resource.

> *Refer to the [documentation](https://gavinying.github.io/modpoll/configure.html) site for more details.*

### Poll local device (modsim)

If you are blocked by company firewall for online device or prefer a local test, you can launch your own device simulator by running *modsim* locally,

```bash
docker run --rm -p 5020:5020 topmaker/modsim
```

It will create a virtual Modbus TCP device running at `localhost:5020`, and you can open a new terminal, poll the virtual device using *modpoll* tool,

```bash
modpoll \
  --tcp localhost \
  --tcp-port 5020 \
  --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
```

> Use `sudo` before the docker command if you want to use the standard port `502`.

```bash
sudo docker run --rm -p 502:5020 topmaker/modsim
```

In a new terminal,

```
modpoll \
  --tcp localhost \
  --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
```

### Publish data to MQTT broker

This is a useful function of this new *modpoll* tool, which provides a simple way to publish collected Modbus data to MQTT broker, so users can view data from a smart phone via a MQTT client.

The following example uses a public MQTT broker `broker.emqx.io` for test purpose. You can also set up your own MQTT broker locally using [mosquitto](https://mosquitto.org/download/).

```bash
modpoll \
  --tcp modsim.topmaker.net \
  --mqtt-host broker.emqx.io \
  --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
```

With successful data polling and publishing, you can subscribe the default data topic `modpoll/modsim01/data` on the same MQTT broker `broker.emqx.io` to view the collected data.

The MQTT topics can be customized by providing the following arguments,

  - `mqtt-publish-topic-pattern`
  - `mqtt-subscribe-topic-pattern`
  - `mqtt-diagnostics-topic-pattern`

See [document](https://gavinying.github.io/modpoll/usage.html#Named%20Arguments) for details.

> ⚠️ **Note:** The old `--mqtt-topic-prefix` argument is now deprecated and will be removed in the future release. Suggest to use `--mqtt-xxx-topic-pattern` in new project. If both are used, `--mqtt-topic-prefix` argument will take precedence in order to keep backward compatibility until it is removed.


<p align="center">
  <img src="docs/assets/screencast-modpoll-mqtt.gif">
</p>


### Write registers via MQTT publish

The *modpoll* tool will subscribe to the topic `modpoll/{{device_name}}/set` by default once it successfully connected to MQTT broker, user can write device register(s) via MQTT publish,

- To write a single holding register (address at `40001`)

  ```json
  {
    "object_type": "holding_register",
    "address": 40001,
    "value": 12
  }
  ```

- To write multiple holding registers (address starting from `40001`)

  ```json
  {
    "object_type": "holding_register",
    "address": 40001,
    "value": [12, 13, 14, 15]
  }
  ```


## Run with docker

A docker image has been provided for user to directly run the tool without local installation,

  ```bash
  docker run --rm topmaker/modpoll
  ```

It shows the version of the tool by default.

Similar to the above *modsim* test, we can poll data with `docker run`, in order to avoid printing out received data, the argument `--daemon` or `-d` is recommended to use with docker.

  ```bash
  docker run --rm topmaker/modpoll \
    modpoll -d \
      --tcp modsim.topmaker.net \
      --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
  ```

If you want to load a local configure file, you need to mount a local folder onto container volume,
for example, if the child folder `examples` contains the config file `modsim.csv`, we can use it via the following command,

  ```bash
  docker run --rm -v $(pwd)/examples:/app/examples topmaker/modpoll \
    modpoll -d \
      --tcp modsim.topmaker.net \
      --config /app/examples/modsim.csv
  ```


## Example Use Cases

- Connect to Modbus TCP device

  ```bash
  modpoll \
    --tcp 192.168.1.10 \
    --config examples/modsim.csv
  ```

- Connect to Modbus RTU device

  ```bash
  modpoll \
    --rtu /dev/ttyUSB0 \
    --rtu-baud 9600 \
    --config contrib/eniwise/scpms6.csv
  ```

- Connect to Modbus TCP device and publish data to MQTT broker

  ```bash
  modpoll \
    --tcp modsim.topmaker.net \
    --mqtt-host broker.emqx.io \
    --config examples/modsim.csv
  ```

- Connect to Modbus TCP device and export data to local csv file

  ```bash
  modpoll \
    --tcp modsim.topmaker.net \
    --export data.csv \
    --config examples/modsim.csv
  ```

- Connect to Modbus TCP devices using multiple config files

  ```bash
  modpoll \
    --tcp modsim.topmaker.net \
    --config examples/modsim.csv examples/modsim2.csv
  ```


> Refer to the [documentation](https://gavinying.github.io/modpoll) site for more details about the configuration and examples.

> *If you find this tool useful, please support us by starring 🌟 our repository to encourage further improvements.*

## Credits

The implementation of this project is heavily inspired by the following two projects:
- https://github.com/owagner/modbus2mqtt (MIT license)
- https://github.com/mbs38/spicierModbus2mqtt (MIT license)

Thanks to Max Brueggemann and Oliver Wagner for their great work.


## License

MIT © 2021-2024, Ying Shaodong
