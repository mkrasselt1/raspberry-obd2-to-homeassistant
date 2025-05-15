import paho.mqtt.client as mqtt
import json

class MqttHandler:
    def __init__(self, broker, port, username, password, topic_prefix):
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.connect(broker, port, 60)
        self.topic_prefix = topic_prefix
        self.initialized_pids = set()  # Keep track of initialized PIDs to avoid duplicate autodiscovery

    def on_connect(self, client, userdata, flags, rc):
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

    def initialize_pid(self, pid, name, unit, mqtt_id):
        """
        Publish Home Assistant MQTT discovery message for a new PID.
        """
        if mqtt_id in self.initialized_pids:
            return  # Avoid reinitializing the same PID

        discovery_topic = f"homeassistant/sensor/{mqtt_id}/config"
        state_topic = f"{self.topic_prefix}/{mqtt_id}/state"
        payload = {
            "name": name,
            "state_topic": state_topic,
            "unit_of_measurement": unit,
            "device_class": None,  # Optional: Define Home Assistant device class if applicable
            "state_class": "measurement",  # Define state class (e.g., measurement)
            "unique_id": f"obd2_{mqtt_id}",
            "device": {
                "identifiers": ["obd2_device"],
                "name": "OBD2 Dongle",
                "manufacturer": "Michael Krasselt",
                "model": "OBD2 Dongle via PI"
            }
        }
        # Publish discovery message
        self.publish(discovery_topic, payload, retain=True)
        print(f"Initialized PID {name} with MQTT ID {mqtt_id} in Home Assistant")
        self.initialized_pids.add(mqtt_id)

    def update_pid_value(self, mqtt_id, value):
        """
        Update the value of a PID in Home Assistant.
        """
        state_topic = f"{self.topic_prefix}/{mqtt_id}/state"
        self.publish(state_topic, value)
        print(f"Updated PID with MQTT ID {mqtt_id} to value {value}")
