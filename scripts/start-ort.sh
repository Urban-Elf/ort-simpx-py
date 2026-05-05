#!/bin/bash

# check if venv exists
if [ ! -d "./ort/venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv ./ort/venv
    source ./ort/venv/bin/activate
    pip install -r ./ort/requirements.txt
else
    source ./ort/venv/bin/activate
fi

# run the server
./ort/venv/bin/python ./bot_ort.py