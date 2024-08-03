import logging
import queue
import socket
import ssl
from multiprocessing import Queue

from paho.mqtt.client import (
    Client as MQTTClient,
    CallbackAPIVersion,
    ReasonCode,
    MQTTProtocolVersion,
)
from paho.mqtt import MQTTException

args = None
logger = None
mqttc = None
mqtt_initial_connection_made = False
rx_queue = Queue(maxsize=1000)


class MqttMsg:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload


# Callbacks
def _on_connect(client, userdata, flags, reason_code, properties):
    # check if the broker already has a persistent session for this client
    if isinstance(flags, dict):  # MQTTv5
        session_present = flags.get("session present", False)
    else:  # MQTTv3
        session_present = flags.session_present

    if isinstance(reason_code, ReasonCode):
        rc = reason_code.value
    else:
        rc = reason_code

    if rc == 0:
        logger.info("Connection successful")
        if session_present:
            logger.info("Session present, reusing existing session")
        else:
            logger.info("New session created")
            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            if "subscribe_topic" in userdata:
                topic = userdata.get("subscribe_topic")
                qos = userdata.get("subscribe_qos", 0)  # Default to QoS 0
                logger.info(f"Subscribe to topic: {topic} with QoS: {qos}")
                client.subscribe(topic, qos)
    else:
        logger.warning(f"Connection failed with reason code: {reason_code}")


def _on_subscribe(client, userdata, mid, reason_codes, properties):
    for sub_result in reason_codes:
        if sub_result == 1:
            logger.info("Subscribed.")
        # Any reason code >= 128 is a failure.
        if sub_result >= 128:
            logger.warning("Failed to subscribe.")


def _on_publish(client, userdata, mid, reason_codes, properties):
    logger.debug("Sent.")


def _on_message(client, userdata, message):
    if message.retain == 0:
        logger.info(f"Receive message ({message.topic}): {message.payload}")
    else:
        logger.info(f"Receive retained message ({message.topic}): {message.payload}")
    obj = message.topic, message.payload
    try:
        rx_queue.put(obj, block=False)
    except queue.Full:
        logger.warning("MQTT receiving queue is full, ignoring new message.")


def _on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("Disconnected.")
    if reason_code > 0:
        logger.warning(f"Disconnected with error, reason_code={reason_code}.")


def _on_log(client, userdata, level, buf):
    logger.debug(f"{level} | {buf}")


def mqttc_setup(config) -> bool:
    global args
    args = config
    global logger
    logger = logging.getLogger(__name__)
    try:
        if args.mqtt_clientid is None:
            if args.mqtt_qos == 0:
                clientid = ""
            else:
                clientid = socket.gethostname()
        else:
            clientid = args.mqtt_clientid
        global mqttc

        if args.mqtt_use_tls:
            if args.mqtt_tls_version == "tlsv1.2":
                tlsVersion = ssl.PROTOCOL_TLSv1_2
            elif args.mqtt_tls_version == "tlsv1.1":
                tlsVersion = ssl.PROTOCOL_TLSv1_1
            elif args.mqtt_tls_version == "tlsv1":
                tlsVersion = ssl.PROTOCOL_TLSv1
            else:
                tlsVersion = ssl.PROTOCOL_TLS

            if not args.mqtt_insecure:
                cert_required = ssl.CERT_REQUIRED
            else:
                cert_required = ssl.CERT_NONE

            mqttc.tls_set(
                ca_certs=args.mqtt_cacerts,
                certfile=None,
                keyfile=None,
                cert_reqs=cert_required,
                tls_version=tlsVersion,
                ciphers=None,
            )

        if args.mqtt_user:
            mqttc.username_pw_set(args.mqtt_user, args.mqtt_pass)

        clean_start_or_session = args.mqtt_qos == 0

        if args.mqtt_version == "5.0":
            mqttc = MQTTClient(
                CallbackAPIVersion.VERSION2,
                client_id=clientid,
                userdata={"qos": args.mqtt_qos},
                protocol=MQTTProtocolVersion.MQTTv5,
            )
            mqttc.on_connect = _on_connect
            mqttc.on_subscribe = _on_subscribe
            mqttc.on_message = _on_message
            mqttc.on_publish = _on_publish
            mqttc.on_disconnect = _on_disconnect

            if "DEBUG" == args.loglevel.upper():
                mqttc.on_log = _on_log
            mqttc.connect(
                host=args.mqtt_host,
                port=args.mqtt_port,
                keepalive=60,
                clean_start=clean_start_or_session,
            )
        else:
            mqttc = MQTTClient(
                CallbackAPIVersion.VERSION2,
                client_id=clientid,
                clean_session=clean_start_or_session,
                userdata={"qos": args.mqtt_qos},
                protocol=MQTTProtocolVersion.MQTTv311,
            )
            mqttc.on_connect = _on_connect
            mqttc.on_subscribe = _on_subscribe
            mqttc.on_message = _on_message
            mqttc.on_publish = _on_publish
            mqttc.on_disconnect = _on_disconnect

            if "DEBUG" == args.loglevel.upper():
                mqttc.on_log = _on_log
            mqttc.connect(host=args.mqtt_host, port=args.mqtt_port, keepalive=60)

        # start loop - let paho manage connection
        mqttc.loop_start()

        global mqtt_initial_connection_made
        mqtt_initial_connection_made = True
        return True

    except Exception as ex:
        logger.error(f"mqtt connection error: {ex}")
        return False


def mqttc_publish(topic, msg, qos=0, retain=False):
    try:
        if not mqttc:
            return
        if not mqttc.is_connected() and qos == 0:
            return
        pubinfo = mqttc.publish(topic, msg, qos, retain)
        logger.debug(
            f"Publishing MQTT topic: {topic}, msg: {msg}, qos: {qos}, RC: {pubinfo.rc}"
        )
        logger.info(f"Publish message to topic: {topic}")
        return pubinfo
    except MQTTException as ex:
        logger.error(f"Failed to publish MQTT topic: {topic}, msg: {msg}, qos: {qos}")
        raise ex


def mqttc_receive():
    try:
        topic, payload = rx_queue.get(block=False)
        return topic, payload
    except queue.Empty:
        return None, None


def mqttc_close():
    if mqttc:
        mqttc.loop_stop()
        mqttc.disconnect()
