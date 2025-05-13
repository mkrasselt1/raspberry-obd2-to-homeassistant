import obd
import paho.mqtt.client as mqtt
import json
import time

# MQTT Configuration
MQTT_BROKER = "mqtt_broker_address"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_USER = "mqtt_user"  # Replace with your MQTT username
MQTT_PASSWORD = "mqtt_password"  # Replace with your MQTT password
MQTT_TOPIC_PREFIX = "homeassistant/sensor/obd2"  # Prefix for Home Assistant MQTT autodiscovery

# OBD Configuration
OBD_PORT = "/dev/ttyUSB0"  # Replace with your OBD2 dongle's port
OBD_BAUDRATE = 9600

# Torque Pro PID List (Example PIDs)
PID_LIST = {
    "01": {  # Mode 01
        "0C": {  # RPM
            "name": "Engine RPM",
            "unit": "rpm",
            "mqtt_id": "engine_rpm"
        },
        "0D": {  # Speed
            "name": "Vehicle Speed",
            "unit": "km/h",
            "mqtt_id": "vehicle_speed"
        }
    }
}

# MQTT Client Setup
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

mqtt_client.on_connect = on_connect
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

def send_autodiscovery():
    """Send MQTT autodiscovery config for Home Assistant."""
    for mode, pids in PID_LIST.items():
        for pid, details in pids.items():
            config_topic = f"{MQTT_TOPIC_PREFIX}/{details['mqtt_id']}/config"
            config_payload = {
                "name": details["name"],
                "state_topic": f"{MQTT_TOPIC_PREFIX}/{details['mqtt_id']}/state",
                "unit_of_measurement": details["unit"],
                "unique_id": f"obd2_{details['mqtt_id']}",
                "device": {
                    "identifiers": ["obd2_device"],
                    "name": "OBD2 Dongle",
                    "manufacturer": "Generic",
                    "model": "OBD2 Bluetooth Dongle"
                }
            }
            mqtt_client.publish(config_topic, json.dumps(config_payload), retain=True)

def read_obd_data(connection):
    """Read data from OBD2 and publish to MQTT."""
    for mode, pids in PID_LIST.items():
        for pid, details in pids.items():
            try:
                cmd = obd.commands[pid]  # Get OBD command by PID
                response = connection.query(cmd)
                if response.is_successful():
                    value = response.value.magnitude
                    topic = f"{MQTT_TOPIC_PREFIX}/{details['mqtt_id']}/state"
                    mqtt_client.publish(topic, value)
                    print(f"Published {details['name']}: {value} {details['unit']} to {topic}")
            except Exception as e:
                print(f"Failed to read PID {pid}: {e}")

def main():
    # Connect to OBD2
    print("Connecting to OBD2 dongle...")
    connection = obd.OBD(portstr=OBD_PORT)
    
    if not connection.is_connected():
        print("Failed to connect to OBD2 dongle. Exiting...")
        return

    # Send MQTT autodiscovery config
    print("Sending MQTT autodiscovery messages...")
    send_autodiscovery()
    
    # Main loop
    print("Starting data collection...")
    try:
        while True:
            read_obd_data(connection)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        connection.close()

if __name__ == "__main__":
    main()
