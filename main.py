import obd
import paho.mqtt.client as mqtt
import json
import csv
import os
import time

# Load configuration from external file
CONFIG_FILE = "config.json"
try:
    with open(CONFIG_FILE, "r") as file:
        config = json.load(file)
except FileNotFoundError:
    print(f"Configuration file '{CONFIG_FILE}' not found. Exiting...")
    exit(1)

# MQTT Configuration
MQTT_BROKER = config["mqtt"]["broker"]
MQTT_PORT = config["mqtt"]["port"]
MQTT_USER = config["mqtt"]["user"]
MQTT_PASSWORD = config["mqtt"]["password"]
MQTT_TOPIC_PREFIX = config["mqtt"]["topic_prefix"]

# OBD Configuration
OBD_MODE = config["obd"]["mode"]  # "uart" or "tcp"
OBD_PORT = config["obd"].get("port", "/dev/ttyUSB0")  # Default for UART
OBD_BAUDRATE = config["obd"].get("baudrate", 9600)  # Default for UART
OBD_TCP_URL = config["obd"].get("tcp_url")  # For TCP mode
PIDS_FOLDER = "pids"  # Folder where PID CSV files are stored

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

def load_pids_from_folder(folder_path):
    """Load PID definitions from all CSV files in a folder."""
    pid_list = {}
    try:
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".csv"):
                file_path = os.path.join(folder_path, file_name)
                print(f"Loading PIDs from {file_path}...")
                with open(file_path, mode="r") as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    for row in csv_reader:
                        mode = row["Mode"]
                        pid = row["PID"]
                        name = row["Name"]
                        unit = row["Unit"]
                        mqtt_id = row["MQTT_ID"]
                        
                        if mode not in pid_list:
                            pid_list[mode] = {}
                        pid_list[mode][pid] = {
                            "name": name,
                            "unit": unit,
                            "mqtt_id": mqtt_id
                        }
    except Exception as e:
        print(f"Failed to load PIDs: {e}")
        exit(1)
    return pid_list

PID_LIST = load_pids_from_folder(PIDS_FOLDER)

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
    
    connection = None
    if OBD_MODE == "uart":
        connection = obd.OBD(portstr=OBD_PORT, baudrate=OBD_BAUDRATE)
    elif OBD_MODE == "tcp":
        connection = obd.OBD(OBD_TCP_URL)
    else:
        print(f"Invalid OBD mode: {OBD_MODE}. Exiting...")
        return
    
    if not connection or not connection.is_connected():
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
