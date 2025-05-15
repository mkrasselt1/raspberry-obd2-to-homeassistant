from mqtt_handler import MqttHandler
from obd_reader import ObdReader
import time

def main():
    # Load configuration (assuming a load_config function exists)
    config = load_config("config.json")

    # Initialize MQTT Handler
    mqtt_handler = MqttHandler(
        broker=config["mqtt"]["broker"],
        port=config["mqtt"]["port"],
        username=config["mqtt"]["user"],
        password=config["mqtt"]["password"],
        topic_prefix=config["mqtt"]["topic_prefix"]
    )
    mqtt_handler.start_loop()

    # Initialize OBD Reader
    obd_reader = ObdReader(
        mode=config["obd"]["mode"],
        port=config["obd"].get("port"),
        baudrate=config["obd"].get("baudrate"),
        tcp_url=config["obd"].get("tcp_url")
    )
    obd_reader.connect()

    # Load PIDs from folder
    pids = load_pids_from_folder("pids")

    # Initialize PIDs in Home Assistant
    for mode, pid_group in pids.items():
        for pid, details in pid_group.items():
            mqtt_handler.initialize_pid(
                pid=pid,
                name=details["name"],
                unit=details["unit"],
                mqtt_id=details["mqtt_id"]
            )

    # Continuously read and update PID values
    try:
        while True:
            for mode, pid_group in pids.items():
                for pid, details in pid_group.items():
                    value = obd_reader.read_pid(mode, pid)
                    if value is not None:
                        mqtt_handler.update_pid_value(details["mqtt_id"], value)
            time.sleep(1)  # Adjust the polling interval as needed
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        mqtt_handler.stop_loop()

if __name__ == "__main__":
    main()
