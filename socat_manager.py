import subprocess
import time
import re

class SocatManager:
    def __init__(self, tcp_url, serial_port="/dev/ttyOBD2", baudrate=9600):
        self.tcp_url = tcp_url  # z.B. "YOUR_OBD_TCP_HOST:PORT"
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.process = None

    def _validate_serial_port(self, port):
        # Nur absolute Pfadangaben erlauben, keine Sonderzeichen
        if not re.fullmatch(r"/[a-zA-Z0-9/_\-]+", port):
            raise ValueError(f"Ungültiger serial_port: {port}")

    def _validate_baudrate(self, baudrate):
        if not isinstance(baudrate, int) or baudrate <= 0:
            raise ValueError(f"Ungültige baudrate: {baudrate}")

    def _validate_tcp_url(self, url):
        # DNS/IP:Port, z.B. 192.0.2.1:3333 oder myhost.local:3333
        if not re.fullmatch(r"([a-zA-Z0-9\.\-]+|\d{1,3}(\.\d{1,3}){3}):\d{1,5}", url):
            raise ValueError(f"Ungültige tcp_url: {url}")

    def start(self):
        self._validate_serial_port(self.serial_port)
        self._validate_baudrate(self.baudrate)
        self._validate_tcp_url(self.tcp_url)

        cmd = [
            "nohup", "socat",
            f"PTY,link={self.serial_port},b{self.baudrate},raw,echo=0",
            f"TCP:{self.tcp_url}"
        ]
        self.process = subprocess.Popen(
            " ".join(cmd),
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)  # Warten, bis das Device angelegt ist

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None