import argparse

from . import __version__


def get_parser():
    parser = argparse.ArgumentParser(
        description=f"Modpoll v{__version__} - A New Command-line Tool for Modbus and MQTT"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"v{__version__}",
    )
    parser.add_argument(
        "-f",
        "--config",
        required=True,
        help="A local path or URL of Modbus configuration file. Required!",
        nargs="+",
    )
    parser.add_argument(
        "-d",
        "--daemon",
        action="store_true",
        help="Run in daemon mode without printing result. Recommended to use with docker",
    )
    parser.add_argument(
        "-r",
        "--rate",
        type=float,
        default=10.0,
        help="The sampling rate (s) to poll modbus device, Defaults to 10.0",
    )
    parser.add_argument(
        "-1", "--once", action="store_true", help="Only run polling at one time"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="The time interval in seconds between two polling, Defaults to 1.0",
    )
    parser.add_argument(
        "--tcp", help="Act as a Modbus TCP master, connecting to host TCP"
    )
    parser.add_argument(
        "--tcp-port", type=int, default=502, help="Port for MODBUS TCP. Defaults to 502"
    )
    parser.add_argument(
        "--udp", help="Act as a Modbus UDP master, connecting to host UDP"
    )
    parser.add_argument(
        "--udp-port", type=int, default=502, help="Port for MODBUS UDP. Defaults to 502"
    )
    parser.add_argument("--rtu", help="pyserial URL (or port name) for RTU serial port")
    parser.add_argument(
        "--rtu-baud",
        type=int,
        default=9600,
        help="Baud rate for serial port. Defaults to 9600",
    )
    parser.add_argument(
        "--rtu-parity",
        choices=["none", "odd", "even"],
        default="none",
        help="Parity for serial port. Defaults to none",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Response time-out seconds for MODBUS devices, Defaults to 3.0",
    )
    parser.add_argument(
        "-o",
        "--export",
        default=None,
        help="The file name to export references/registers",
    )
    parser.add_argument(
        "--mqtt-version",
        choices=["3.1.1", "5.0"],
        default="3.1.1",
        help="MQTT version. Defaults to MQTT v3.1.1",
    )
    parser.add_argument(
        "--mqtt-host",
        default=None,
        help="MQTT server address. Skip MQTT setup if not specified",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="1883 for non-TLS or 8883 for TLS, Defaults to 1883",
    )
    parser.add_argument(
        "--mqtt-clientid",
        default=None,
        help="MQTT client name, If qos > 0, set unique name for multiple clients",
    )
    parser.add_argument(
        "--mqtt-topic-prefix",
        default=None,
        help="(DEPRECATED) Topic prefix for MQTT subscribing/publishing. Defaults to None",
    )
    parser.add_argument(
        "--mqtt-publish-topic-pattern",
        default="modpoll/<device_name>/data",
        help='Topic pattern for MQTT publish. Use <device_name> as placeholder for the device names in Modbus config. Defaults to "modpoll/<device_name>"',
    )
    parser.add_argument(
        "--mqtt-subscribe-topic-pattern",
        default="modpoll/+/set",
        help='Topic pattern for MQTT subscribe. Defaults to "modpoll/+/set"',
    )
    parser.add_argument(
        "--mqtt-diagnostics-topic-pattern",
        default="modpoll/<device_name>/diagnostics",
        help="Topic pattern for MQTT diagnostics. Use <device_name> as placeholder for the device names in Modbus config. Defaults to modpoll/<device_name>/diagnostics",
    )
    parser.add_argument(
        "--mqtt-qos",
        choices=[0, 1, 2],
        type=int,
        default=0,
        help="MQTT QoS value. Defaults to 0",
    )
    parser.add_argument(
        "--mqtt-user", default=None, help="Username for authentication (optional)"
    )
    parser.add_argument(
        "--mqtt-pass", default=None, help="Password for authentication (optional)"
    )
    parser.add_argument("--mqtt-use-tls", action="store_true", help="Use TLS")
    parser.add_argument(
        "--mqtt-insecure",
        action="store_true",
        help="Use TLS without providing certificates",
    )
    parser.add_argument("--mqtt-cacerts", default=None, help="Path to ca keychain")
    parser.add_argument(
        "--mqtt-tls-version",
        choices=["tlsv1.2", "tlsv1.1", "tlsv1"],
        default="tlsv1.2",
        help="TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1",
    )
    parser.add_argument(
        "--mqtt-single",
        action="store_true",
        help="Publish each value in a single topic. If not specified, groups all values in one topic.",
    )
    parser.add_argument(
        "--diagnostics-rate",
        type=float,
        default=0,
        help="Time in seconds as publishing period for each device diagnostics",
    )
    parser.add_argument(
        "--autoremove",
        action="store_true",
        help="Automatically remove poller if modbus communication has failed 3 times.",
    )
    parser.add_argument(
        "--loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set log level, Defaults to INFO",
    )
    parser.add_argument(
        "--timestamp", action="store_true", help="Add timestamp to the result"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=0,
        help="Time to delay sending first request in seconds after connecting. Default to 0",
    )
    parser.add_argument(
        "--framer",
        default="default",
        choices=["default", "ascii", "binary", "rtu", "socket"],
        help="The type of framer for modbus message. Use default framer if not specified.",
    )
    return parser
