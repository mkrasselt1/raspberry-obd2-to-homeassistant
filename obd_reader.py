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
            self.connection = obd.OBD("/dev/ttyOBD2", baudrate=self.baudrate)
        else:
            print(f"Invalid OBD mode: {self.mode}. Exiting...")
            exit(1)

        if not self.connection or not self.connection.is_connected():
            print("Failed to connect to OBD2 dongle. Exiting...")
            exit(1)

    def disconnect(self):
        if self.connection:
            self.connection.close()

    def parse_formula(self, equation, data_bytes):
        context = {}
        for idx, byte in enumerate(data_bytes):
            var = chr(ord('A') + idx)
            context[var] = byte
        try:
            return eval(equation, {}, context)
        except Exception as e:
            print(f"Error evaluating equation '{equation}' with bytes {data_bytes}: {e}")
            return None

    def read_data(self, pid_list, mqtt_handler):
        for (mode, pid), parameters in pid_list.items():
            for pid_id, details in parameters.items():
                try:
                    # Standard-PIDs (meist Mode 01)
                    if pid in obd.commands and mode == "01":
                        cmd = obd.commands[pid]
                        response = self.connection.query(cmd, force=True)
                        success = response.is_successful()
                    else:
                        # Custom PID: baue Befehl aus Mode und PID
                        command_str = f"{mode} " + " ".join([pid[i:i+2] for i in range(0, len(pid), 2)])
                        response = self.connection.query(command_str)
                        success = hasattr(response, "messages") and response.messages

                    if success:
                        if hasattr(response, "messages") and response.messages:
                            raw_bytes = response.messages[0].data[2:]
                            data_bytes = [b for b in raw_bytes]
                        else:
                            data_bytes = []
                        value = None
                        if "equation" in details and data_bytes:
                            value = self.parse_formula(details["equation"], data_bytes)
                        else:
                            value = response.value.magnitude if hasattr(response, "value") and response.value else None
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
