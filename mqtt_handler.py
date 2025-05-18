import paho.mqtt.client as mqtt
import json
import uuid
import re

def get_mac_address():
    mac = uuid.getnode()
    return ':'.join(['{:02x}'.format((mac >> ele) & 0xff) for ele in range(40, -1, -8)])

def make_safe_id(pid_id):
    # Erlaubt nur Buchstaben, Zahlen und Unterstriche
    return re.sub(r'[^a-zA-Z0-9_]', '_', pid_id.replace(" ", "_"))

class MqttHandler:
    def __init__(self, broker, port, username, password, topic_prefix, device_name="OBD2 Dongle", log_enabled=True):
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.connect(broker, port, 60)
        self.topic_prefix = topic_prefix
        self.initialized_pids = set()
        self.device_name = device_name
        self.mac_address = get_mac_address()
        self.log_enabled = log_enabled

    def on_connect(self, client, userdata, flags, rc):
        if self.log_enabled:
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print(f"Failed to connect, return code {rc}")

    def publish(self, topic, payload, retain=False):
        self.client.publish(topic, json.dumps(payload), retain=retain)

    def start_loop(self):
        self.client.loop_start()

    def stop_loop(self):
        self.client.loop_stop()

    def initialize_pid(self, pid, name, unit, pid_id):
        """
        Publish Home Assistant MQTT discovery message for a new PID.
        """
        if pid_id in self.initialized_pids:
            return  # Avoid reinitializing the same PID

        safe_pid_id = make_safe_id(pid_id)  # Make the PID ID safe for MQTT
        discovery_topic = f"homeassistant/sensor/{safe_pid_id}/config"
        state_topic = f"{self.topic_prefix}/{safe_pid_id}/state"
        payload = {
            "name": name,
            "state_topic": state_topic,
            "unit_of_measurement": unit,
            "device_class": None,  # Optional: Define Home Assistant device class if applicable
            "state_class": "measurement",  # Define state class (e.g., measurement)
            "unique_id": f"obd2_{safe_pid_id}",
            "device": {
                "identifiers": [f"obd2_device_{self.mac_address}"],
                "name": self.device_name,
                "manufacturer": "Michael Krasselt",
                "model": "OBD2 Dongle via PI"
            }
        }
        # Publish discovery message
        self.publish(discovery_topic, payload, retain=True)
        if self.log_enabled:
            print(f"Initialized PID {name} with MQTT ID {pid_id} in Home Assistant")
        self.initialized_pids.add(pid_id)

    def update_pid_value(self, pid_id, value):
        """
        Update the value of a PID in Home Assistant.
        """
        safe_pid_id = make_safe_id(pid_id)  # Make the PID ID safe for MQTT
        state_topic = f"{self.topic_prefix}/{safe_pid_id}/state"
        self.publish(state_topic, value)
        if self.log_enabled:
            print(f"Updated PID with MQTT ID {pid_id} to value {value}")
