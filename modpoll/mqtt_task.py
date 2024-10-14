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
        log_level: str = "INFO",
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
        self.loglevel = log_level

        self.mqtt_client: Optional[MQTTClient] = None
        self.clean_start_or_session = qos == 0
        self.rx_queue: Queue = Queue(maxsize=1000)
        self.logger = logging.getLogger(__name__)

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
            self.logger.debug("Connected to MQTT broker.")
            if session_present:
                self.logger.info("MQTT session present, reusing existing session")
            else:
                self.logger.info("Created new MQTT session.")
                for topic in self.subscribe_topics:
                    self.logger.info(
                        f"Subscribe to topic: {topic} with QoS: {self.qos}"
                    )
                    client.subscribe(topic, self.qos)
        else:
            self.logger.warning(f"Connection failed with reason code: {rc}")

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        if isinstance(reason_codes, int):
            reason_codes = [reason_codes]
        for rc in reason_codes:
            if rc == 0 or rc == 1:
                self.logger.info("Subscribed successfully.")
            else:
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
        msg = (message.topic, message.payload)
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

    def _setup_tls(self):
        try:
            tls_versions = {
                "tlsv1.2": ssl.PROTOCOL_TLSv1_2,
                "tlsv1.1": ssl.PROTOCOL_TLSv1_1,
                "tlsv1": ssl.PROTOCOL_TLSv1,
            }
            tlsVersion = tls_versions.get(self.tls_version.lower(), ssl.PROTOCOL_TLS)
            cert_required = ssl.CERT_NONE if self.insecure else ssl.CERT_REQUIRED
            self.mqtt_client.tls_set(
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

    def setup(self) -> bool:
        try:
            clientid = self.clientid or ("" if self.qos == 0 else socket.gethostname())

            if self.mqtt_version == "5.0":
                self.mqtt_client = MQTTClient(
                    CallbackAPIVersion.VERSION2,
                    client_id=clientid,
                    protocol=MQTTProtocolVersion.MQTTv5,
                )
            else:
                self.mqtt_client = MQTTClient(
                    CallbackAPIVersion.VERSION2,
                    client_id=clientid,
                    clean_session=self.clean_start_or_session,
                    protocol=MQTTProtocolVersion.MQTTv311,
                )

            if self.use_tls:
                self._setup_tls()

            if self.user:
                self.mqtt_client.username_pw_set(self.user, self.password)

            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_subscribe = self._on_subscribe
            self.mqtt_client.on_message = self._on_message
            self.mqtt_client.on_publish = self._on_publish
            self.mqtt_client.on_disconnect = self._on_disconnect
            if self.loglevel.upper() == "DEBUG":
                self.mqtt_client.on_log = self._on_log

            return True
        except Exception as ex:
            self.logger.error(f"MQTT client setup error: {ex}")
            return False

    def connect(self) -> bool:
        if not self.mqtt_client:
            self.logger.error("MQTT client not initialized. Call setup() first.")
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

            self.mqtt_client.connect(**connect_kwargs)
            self.mqtt_client.loop_start()
            return True
        except (OSError, MQTTException) as ex:
            self.logger.error(f"MQTT connection error: {ex}")
            return False

    def publish(
        self, topic: str, msg: str, qos: Optional[int] = None, retain: bool = False
    ) -> Optional[MQTTMessageInfo]:
        if not self.mqtt_client:
            self.logger.error("MQTT client not initialized. Call setup() first.")
            return None

        qos = self.qos if qos is None else qos

        if not self.mqtt_client.is_connected():
            if qos == 0:
                self.logger.warning(
                    "MQTT client not connected and QoS is 0, skipping publish"
                )
                return None
            self.logger.warning("MQTT client not connected, attempting to reconnect")
            if not self.connect():
                return None

        try:
            pubinfo = self.mqtt_client.publish(topic, msg, qos, retain)
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

    def receive(self) -> Tuple[Optional[str], Optional[bytes]]:
        try:
            topic, payload = self.rx_queue.get(block=False)
            return topic, payload
        except queue.Empty:
            return None, None

    def is_connected(self) -> bool:
        return self.mqtt_client is not None and self.mqtt_client.is_connected()

    def close(self) -> None:
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except MQTTException as ex:
                self.logger.error(f"Error during MQTT client closure: {ex}")
        else:
            self.logger.warning("MQTT client not initialized, nothing to close.")
