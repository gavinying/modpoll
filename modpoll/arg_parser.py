import argparse
import os

from . import __version__


def get_parser():
    parser = argparse.ArgumentParser(description=f'modpoll v{__version__} - A New Command Line Tool for Modbus')
    parser.add_argument('-v', '--version', action='version', version=f'modpoll v{__version__}')
    parser.add_argument('-f', '--config', required=(os.environ.get(key='MODPOLL_CONFIG') == None),
                        default=os.environ.get(key='MODPOLL_CONFIG'),
                        help='A local path or URL of Modbus configuration file. Required!')
    parser.add_argument('-r', '--rate', type=float,
                        default=os.environ.get(key='MODPOLL_RATE', default=5.0),
                        help='The sampling rate (s) to poll modbus device, Defaults to 5.0')
    parser.add_argument('-1', '--once', action='store_true',
                        default=os.environ.get(key='MODPOLL_ONCE'),
                        help="Only run polling at one time")
    parser.add_argument('--interval', type=float,
                        default=os.environ.get(key='MODPOLL_INTERVAL', default=1.0),
                        help='The time interval in seconds between two polling, Defaults to 1.0')
    parser.add_argument('--tcp',
                        default=os.environ.get(key='MODPOLL_TCP'),
                        help='Act as a Modbus TCP master, connecting to host TCP')
    parser.add_argument('--tcp-port', type=int,
                        default=os.environ.get(key='MODPOLL_TCP_PORT', default=502),
                        help='Port for MODBUS TCP. Defaults to 502')
    parser.add_argument('--rtu',
                        default=os.environ.get(key='MODPOLL_RTU'),
                        help='pyserial URL (or port name) for RTU serial port')
    parser.add_argument('--rtu-baud', type=int,
                        default=os.environ.get(key='MODPOLL_RTU_BAUD', default=9600),
                        help='Baud rate for serial port. Defaults to 9600')
    parser.add_argument('--rtu-parity', choices=['none', 'odd', 'even'],
                        default=os.environ.get(key='MODPOLL_RTU_PARITY', default='none'),
                        help='Parity for serial port. Defaults to none')
    parser.add_argument('--timeout', type=float,
                        default=os.environ.get(key='MODPOLL_TIMEOUT', default=3.0),
                        help='Response time-out seconds for MODBUS devices, Defaults to 3.0')
    parser.add_argument('-o', '--export',
                        default=os.environ.get(key='MODPOLL_EXPORT', default=None),
                        help='The file name to export references/registers')
    parser.add_argument('--mqtt-host',
                        default=os.environ.get(key='MODPOLL_MQTT_HOST', default=None),
                        help='MQTT server address. Skip MQTT setup if not specified')
    parser.add_argument('--mqtt-port', type=int,
                        default=os.environ.get(key='MODPOLL_MQTT_PORT', default=1883),
                        help='1883 for non-TLS or 8883 for TLS, Defaults to 1883')
    parser.add_argument('--mqtt-clientid',
                        default=os.environ.get(key='MODPOLL_MQTT_CLIENTID', default=None),
                        help='MQTT client name, If qos > 0, set unique name for multiple clients')
    parser.add_argument('--mqtt-topic-prefix',
                        default=os.environ.get(key='MODPOLL_MQTT_TOPIC_PREFIX', default='modpoll/'),
                        help='Topic prefix for MQTT subscribing/publishing. Defaults to "modpoll/"')
    parser.add_argument('--mqtt-qos', type=int, choices=[0, 1, 2],
                        default=os.environ.get(key='MODPOLL_MQTT_QOS', default=0),
                        help='MQTT QoS value. Defaults to 0')
    parser.add_argument('--mqtt-user',
                        default=os.environ.get(key='MODPOLL_MQTT_USER', default=None),
                        help='Username for authentication (optional)')
    parser.add_argument('--mqtt-pass', 
                        default=os.environ.get(key='MODPOLL_MQTT_PASS', default=None),
                        help='Password for authentication (optional)')
    parser.add_argument('--mqtt-use-tls', action='store_true',
                        default=os.environ.get(key='MODPOLL_MQTT_USE_TLS'),
                        help='Use TLS')
    parser.add_argument('--mqtt-insecure', action='store_true',
                        default=os.environ.get(key='MODPOLL_MQTT_INSECURE'),
                        help='Use TLS without providing certificates')
    parser.add_argument('--mqtt-cacerts', 
                        default=os.environ.get(key='MODPOLL_MQTT_CACERTS', default=None),
                        help="Path to ca keychain")
    parser.add_argument('--mqtt-tls-version', choices=['tlsv1.2', 'tlsv1.1', 'tlsv1'],
                        default=os.environ.get(key='MODPOLL_MQTT_TLS_VERSION', default=None),
                        help='TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1')
    parser.add_argument('--diagnostics-rate', type=float,
                        default=os.environ.get(key='MODPOLL_DIAGNOSTICS_RATE', default=0),
                        help='Time in seconds as publishing period for each device diagnostics')
    parser.add_argument('--autoremove', action='store_true',
                        default=os.environ.get(key='MODPOLL_AUTOREMOVE'),
                        help='Automatically remove poller if modbus communication has failed 3 times.')
    parser.add_argument('--loglevel', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default=os.environ.get(key='MODPOLL_LOGLEVEL', default='INFO'),
                        help='Set log level, Defaults to INFO')
    parser.add_argument('--timestamp', action='store_true',
                        default=os.environ.get(key='MODPOLL_TIMESTAMP'),
                        help='Add timestamp to the result')
    parser.add_argument('--delay', type=int,
                        default=os.environ.get(key='MODPOLL_DELAY', default=0),
                        help='Time to delay sending first request in seconds after connecting. Default to 0')
    parser.add_argument('--mqtt-single', action='store_true',
                        default=os.environ.get(key='MODPOLL_MQTT_SINGLE'),
                        help='Publish each value in a single topic. If not specified groups all values in a single topic.')
    return parser
