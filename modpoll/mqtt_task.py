import logging
import queue
import socket
import ssl
from multiprocessing import Queue
from typing import Optional, Tuple, List

from paho.mqtt.client import (
    Client as MQTTClient,
    CallbackAPIVersion,
    ReasonCode,
    MQTTProtocolVersion,
    MQTTMessageInfo,
)
from paho.mqtt import MQTTException


class MqttHandler:
    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        user: Optional[str],
        password: Optional[str],
        clientid: Optional[str],
        qos: int,
        subscribe_topics: List[str] = [],
        use_tls: bool = False,
        tls_version: str = "tlsv1.2",
        cacerts: Optional[str] = None,
        insecure: bool = False,
        mqtt_version: str = "5.0",
    ):
        self.name = name
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.clientid = clientid
        self.qos = qos
        self.subscribe_topics = subscribe_topics
        self.use_tls = use_tls
        self.tls_version = tls_version
        self.cacerts = cacerts
        self.insecure = insecure
        self.mqtt_version = mqtt_version
        self.loglevel = "INFO"

        self.logger = logging.getLogger(name)
        self.mqttc: Optional[MQTTClient] = None
        self.clean_start_or_session = qos == 0
        self.rx_queue: Queue = Queue(maxsize=1000)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if isinstance(flags, dict):  # MQTTv5
            session_present = flags.get("session present", False)
        else:  # MQTTv3
            session_present = flags.session_present

        if isinstance(reason_code, ReasonCode):
            rc = reason_code.value
        else:
            rc = reason_code

        if rc == 0:
            self.logger.info("Connection successful")
            if session_present:
                self.logger.info("Session present, reusing existing session")
            else:
                self.logger.info("New session created")
                for topic in self.subscribe_topics:
                    self.logger.info(
                        f"Subscribe to topic: {topic} with QoS: {self.qos}"
                    )
                    client.subscribe(topic, self.qos)
        else:
            self.logger.warning(f"Connection failed with reason code: {rc}")

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        for rc in reason_codes:
            if rc == 1:
                self.logger.info("Subscribed.")
            elif rc >= 128:
                self.logger.warning(f"Failed to subscribe. Reason code: {rc}")

    def _on_publish(self, client, userdata, mid, reason_codes, properties):
        self.logger.debug(f"Message (mid={mid}) published successfully.")

    def _on_message(self, client, userdata, message):
        if message.retain == 0:
            self.logger.info(f"Receive message ({message.topic}): {message.payload}")
        else:
            self.logger.info(
                f"Receive retained message ({message.topic}): {message.payload}"
            )
        msg = message.topic, message.payload
        try:
            self.rx_queue.put(msg, block=False)
        except queue.Full:
            self.logger.warning("MQTT receiving queue is full, ignoring new message.")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.logger.info("Disconnected.")
        else:
            self.logger.warning(f"Disconnected with error, reason_code={reason_code}.")

    def _on_log(self, client, userdata, level, buf):
        self.logger.debug(f"{level} | {buf}")

    def mqttc_setup(self) -> bool:
        try:
            clientid = self.clientid or ("" if self.qos == 0 else socket.gethostname())

            if self.mqtt_version == "5.0":
                self.mqttc = MQTTClient(
                    CallbackAPIVersion.VERSION2,
                    client_id=clientid,
                    protocol=MQTTProtocolVersion.MQTTv5,
                )
            else:
                self.mqttc = MQTTClient(
                    CallbackAPIVersion.VERSION2,
                    client_id=clientid,
                    clean_session=self.clean_start_or_session,
                    protocol=MQTTProtocolVersion.MQTTv311,
                )

            if self.use_tls:
                self._setup_tls()

            if self.user:
                self.mqttc.username_pw_set(self.user, self.password)

            self.mqttc.on_connect = self._on_connect
            self.mqttc.on_subscribe = self._on_subscribe
            self.mqttc.on_message = self._on_message
            self.mqttc.on_publish = self._on_publish
            self.mqttc.on_disconnect = self._on_disconnect
            if self.loglevel.upper() == "DEBUG":
                self.mqttc.on_log = self._on_log

            return True
        except Exception as ex:
            self.logger.error(f"MQTT client setup error: {ex}")
            return False

    def _setup_tls(self):
        try:
            tls_versions = {
                "tlsv1.2": ssl.PROTOCOL_TLSv1_2,
                "tlsv1.1": ssl.PROTOCOL_TLSv1_1,
                "tlsv1": ssl.PROTOCOL_TLSv1,
            }
            tlsVersion = tls_versions.get(self.tls_version.lower(), ssl.PROTOCOL_TLS)
            cert_required = ssl.CERT_NONE if self.insecure else ssl.CERT_REQUIRED
            self.mqttc.tls_set(
                ca_certs=self.cacerts,
                certfile=None,
                keyfile=None,
                cert_reqs=cert_required,
                tls_version=tlsVersion,
                ciphers=None,
            )
        except ssl.SSLError as ssl_ex:
            self.logger.error(f"SSL setup error: {ssl_ex}")
            raise
        except Exception as ex:
            self.logger.error(f"TLS setup error: {ex}")
            raise

    def mqttc_connect(self) -> bool:
        if not self.mqttc:
            self.logger.error("MQTT client not initialized. Call mqttc_setup() first.")
            return False

        try:
            connect_kwargs = {
                "host": self.host,
                "port": self.port,
                "keepalive": 60,
            }
            if self.mqtt_version == "5.0":
                connect_kwargs["clean_start"] = self.clean_start_or_session
            else:
                connect_kwargs["clean_session"] = self.clean_start_or_session

            self.mqttc.connect(**connect_kwargs)
            self.mqttc.loop_start()
            return True
        except (OSError, MQTTException) as ex:
            self.logger.error(f"MQTT connection error: {ex}")
            return False

    def mqttc_publish(
        self, topic: str, msg: str, qos: int = 0, retain: bool = False
    ) -> Optional[MQTTMessageInfo]:
        if not self.mqttc:
            self.logger.error("MQTT client not initialized. Call mqttc_setup() first.")
            return None
        if not self.mqttc.is_connected():
            if qos == 0:
                self.logger.warning(
                    "MQTT client not connected and QoS is 0, skipping publish"
                )
                return None
            self.logger.warning("MQTT client not connected, attempting to reconnect")
            if not self.mqttc_connect():
                return None

        try:
            pubinfo = self.mqttc.publish(topic, msg, qos, retain)
            self.logger.debug(
                f"Publishing MQTT topic: {topic}, msg: {msg}, qos: {qos}, RC: {pubinfo.rc}"
            )
            self.logger.info(f"Publish message to topic: {topic}")
            return pubinfo
        except MQTTException as ex:
            self.logger.error(
                f"Failed to publish MQTT topic: {topic}, msg: {msg}, qos: {qos}. Error: {ex}"
            )
            return None

    def mqttc_receive(self) -> Tuple[Optional[str], Optional[bytes]]:
        try:
            topic, payload = self.rx_queue.get(block=False)
            return topic, payload
        except queue.Empty:
            return None, None

    def mqttc_connected(self) -> bool:
        return self.mqttc is not None and self.mqttc.is_connected()

    def mqttc_close(self) -> None:
        if self.mqttc:
            try:
                self.mqttc.loop_stop()
                self.mqttc.disconnect()
            except MQTTException as ex:
                self.logger.error(f"Error during MQTT client closure: {ex}")
        else:
            self.logger.warning("MQTT client not initialized, nothing to close.")
