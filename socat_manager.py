import subprocess
import time

class SocatManager:
    def __init__(self, tcp_url, serial_port="/dev/ttyOBD2"):
        self.tcp_url = tcp_url
        self.serial_port = serial_port
        self.process = None

    def start(self):
        if not self.tcp_url:
            raise ValueError("No TCP URL provided for socat.")
        cmd = [
            "sudo", "socat",
            f"pty,link={self.serial_port},raw",
            f"tcp:{self.tcp_url}"
        ]
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # Warten, bis das Device angelegt ist

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None