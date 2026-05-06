#!/bin/bash

# RUN THIS SCRIPT FROM THE ROOT OF THE REPO
# $ ./scripts/start-ort.sh

# check if venv exists
if [ ! -d "./ort/venv" ]; then
    echo "Virtual environment not found. Creating one..."
    sudo apt update && sudo apt install -y python3-venv
    python3 -m venv ./ort/venv
    source ./ort/venv/bin/activate
    pip install -r ./ort/requirements.txt
else
    source ./ort/venv/bin/activate
fi

# run the server
./ort/venv/bin/python ./bot_ort.py