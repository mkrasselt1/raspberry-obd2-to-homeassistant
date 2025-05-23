# Raspberry OBD2 to Home Assistant

A project designed to integrate car data from an OBD2 dongle with [Home Assistant](https://www.home-assistant.io/) using MQTT and Torque Pro PID lists. This tool enables real-time vehicle data to be sent to Home Assistant via MQTT autodiscovery.

## Features

- Connects to an OBD2 Bluetooth dongle.
- Uses Torque Pro PID lists to determine which data to read from the vehicle.
- Sends OBD2 data to an MQTT broker.
- MQTT autodiscovery for seamless integration with Home Assistant.
- Designed for Raspberry Pi or any Linux-based system.

---

## Requirements

- A Raspberry Pi or Linux-based system.
- Python 3.7 or later installed.
- An OBD2 Bluetooth dongle.
- MQTT broker (e.g., Mosquitto).
- Home Assistant instance.
- Torque Pro PID list for the car you want to monitor.

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/mkrasselt1/raspberry-obd2-to-homeassistant.git
cd raspberry-obd2-to-homeassistant
```

### Step 2: Run the Installer Script

Run the provided install script to set up the project and create a systemd service for running the Python script.
bash

```bash
chmod +x install.sh
sudo ./install.sh
```

The script will:

    1. Clone the repository into /opt/raspberry-obd2-to-homeassistant.
    2. Set up a Python virtual environment and install required dependencies.
    3. Create and enable a systemd service to run the script.

## Configuration
### MQTT Broker Settings

Update the main.py file with the correct MQTT broker details:
Python

```bash
MQTT_BROKER = "mqtt_broker_address"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_USER = "mqtt_user"  # Replace with your MQTT username
MQTT_PASSWORD = "mqtt_password"  # Replace with your MQTT password
```

## OBD2 Dongle Settings

Specify the correct OBD2 dongle port in the main.py file:
Python

OBD_PORT = "/dev/ttyUSB0"  # Replace with your OBD2 dongle's port

Torque Pro PID List

Put the into the pid folder that you want to monitor. Example:

https://raw.githubusercontent.com/JejuSoul/OBD-PIDs-for-HKMC-EVs/refs/heads/master/Ioniq%20EV%20-%2028kWh/extendedpids/Hyundai_Ioniq_EV_BMS_data.csv

##Usage
Starting the Service

The service will start automatically after installation. You can manually start or stop it using:

```bash
sudo systemctl start obv2_to_homeassistant
sudo systemctl stop obd2_to_homeassistant
```

### Checking Service Logs

View logs to debug or monitor the service:

```bash
sudo journalctl -u obd2_to_homeassistant
```

##Testing the Script

To test the script without running it as a service:

```bash
python3 main.py
```

# Home Assistant Integration

Once the script is running, Home Assistant will automatically discover the sensors via MQTT autodiscovery. You can find the sensors in the Home Assistant UI under Settings > Devices & Services.
Contributing

Contributions are welcome! If you have suggestions, bug reports, or feature requests, feel free to open an issue or submit a pull request.

# License

This project is licensed under the MIT License. See the LICENSE file for details.

# Troubleshooting
## Common Issues

    OBD2 dongle not connecting
    Ensure the correct port is set in the OBD_PORT variable of main.py. Use ls /dev/ to find the correct serial port.

    MQTT connection issues
    Verify your MQTT broker is running and accessible. Check the broker address, username, and password.

    Home Assistant not discovering sensors
    Ensure MQTT autodiscovery is enabled in Home Assistant and the script is publishing data to the correct topic.

    Python dependency issues
    Run the following to reinstall dependencies:
    bash

    source /opt/raspberry-obd2-to-homeassistant/venv/bin/activate
    pip install -r requirements.txt

## Acknowledgments

    Home Assistant for its amazing home automation platform.
    Torque Pro for their extensive PID list.
