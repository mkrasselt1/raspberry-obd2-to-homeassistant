#!/bin/bash

# Set up variables
REPO_URL="https://github.com/mkrasselt1/raspberry-obd2-to-homeassistant.git"
INSTALL_DIR="/opt/raspberry-obd2-to-homeassistant"
SERVICE_NAME="obd2_to_homeassistant"
PYTHON_SCRIPT="main.py"  # Replace with the actual Python script name in the repo
VENV_DIR="$INSTALL_DIR/venv"

# Update system and install necessary packages
echo "Updating system and installing required packages..."
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

# Clone the repository
echo "Cloning repository..."
sudo git clone "$REPO_URL" "$INSTALL_DIR"

# Set up a Python virtual environment
echo "Setting up Python virtual environment..."
sudo python3 -m venv "$VENV_DIR"
sudo "$VENV_DIR/bin/pip" install --upgrade pip

# Install required Python dependencies
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    sudo "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
else
    echo "No requirements.txt found. Skipping dependency installation."
fi

# Create a systemd service file
echo "Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=OBD2 to Home Assistant Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/$PYTHON_SCRIPT
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd, enable and start the service
echo "Enabling and starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "Installation complete. The service should now be running."
