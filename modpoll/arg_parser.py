import argparse

from . import __version__


def get_parser():
    parser = argparse.ArgumentParser(description=f'modpoll v{__version__} - A Command Line Tool for Modbus')
    parser.add_argument('-v', '--version', action='version', version=f'modpoll v{__version__}')
    parser.add_argument('-f', '--config', required=True,
                        help='A local path or URL of Modbus configuration file. Required!')
    parser.add_argument('-r', '--rate', default=5.0, type=float,
                        help='The sampling rate (s) to poll modbus device, Defaults to 5.0')
    parser.add_argument('-1', '--once', action='store_true',
                        help="Only run polling at one time")
    parser.add_argument('--interval', default=1.0, type=float,
                        help='The time interval in seconds between two polling, Defaults to 1.0')
    parser.add_argument('--tcp',
                        help='Act as a Modbus TCP master, connecting to host TCP')
    parser.add_argument('--tcp-port', default=502, type=int,
                        help='Port for MODBUS TCP. Defaults to 502')
    parser.add_argument('--rtu',
                        help='pyserial URL (or port name) for RTU serial port')
    parser.add_argument('--rtu-baud', default=9600, type=int,
                        help='Baud rate for serial port. Defaults to 9600')
    parser.add_argument('--rtu-parity', default='none', choices=['none', 'odd', 'even'],
                        help='Parity for serial port. Defaults to none')
    parser.add_argument('--timeout', default=3.0, type=float,
                        help='Response time-out seconds for MODBUS devices, Defaults to 3.0')
    parser.add_argument('-o', '--export', default=None,
                        help='The file name to export references/registers')
    parser.add_argument('--mqtt-host', default=None,
                        help='MQTT server address. Skip MQTT setup if not specified')
    parser.add_argument('--mqtt-port', default=1883, type=int,
                        help='1883 for non-TLS or 8883 for TLS, Defaults to 1883')
    parser.add_argument('--mqtt-topic-prefix', default='modpoll/',
                        help='Topic prefix for MQTT subscribing/publishing. Defaults to "modpoll/"')
    parser.add_argument('--mqtt-qos', default=0, type=int, choices=[0, 1, 2],
                        help='MQTT QoS value. Defaults to 0')
    parser.add_argument('--mqtt-user', default=None,
                        help='Username for authentication (optional)')
    parser.add_argument('--mqtt-pass', default=None,
                        help='Password for authentication (optional)')
    parser.add_argument('--mqtt-use-tls', action='store_true',
                        help='Use TLS')
    parser.add_argument('--mqtt-insecure', action='store_true',
                        help='Use TLS without providing certificates')
    parser.add_argument('--mqtt-cacerts', default=None,
                        help="Path to ca keychain")
    parser.add_argument('--mqtt-tls-version', default=None, choices=['tlsv1.2', 'tlsv1.1', 'tlsv1'],
                        help='TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1')
    parser.add_argument('--diagnostics-rate', default=0, type=float,
                        help='Time in seconds as publishing period for each device diagnostics')
    parser.add_argument('--autoremove', action='store_true',
                        help='Automatically remove poller if modbus communication has failed 3 times.')
    parser.add_argument('--loglevel', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set log level, Defaults to INFO')

    return parser
