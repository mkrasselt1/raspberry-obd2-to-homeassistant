from mqtt_handler import MqttHandler
from obd_reader import ObdReader
import time
from pid_loader import load_pids_from_folder
from config import load_config

def main():
    config = load_config("config.json")
    socat_manager = None
    
    # Starte socat nur bei TCP-Modus
    if config["obd"]["mode"] == "tcp":
        from socat_manager import SocatManager
        socat_manager = SocatManager(
            tcp_url=config["obd"]["tcp_url"],
            serial_port="/dev/ttyOBD2"
        )
        socat_manager.start()

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
                pid_id=details["pid_id"]
            )

    # Continuously read and update PID values
    try:
        while True:
            for mode, pid_group in pids.items():
                for pid, details in pid_group.items():
                    value = obd_reader.read_pid(mode, pid)
                    if value is not None:
                        mqtt_handler.update_pid_value(details["pid_id"], value)
            time.sleep(1)  # Adjust the polling interval as needed
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        mqtt_handler.stop_loop()
        if socat_manager:
            socat_manager.stop()

if __name__ == "__main__":
    main()
