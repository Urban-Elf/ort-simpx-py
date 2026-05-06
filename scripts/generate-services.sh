#!/bin/bash

# THIS SCRIPT MUST BE RUN INSIDE THE 'scripts' FOLDER

# Ensure the script is run with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Get the absolute path of the 'scripts' folder
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Set Working Directory to one level up
WORKING_DIR=$(dirname "$SCRIPT_DIR")

SERVICE_A_PATH="$SCRIPT_DIR/start-server.sh"
SERVICE_B_PATH="$SCRIPT_DIR/start-ort.sh"

# Verify scripts exist
if [[ ! -f "$SERVICE_A_PATH" ]] || [[ ! -f "$SERVICE_B_PATH" ]]; then
    echo "Error: Could not find start-server.sh or start-ort.sh in $SCRIPT_DIR"
    exit 1
fi

# 1. Create Service A (The Base)
echo "Generating ort-server.service..."
cat <<EOF > /etc/systemd/system/ort-server.service
[Unit]
Description=Start Server (Service A)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$WORKING_DIR
ExecStart=/bin/bash $SERVICE_A_PATH
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# 2. Create Service B (The Dependent)
echo "Generating ort-client.service..."
cat <<EOF > /etc/systemd/system/ort-client.service
[Unit]
Description=Start ORT (Service B)
After=network-online.target ort-server.service
Wants=network-online.target
Requires=ort-server.service

[Service]
Type=simple
WorkingDirectory=$WORKING_DIR
ExecStart=/bin/bash $SERVICE_B_PATH
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# 3. Finalize
echo "Applying permissions and reloading systemd..."
chmod +x "$SERVICE_A_PATH"
chmod +x "$SERVICE_B_PATH"
systemctl daemon-reload

echo "------------------------------------------------"
echo "Success!"
echo "Working Directory set to: $WORKING_DIR"
echo "Scripts located in:      $SCRIPT_DIR"
echo "------------------------------------------------"
echo "To start: sudo systemctl start ort-client"