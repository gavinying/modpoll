import logging
import socket

import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException

# global objects
log = None
mqttc = None
initial_connection_made = False


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


def mqttc_setup(args):
    global log
    log = logging.getLogger(__name__)
    try:
        global mqttc
        mqttc = mqtt.Client(socket.gethostname(), clean_session=(args.mqtt_qos == 0))
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
        #     mqttc.tls_set(ca_certs=args.mqtt_cacerts, certfile=None, keyfile=None, cert_reqs=cert_required,
        #                    tls_version=tlsVersion)
        #
        #     if args.mqtt_insecure:
        #         mqttc.tls_insecure_set(True)

        if args.mqtt_user:
            mqttc.username_pw_set(args.mqtt_user, args.mqtt_password)

        mqttc.on_message = _on_message
        mqttc.on_connect = _on_connect
        mqttc.on_disconnect = _on_disconnect
        mqttc.on_publish = _on_publish
        mqttc.on_subscribe = _on_subscribe

        if "DEBUG" == args.loglevel.upper():
            mqttc.on_log = _on_log

        # try to connect
        mqttc.connect(host=args.mqtt_host, port=args.mqtt_port, keepalive=60)

        # start loop - let paho manage connection
        mqttc.loop_start()

        global initial_connection_made
        initial_connection_made = True
        return True

    except Exception as ex:
        log.error(f"mqtt connection error: {ex}")
        # raise ex
        return False


def mqttc_publish(topic, msg, qos=0, retain=False):
    global mqttc
    try:
        if not mqttc:
            return
        if not mqttc.is_connected() and qos == 0:
            return
        pubinfo = mqttc.publish(topic, msg, qos, retain)
        # pubinfo.wait_for_publish()
        log.debug(f"publishing MQTT topic: {topic}, msg: {msg}, qos: {qos}, RC: {pubinfo.rc}")
        log.info(f"published message to topic: {topic}")
        return pubinfo
    except MQTTException as ex:
        log.error(f"Error publishing MQTT topic: {topic}, msg: {msg}, qos: {qos}")
        raise ex


def mqttc_close():
    global mqttc
    if mqttc:
        mqttc.loop_stop()
        mqttc.disconnect()
