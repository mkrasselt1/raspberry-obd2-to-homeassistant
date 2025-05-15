import paho.mqtt.client as mqtt
import json

class MqttHandler:
    def __init__(self, broker, port, username, password, topic_prefix):
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.connect(broker, port, 60)
        self.topic_prefix = topic_prefix

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
