from config import load_config
from pid_loader import load_pids_from_folder
from mqtt_handler import MqttHandler
from obd_reader import ObdReader

def send_autodiscovery(mqtt_handler, pid_list):
    """Send MQTT autodiscovery config for Home Assistant."""
    for mode, pids in pid_list.items():
        for pid, details in pids.items():
            config_topic = f"{mqtt_handler.topic_prefix}/{details['mqtt_id']}/config"
            config_payload = {
                "name": details["name"],
                "state_topic": f"{mqtt_handler.topic_prefix}/{details['mqtt_id']}/state",
                "unit_of_measurement": details["unit"],
                "unique_id": f"obd2_{details['mqtt_id']}",
                "device": {
                    "identifiers": ["obd2_device"],
                    "name": "OBD2 Dongle",
                    "manufacturer": "Generic",
                    "model": "OBD2 Bluetooth Dongle"
                }
            }
            mqtt_handler.publish(config_topic, config_payload, retain=True)

def main():
    # Load configuration
    config = load_config()

    # Initialize MQTT handler
    mqtt_handler = MqttHandler(
        broker=config["mqtt"]["broker"],
        port=config["mqtt"]["port"],
        username=config["mqtt"]["user"],
        password=config["mqtt"]["password"],
        topic_prefix=config["mqtt"]["topic_prefix"]
    )
    mqtt_handler.start_loop()

    # Load PIDs
    pid_list = load_pids_from_folder("pids")

    # Initialize OBD Reader
    obd_reader = ObdReader(
        mode=config["obd"]["mode"],
        port=config["obd"].get("port"),
        baudrate=config["obd"].get("baudrate"),
        tcp_url=config["obd"].get("tcp_url")
    )
    obd_reader.connect()

    # Send MQTT Autodiscovery
    send_autodiscovery(mqtt_handler, pid_list)

    # Start reading and publishing data
    obd_reader.start_reading(pid_list, mqtt_handler)

if __name__ == "__main__":
    main()
