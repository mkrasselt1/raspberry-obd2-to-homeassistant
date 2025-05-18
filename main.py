from mqtt_handler import MqttHandler
from gpspoller import GpsPoller
import ioniq_bev
import elm327
import time
from config import load_config

def main():
    # Load configuration
    config = load_config("config.json")
    socat_manager = None

    # Starte socat nur bei TCP-Modus
    if config["obd"]["mode"] == "tcp":
        from socat_manager import SocatManager
        socat_manager = SocatManager(
            tcp_url=config["obd"]["tcp_url"],
            serial_port=config["obd"].get("port", "/dev/ttyOBD2"),
            baudrate=config["obd"].get("baudrate", 9600)
        )
        socat_manager.start()

    # Initialize MQTT Handler
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

    Threads = []

    # Init dongle
    dongle_instance = elm327.Elm327(config['obd'])

    # Init GPS interface
    gps = GpsPoller()
    Threads.append(gps)

    # Init car
    car_instance = ioniq_bev.IoniqBev(config, dongle_instance, gps)
    Threads.append(car_instance)

    # Start polling loops
    for t in Threads:
        t.start()

    try:
        while True:
            now = time.time()
            for t in Threads:
                status = t.check_thread()
                if not status:
                    raise Exception(f"Thread {t} failed.")

            # Publish car data to MQTT
            car_data = {}
            car_instance.read_dongle(car_data)
            for key, value in car_data.items():
                mqtt_handler.update_pid_value(key, value)

            # Ensure messages get printed to the console.
            time.sleep(1)

    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        for t in Threads[::-1]:  # reverse Threads
            t.stop()
        mqtt_handler.stop_loop()

if __name__ == "__main__":
    main()
