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
        self.send_serial_cmd("AT D")      # Set all settings to default
        self.send_serial_cmd("AT Z")      # Reset ELM327
        self.send_serial_cmd("AT E0")     # Echo off (Antworten enthalten nicht den gesendeten Befehl)
        self.send_serial_cmd("AT L0")     # Linefeeds off (keine Zeilenumbrüche in Antworten)
        self.send_serial_cmd("AT S0")     # Spaces off (keine Leerzeichen in Antworten)
        ##self.send_serial_cmd("AT H0")     # Headers off (nur Daten, keine CAN-IDs in Antwort)
        self.send_serial_cmd("AT H1")     # Headers on (include CAN IDs in responses)
        self.send_serial_cmd("AT D0")     # Display of DLC off (keine Anzeige der Datenlänge)
        self.send_serial_cmd("AT CAF1")   # Automatic formatting on (Antworten werden automatisch formatiert)
        #self.send_serial_cmd("AT SP 0")   # Set protocol to automatic
        self.send_serial_cmd("AT SP 6")   # Setze Protokoll auf ISO 15765-4 CAN (meist für neuere Fahrzeuge)
        self.send_serial_cmd("AT ST 96")  # Set timeout to 150ms (hex 96 = 150 decimal)
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
        return response_bytes

    def parse_formula(self, equation, data_bytes):
        context = {}
        for idx, byte in enumerate(data_bytes):
            # Generate Excel-style column names (A, B, ..., Z, AA, AB, ...)
            def excel_col_name(n):
                name = ""
                while n >= 0:
                    name = chr(n % 26 + ord('A')) + name
                    n = n // 26 - 1
                return name

            var = excel_col_name(idx)
            context[var] = byte
            context[var.lower()] = byte
        try:
            return eval(equation, {}, context)
        except Exception as e:
            if self.debug:
                print(f"Error evaluating equation '{equation}' with bytes {data_bytes}: {e}")
            return None

    def parse_multiframe_response(self, response_bytes):
        """
        Zerlegt die Multi-Frame-Antwort in eine Liste von Nutzdaten-Bytes.
        """
        lines = response_bytes.decode(errors="ignore").split('\r')
        data_bytes = []
        first = True
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if len(line) > 3 and line[:3].isalnum():
                payload = line[3:]
                # In 2er-Schritten in Bytes umwandeln
                bytes_list = [int(payload[i:i+2], 16) for i in range(0, len(payload), 2) if len(payload[i:i+2]) == 2]
                if first:
                    # Überspringe die ersten 3 Bytes (Länge, Service, PID)
                    data_bytes.extend(bytes_list[3:])
                    first = False
                else:
                    data_bytes.extend(bytes_list)
        return data_bytes

    def read_data(self, pid_list, mqtt_handler):
        for pid, parameters in pid_list.items():
            for pid_id, details in parameters.items():
                try:
                    pid_clean = pid.upper()
                    if len(pid_clean) % 2 != 0:
                        pid_clean = "0" + pid_clean
                    command_str = ''.join([pid_clean[i:i+2] for i in range(0, len(pid_clean), 2)])
                    if details.get("header"):
                        self.send_serial_cmd(f"AT SH {details['header']}")
                    response_bytes = self.send_serial_cmd(command_str)
                    if self.debug:
                        print(f"PID {pid_id} ({command_str}) PARSED: {response_bytes}")
                    value = None
                    if "equation" in details and response_bytes:
                        # Multi-Frame-Parsing
                        data_bytes = self.parse_multiframe_response(response_bytes)
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
