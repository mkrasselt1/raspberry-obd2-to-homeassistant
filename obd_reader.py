import time
import serial
import re




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
        response_ascii = response_bytes.decode(errors="ignore")
        if self.debug:
            print(f"[SERIAL RECV] {response_bytes.hex(' ')}")
            print(f"[SERIAL RECV DECODED] {response_ascii}")
        return response_ascii  # <-- ASCII-Text zurückgeben
    

    def parse_formula(self, equation, data_bytes):
        context = {}
        context_lower = {}
        offset = 0  # Standardmäßig kein Offset
        if len(data_bytes) > 3:
            # Prüfe, ob die ersten drei Bytes wie erwartet sind (optional)
            offset = 2  # oder offset = 3, wenn du immer ab dem 4. Byte starten willst
        for idx, byte in enumerate(data_bytes[offset:]):
            # Generate Excel-style column names (A, B, ..., Z, AA, AB, ...)
            def excel_col_name(n):
                name = ""
                while n >= 0:
                    name = chr(n % 26 + ord('A')) + name
                    n = n // 26 - 1
                return name

            var = excel_col_name(idx)
            context[var] = byte
            context_lower[var.lower()] = byte
        print(f"Context for equation '{equation}': {context}")  # <--- Hier wird das Dictionary ausgegeben
        context = {**context, **context_lower}
        try:
            equation = equation.replace('>', '>>').replace('<', '<<')
            def preprocess_expr(expr):
                # Int64(A,B,C,D) → (A << 24 | B << 16 | C << 8 | D) (big endian)
                def int64_fn_repl(match):
                    bytes_vars = [v.strip() for v in match.group(1).split(',')]
                    n = len(bytes_vars)
                    exprs = [f"({v} << {8 * (n - i - 1)})" for i, v in enumerate(bytes_vars)]
                    return "(" + " | ".join(exprs) + ")"
                expr = re.sub(r'Int64\s*\(\s*([^)]+)\s*\)', int64_fn_repl, expr)

                # Signed <expr> → signed_int(<expr>)
                def signed_repl(match):
                    # Wir wrappen den Ausdruck in signed_int()
                    inner = match.group(1)
                    return f"signed_int({inner})"
                expr = re.sub(r'Signed\s+([^\s:()]+(?:\([^)]+\))?)', signed_repl, expr)
                
                # <expr>:<n> → ((<expr> >> n) & 1)
                # Funktioniert für Variablen, Funktionsaufrufe und Klammerausdrücke
                expr = re.sub(r'([a-zA-Z_][\w() ,]*)\s*:\s*(\d+)', r'((\1 >> \2) & 1)', expr)
                return expr

            def signed_int(x, bits=64):
                """Interpretiert x als signed Integer mit angegebener Bitbreite (default: 64)."""
                mask = (1 << bits) - 1
                x = x & mask
                sign_bit = 1 << (bits - 1)
                return x - (1 << bits) if (x & sign_bit) else x

            def safe_eval(expr, context=None):
                expr_transformed = preprocess_expr(expr)
                return eval(expr_transformed, {"signed_int": signed_int}, context or {})
            
            return safe_eval(equation, context)
        except Exception as e:
            if self.debug:
                print(f"Error evaluating equation '{equation}' with bytes {data_bytes}: {e}")
            return None

    def parse_multiframe_response(self, response_ascii):
        """
        Zerlegt die Multi-Frame-Antwort (ASCII) in eine Liste von Nutzdaten-Bytes.
        """
        lines = response_ascii.split('\r')
        data_bytes = []
        first = True
        for line in lines:
            line = line.strip()
            if not line or not line[:3].isalnum():
                continue
            payload = line[3:]  # CAN-ID entfernen
            # Prompt-Zeichen oder sonstige Steuerzeichen entfernen
            payload = payload.replace('>', '').replace(' ', '')
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
            # PID nur einmal abfragen!
            pid_clean = pid.upper()
            if len(pid_clean) % 2 != 0:
                pid_clean = "0" + pid_clean
            command_str = ''.join([pid_clean[i:i+2] for i in range(0, len(pid_clean), 2)])
            # Optional: Header setzen, wenn einer der Messwerte einen Header definiert
            header = None
            for details in parameters.values():
                if details.get("header"):
                    header = details["header"]
                    break
            if header:
                self.send_serial_cmd(f"AT SH {header}")
            response_ascii = self.send_serial_cmd(command_str)
            data_bytes = self.parse_multiframe_response(response_ascii)
            print(f"Data bytes for PID {pid}: " + ", ".join([f"{i}:0x{b:02X}" for i, b in enumerate(data_bytes)]))
            # Jetzt für alle Messwerte auswerten
            for pid_id, details in parameters.items():
                value = None
                if "equation" in details and data_bytes:
                    value = self.parse_formula(details["equation"], data_bytes)
                if self.debug:
                    print(f"Published {details['name']}: {value} {details['unit']}")
                mqtt_handler.update_pid_value(details["pid_id"], value)

    def start_reading(self, pid_list, mqtt_handler, interval=1):
        try:
            while True:
                self.read_data(pid_list, mqtt_handler)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            self.disconnect()
