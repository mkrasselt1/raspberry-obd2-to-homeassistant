import obd
import time

class ObdReader:
    def __init__(self, mode, port=None, baudrate=None, tcp_url=None):
        self.mode = mode
        self.port = port
        self.baudrate = baudrate
        self.tcp_url = tcp_url
        self.connection = None

    def connect(self):
        print("Connecting to OBD2 dongle...")
        if self.mode == "uart":
            self.connection = obd.OBD(portstr=self.port, baudrate=self.baudrate)
        elif self.mode == "tcp":
            self.connection = obd.OBD(self.tcp_url)
        else:
            print(f"Invalid OBD mode: {self.mode}. Exiting...")
            exit(1)

        if not self.connection or not self.connection.is_connected():
            print("Failed to connect to OBD2 dongle. Exiting...")
            exit(1)

    def disconnect(self):
        if self.connection:
            self.connection.close()

    def read_data(self, pid_list, mqtt_handler):
        for mode, pids in pid_list.items():
            for pid, details in pids.items():
                try:
                    cmd = obd.commands[pid]  # Get OBD command by PID
                    response = self.connection.query(cmd)
                    if response.is_successful():
                        value = response.value.magnitude
                        topic = f"{mqtt_handler.topic_prefix}/{details['pid_id']}/state"
                        mqtt_handler.publish(topic, value)
                        print(f"Published {details['name']}: {value} {details['unit']} to {topic}")
                except Exception as e:
                    print(f"Failed to read PID {pid}: {e}")

    def start_reading(self, pid_list, mqtt_handler, interval=1):
        try:
            while True:
                self.read_data(pid_list, mqtt_handler)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            self.disconnect()
