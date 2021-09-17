import logging
import uuid

import paho.mqtt.client as mqtt

# get logger
from paho.mqtt import MQTTException

log = logging.getLogger(__name__)

# global objects
_mqttc = None
_initial_connection_made = False


# Callbacks
def _on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log.info("Connection successful")
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        # client.subscribe(subscribe_topic)
    elif rc == 1:
        log.warning("Connection refused - incorrect protocol version")
    elif rc == 2:
        log.warning("Connection refused - invalid client identifier")
    elif rc == 3:
        log.warning("Connection refused - server unavailable")
    elif rc == 4:
        log.warning("Connection refused - bad username or password")
    elif rc == 5:
        log.warning("Connection refused - not authorised")
    else:
        log.warning("Unknown error")


def _on_disconnect(client, userdata, rc):
    log.info(f"disconnected. rc={rc}.")


def _on_message(client, obj, msg):
    if msg.retain == 0:
        log.info(f"Receive message ({msg.topic}): {msg.payload}")
    else:
        log.info(f"Receive retained message ({msg.topic}): {msg.payload}")


def _on_publish(client, obj, mid):
    log.debug("Sent.")


def _on_subscribe(client, obj, mid, granted_qos):
    log.debug("Subscribed.")


def _on_log(client, obj, level, string):
    log.debug(f"{level} | {string}")


def mqttc_setup(host: str, port=1883, user=None, password="", qos=0, mqtt_debug=False):
    try:
        # If you want to use a specific client id, use
        # mqttc = mqtt.Client("client-id")
        # but note that the client id must be unique on the broker. Leaving the client
        # id parameter empty will generate a random id for you.
        global _mqttc, _initial_connection_made
        _mqttc = mqtt.Client(str(uuid.uuid4()), clean_session=(qos == 0))
        # if args.mqtt_use_tls:
        #     if args.mqtt_tls_version == "tlsv1.2":
        #         tlsVersion = ssl.PROTOCOL_TLSv1_2
        #     elif args.mqtt_tls_version == "tlsv1.1":
        #         tlsVersion = ssl.PROTOCOL_TLSv1_1
        #     elif args.mqtt_tls_version == "tlsv1":
        #         tlsVersion = ssl.PROTOCOL_TLSv1
        #     elif args.mqtt_tls_version is None:
        #         tlsVersion = None
        #     else:
        #         print("Unknown TLS version - ignoring")
        #         tlsVersion = None
        #
        #     if not args.mqtt_insecure:
        #         cert_required = ssl.CERT_REQUIRED
        #     else:
        #         cert_required = ssl.CERT_NONE
        #
        #     _mqttc.tls_set(ca_certs=args.cacerts, certfile=None, keyfile=None, cert_reqs=cert_required,
        #                    tls_version=tlsVersion)
        #
        #     if args.mqtt_insecure:
        #         _mqttc.tls_insecure_set(True)

        if user and password:
            _mqttc.username_pw_set(user, password)

        _mqttc.on_message = _on_message
        _mqttc.on_connect = _on_connect
        _mqttc.on_disconnect = _on_disconnect
        _mqttc.on_publish = _on_publish
        _mqttc.on_subscribe = _on_subscribe

        if mqtt_debug:
            _mqttc.on_log = _on_log

        # try to connect
        _mqttc.connect(host=host, port=port, keepalive=60)

        # start loop - let paho manage connection
        _mqttc.loop_start()

        _initial_connection_made = True
        return True

    except Exception as ex:
        log.error("mqtt connection error")
        # raise ex
        return False


def mqttc_publish(topic, msg, qos=0, retain=False):
    global _mqttc
    try:
        if not _mqttc:
            return
        if not _mqttc.is_connected() and qos == 0:
            return
        pubinfo = _mqttc.publish(topic, msg, qos, retain)
        # pubinfo.wait_for_publish()
        log.debug(f"publishing MQTT topic: {topic}, msg: {msg}, qos: {qos}, RC: {pubinfo.rc}")
        log.info(f"published message to topic: {topic}")
        return pubinfo
    except MQTTException as ex:
        log.error(f"Error publishing MQTT topic: {topic}, msg: {msg}, qos: {qos}")
        raise ex


def mqttc_close():
    global _mqttc
    if _mqttc:
        _mqttc.loop_stop()
        _mqttc.disconnect()
