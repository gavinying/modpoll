> **2.x development branch.** This checkout accepts WoT TM/TD JSON using profile 0.2. CSV remains supported on the 1.x `main` branch. Install the current preview with `pip install "modpoll[serial]==2.0.0a2"`. Stable 1.x remains available with `pip install "modpoll<2"`. For development, run `mise install` and `mise exec -- poetry install --all-extras`, then prefix the examples below with `mise exec -- poetry run`.

# Modpoll - A New Command-line Tool for Modbus and MQTT

[![Release](https://img.shields.io/github/v/release/top-maker/modpoll)](https://img.shields.io/github/v/release/top-maker/modpoll)
[![Build status](https://img.shields.io/github/actions/workflow/status/top-maker/modpoll/main.yml?branch=main)](https://github.com/top-maker/modpoll/actions/workflows/main.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/top-maker/modpoll)](https://img.shields.io/github/license/top-maker/modpoll)
[![Downloads](https://static.pepy.tech/badge/modpoll/week)](https://pepy.tech/project/modpoll)


> Learn more about *modpoll* usage at [documentation](https://top-maker.github.io/modpoll) site.

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

This tool tested on Python 3.10+ (Ubuntu 22.04+ or equivalent), the package is available in the [Python Package Index](https://pypi.org/), users can easily install it using `pip` or `pipx`. Ubuntu 20.04 and Python 3.8 are no longer supported.

### Using PIP

Install *modpoll* using the following command,

```bash
pip install "modpoll==2.0.0a2"
```

Optionally, [pyserial](https://pyserial.readthedocs.io/) library can be installed for Modbus-RTU communication,

```bash
pip install 'modpoll[serial]==2.0.0a2'
```

Upgrade the tool via the following command,

```bash
pip install -U --pre "modpoll<3"
```

### On Windows

It is recommended to use `pipx` for installing *modpoll* on Windows, refer to [here](https://pypa.github.io/pipx/installation/) for more information about `pipx`.

Once `pipx` installed, you can run the following command in a Command Prompt terminal.

```PowerShell
pipx install "modpoll==2.0.0a2"
```

Upgrade the tool via the following command,

```PowerShell
pipx upgrade modpoll
```

## Quickstart

Use the public Modbus TCP simulator at `modsim.topmaker.net:502` for a quick test:

```bash
modpoll --once \
  --tcp modsim.topmaker.net --tcp-port 502 \
  --config examples/modsim.tm.json
```

### Test modpoll against modsim

This example uses the [modsim v2 development source](https://github.com/top-maker/modsim/tree/v2) and modpoll v2 with
profile 0.2 (`modpoll==2.0.0a2` or a compatible v2 checkout). The published
modsim `2.0.0a1` image predates the managed commands used here. Run these
commands from the modsim repository root; install modpoll separately. The
simulator and broker run locally, and no physical device is needed.

Start the simulator and check its status:

```bash
docker compose up -d --build
docker compose exec -T modsim python -m modsim ps
```

Wait until `ps` reports `"running": true` before exporting the TD of the
running ADAM-6024 instance:

```bash
docker compose exec -T modsim python -m modsim export --running \
  --device io-loopback -o /tmp/adam-6024.td.json
docker compose cp modsim:/tmp/adam-6024.td.json ./adam-6024.td.json
```

In another terminal, still in the modsim directory, poll the TD and save a
snapshot using the modpoll executable from your v2 installation:

```bash
modpoll --once --interval 0 --tcp 127.0.0.1 --tcp-port 5020 \
  --config ./adam-6024.td.json --export ./adam-6024-snapshot.json
```

On a fresh deployment the snapshot contains `adam6024_raw` with `AO0_RAW: 100`
and `AI0_RAW: 100`; previously written values may differ. The exported TD
contains Unit ID 2, so the command targets the second device. The TD preserves
the actual Modbus Forms and project profile 0.2 acquisition metadata.

#### Optional: write via a local MQTT broker

Start a temporary local broker and a continuously running modpoll process:

```bash
docker run --rm -d --name modpoll-demo-mqtt -p 127.0.0.1:1883:1883 \
  eclipse-mosquitto:2 mosquitto -c /mosquitto-no-auth.conf
modpoll --interval 0 --rate 1 --tcp 127.0.0.1 --tcp-port 5020 \
  --config ./adam-6024.td.json --mqtt-host 127.0.0.1 --mqtt-port 1883
```

After modpoll reports its MQTT connection, open another terminal and send a
non-retained write command to the topic named for the TD's `title`:

```bash
docker exec modpoll-demo-mqtt mosquitto_pub -h 127.0.0.1 \
  -t modpoll/adam6024_raw/set \
  -m '{"object_type":"holding_register","address":10,"value":432}'
```

Run the one-shot polling command again. `AO0_RAW` and the simulated loopback
`AI0_RAW` should both read `432`. This is a raw Modbus value in a synthetic
scenario, not a verified electrical range or behavior of a physical ADAM device.
The broker example has no authentication and is published only on host loopback.

Stop the continuous modpoll process with Ctrl+C, then clean up the processes
started for this example:

```bash
docker stop modpoll-demo-mqtt
docker compose down
```

The TD and JSON snapshot remain in the current directory for inspection. The
modsim v2 source and modpoll v2 use the independently published
`modpoll-wot==0.2.0a1`; their application versions are not required to match.
The two repositories have separate release and test lifecycles.

### Modbus ASCII and framers

- Serial transports: use `--serial PORT --framer ascii` (alias: `--rtu` still accepted); pyserial URLs such as `socket://host:port` and `rfc2217://host:port` work for serial-over-TCP tunnels.
- Serial supports framers `ascii` and `rtu` (pymodbus defaults to RTU if `--framer default`). Binary framer is no longer supported in pymodbus 3.9+.

### Prepare a WoT configuration

Use [examples/modsim.tm.json](examples/modsim.tm.json) for the simulator model or
[examples/modsim.generated.td.json](examples/modsim.generated.td.json) for its
generated local TCP instance.
Both preserve the four original blocks and 37 output references. `--unit-id`
overrides each model's optional root `modv:unitID` (fallback 1); a concrete TD's forms must agree with it.
The existing transport, polling, output and MQTT arguments remain available.

See the [current profile](packages/modpoll-wot/profile.md) for field mapping,
access flags, byte order, multiplier semantics and supported limits; the
[0.1 contract](packages/modpoll-wot/CONTRACT.md) documents compatibility.
The configuration loader rejects CSV and reports invalid model fields before
polling. Each model describes one device; use multiple `--config` paths for
multiple devices. Give each model a unique `title`, which is the output device name.

Physical RS485 polling has also been verified by the maintainer with an Eastron
meter (2026-10-28). See [validation](docs/validation.rst) for the evidence scope and
[contributed mappings](contrib/README.md) for vendor references.

For a complete local simulator/MQTT demonstration, use the repository's
[Docker Compose example](examples/README.md).

### MQTT data and write behavior

The local example above uses the `adam6024_raw` TD title for its default topics:
`modpoll/adam6024_raw/data` for samples and `modpoll/adam6024_raw/set` for
write commands. The publish, subscribe and diagnostics topic patterns are
configurable; see the [MQTT documentation](docs/usage.rst).

Writes use literal Modbus PDU addresses and raw values. Holding-register arrays
use FC16 and must contain 1–123 unsigned 16-bit values within the address range.
Invalid, oversized, malformed, ambiguous or retained write messages are ignored
and logged. Brokers can clear the retained flag on live forwarding, so configure
the broker not to retain commands on the set topic; QoS does not make a write
exactly once.

When a sample is invalid in a poll cycle, modpoll omits it from MQTT output and
writes `null` for that reference in the JSON snapshot. Snapshots from multiple
configuration files are combined and replaced atomically. When `--timestamp` is
enabled, the timestamp is the start time of the poll cycle in Unix seconds.


## Run with docker

A docker image has been provided for user to directly run the tool without local installation,

  ```bash
  docker run --rm topmaker/modpoll:2.0.0a2
  ```

It shows the version of the tool by default.

On Linux, host networking connects the container to a simulator on the host.
Mount the JSON configuration into the container; ``--daemon`` suppresses tables.

If you want to load a local configure file, you need to mount a local folder onto container volume,
for example, if the child folder `examples` contains the config file `modsim.tm.json`, we can use it via the following command,

  ```bash
  docker run --rm --network host -v "$(pwd)/examples:/app/examples:ro" topmaker/modpoll:2.0.0a2 \
    modpoll -d \
      --tcp 127.0.0.1 --tcp-port 5020 \
      --config /app/examples/modsim.tm.json
  ```


## Example Use Cases

- Connect to Modbus TCP device

  ```bash
  modpoll \
    --tcp 192.168.1.10 \
    --config examples/modsim.tm.json
  ```

- Connect to Modbus serial device

  ```bash
  modpoll \
    --serial /dev/ttyUSB0 \
    --serial-baud 9600 \
    --config examples/modsim.tm.json
  ```

- Connect to Modbus TCP device and publish data to MQTT broker

  ```bash
  modpoll \
    --tcp 127.0.0.1 --tcp-port 5020 \
    --mqtt-host broker.emqx.io \
    --config examples/modsim.tm.json
  ```

- Connect to Modbus TCP device and export a local JSON snapshot

  ```bash
  modpoll \
    --tcp 127.0.0.1 --tcp-port 5020 \
    --export data.json \
    --config examples/modsim.tm.json
  ```

> Refer to the [documentation](https://top-maker.github.io/modpoll) site for more details about the configuration and examples.

> *If you find this tool useful, please support us by starring 🌟 our repository to encourage further improvements.*

## Credits

The implementation of this project is heavily inspired by the following two projects:
- https://github.com/owagner/modbus2mqtt (MIT license)
- https://github.com/mbs38/spicierModbus2mqtt (MIT license)

Thanks to Max Brueggemann and Oliver Wagner for their great work.


## License

MIT © 2021-2026, Ying Shaodong
