from mqtt_handler import MqttHandler
from gpspoller import GpsPoller
import ioniq_bev
import elm327
import time
from config import load_config

def initialize_homeassistant_sensors(mqtt_handler, car_instance):
    """ Initialize Home Assistant sensors based on the car's fields. """
    print("[INFO] Initializing Home Assistant sensors...")
    base_topic = mqtt_handler.topic_prefix

    # Extract fields from the car instance
    pids = car_instance.get_fields()
    for fields in pids:
        for field in fields:
            if 'name' not in field:
                continue  # Skip fields without a name

            sensor_name = field['name']
            unit = field.get('units', None)
            scale = field.get('scale', None)
            device_class = None  # Optional: Define device class if needed

            # Publish sensor configuration to Home Assistant
            mqtt_handler.initialize_pid(
                pid=sensor_name,
                name=sensor_name.replace("_", " ").capitalize(),
                unit=unit,
                pid_id=sensor_name
            )
            print(f"[INFO] Sensor '{sensor_name}' initialized.")

def main():
    print("[INFO] Starting application...")

    # Load configuration
    print("[INFO] Loading configuration...")
    config = load_config("config.json")
    print("[INFO] Configuration loaded successfully.")
    socat_manager = None

    # Starte socat nur bei TCP-Modus
    if config["obd"]["mode"] == "tcp":
        print("[INFO] Starting socat for TCP mode...")
        from socat_manager import SocatManager
        socat_manager = SocatManager(
            tcp_url=config["obd"]["tcp_url"],
            serial_port=config["obd"].get("port", "/dev/ttyOBD2"),
            baudrate=config["obd"].get("baudrate", 9600)
        )
        socat_manager.start()
        print("[INFO] Socat started successfully.")

    # Initialize MQTT Handler
    print("[INFO] Initializing MQTT handler...")
    mqtt_handler = MqttHandler(
        broker=config["mqtt"]["broker"],
        port=config["mqtt"]["port"],
        username=config["mqtt"]["user"],
        password=config["mqtt"]["password"],
        topic_prefix=config["mqtt"]["topic_prefix"],
        device_name=config["obd"].get("device_name", "OBD2 Dongle"),
        log_enabled=not config.get("debug", False)  # Logging nur wenn debug False!
    )
    mqtt_handler.start_loop()
    print("[INFO] MQTT handler initialized and loop started.")

    Threads = []

    # Init dongle
    print("[INFO] Initializing ELM327 dongle...")
    dongle_instance = elm327.Elm327(config['obd'])
    print("[INFO] Dongle initialized successfully.")

    # Init GPS interface
    print("[INFO] Initializing GPS interface...")
    gps = GpsPoller()
    Threads.append(gps)
    print("[INFO] GPS interface initialized successfully.")

    # Init car
    print("[INFO] Initializing car interface...")
    car_instance = ioniq_bev.IoniqBev(config, dongle_instance, gps)
    Threads.append(car_instance)
    print("[INFO] Car interface initialized successfully.")

    # Initialize Home Assistant sensors
    initialize_homeassistant_sensors(mqtt_handler, car_instance)

    # Start polling loops
    print("[INFO] Starting polling threads...")
    for t in Threads:
        t.start()
    print("[INFO] Polling threads started successfully.")

    try:
        while True:
            now = time.time()
            for t in Threads:
                status = t.check_thread()
                if not status:
                    print(f"[ERROR] Thread {t} failed. Restarting...")
                    t.start()

            # Publish car data to MQTT
            car_data = {}
            car_instance.read_dongle(car_data)
            print(f"[DEBUG] Car data read: {car_data}")
            for key, value in car_data.items():
                mqtt_handler.update_pid_value(key, value)
                print(f"[DEBUG] Published {key}: {value} to MQTT.")

            # Ensure messages get printed to the console.
            time.sleep(1)

    except KeyboardInterrupt:
        print("[INFO] Shutting down...")
    finally:
        print("[INFO] Stopping threads...")
        for t in Threads[::-1]:  # reverse Threads
            t.stop()
        print("[INFO] Threads stopped.")
        mqtt_handler.stop_loop()
        print("[INFO] MQTT loop stopped.")

if __name__ == "__main__":
    main()
