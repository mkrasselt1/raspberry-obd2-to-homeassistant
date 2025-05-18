import obd
import time
import serial

class ObdReader:
    def __init__(self, port=None, baudrate=None, debug=False):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.debug = debug

    def connect(self):
        print("Connecting to OBD2 dongle...")
        self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
        time.sleep(1)
        # --- ELM327 Initialisierung ---
        self.send_serial_cmd("AT Z")      # Reset ELM327
        self.send_serial_cmd("AT E0")     # Echo off (Antworten enthalten nicht den gesendeten Befehl)
        self.send_serial_cmd("AT L0")     # Linefeeds off (keine Zeilenumbrüche in Antworten)
        self.send_serial_cmd("AT S0")     # Spaces off (keine Leerzeichen in Antworten)
        self.send_serial_cmd("AT H0")     # Headers off (nur Daten, keine CAN-IDs in Antwort)
        self.send_serial_cmd("AT D0")     # Display of DLC off (keine Anzeige der Datenlänge)
        self.send_serial_cmd("AT CAF1")   # Automatic formatting on (Antworten werden automatisch formatiert)
        self.send_serial_cmd("AT SP 6")   # Setze Protokoll auf ISO 15765-4 CAN (meist für neuere Fahrzeuge)
        self.send_serial_cmd("AT ST 96")  # Setze Timeout auf 150ms (Standardwert)
        # Optional: self.send_serial_cmd("AT SH ...") für Custom Header, wird aber pro PID gesetzt

        
        

    def disconnect(self):
        if self.ser:
            self.ser.close()

    def send_serial_cmd(self, cmd):
        if self.debug:
            print(f"[SERIAL SEND] {cmd}")
        self.ser.write((cmd + "\r").encode())
        time.sleep(0.2)
        response_bytes = self.ser.read_all()
        if self.debug:
            print(f"[SERIAL RECV] {response_bytes.hex(' ')}")
            try:
                print(f"[SERIAL RECV DECODED] {response_bytes.decode(errors='ignore')}")
            except Exception as e:
                print(f"[SERIAL RECV DECODED] <decode error: {e}>")
        response = response_bytes.decode(errors="ignore")
        return response

    def parse_formula(self, equation, data_bytes):
        context = {}
        for idx, byte in enumerate(data_bytes):
            var = chr(ord('A') + idx)
            context[var] = byte
        try:
            return eval(equation, {}, context)
        except Exception as e:
            if self.debug:
                print(f"Error evaluating equation '{equation}' with bytes {data_bytes}: {e}")
            return None

    def read_data(self, pid_list, mqtt_handler):
        for (mode, pid), parameters in pid_list.items():
            for pid_id, details in parameters.items():
                try:
                    # Stelle sicher, dass PID eine gerade Länge hat (ggf. mit führender Null auffüllen)
                    pid_clean = pid.upper()
                    if len(pid_clean) % 2 != 0:
                        pid_clean = "0" + pid_clean
                    command_str = f"{mode.upper()} " + " ".join([pid_clean[i:i+2] for i in range(0, len(pid_clean), 2)])
                    if details.get("header"):
                        self.send_serial_cmd(f"AT SH {details['header']}")
                    if details.get("binary_mode"):
                        if self.debug:
                            print(f"Binary mode for PID {pid} aktiv!")
                    response = self.send_serial_cmd(command_str)
                    # Rohdaten extrahieren (Antwort parsen)
                    lines = [l.strip() for l in response.splitlines() if l.strip()]
                    data_bytes = []
                    for line in lines:
                        if line.startswith(mode):
                            hexbytes = line[len(mode):].strip().split()
                            data_bytes = [int(b, 16) for b in hexbytes if len(b) == 2]
                            break
                    # Debug: Dump raw CAN data as hex
                    if self.debug:
                        print(f"PID {pid_id} ({command_str}) RAW CAN: {response.encode(errors='ignore').hex(' ')}")
                        print(f"PID {pid_id} ({command_str}) PARSED: {data_bytes}")
                    value = None
                    if "equation" in details and data_bytes:
                        value = self.parse_formula(details["equation"], data_bytes)
                    else:
                        value = None
                    # MQTT nur wenn debug nicht aktiv
                    if not self.debug:
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
