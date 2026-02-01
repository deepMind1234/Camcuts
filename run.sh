#!/bin/bash

# Ensure we are in the project directory
cd "$(dirname "$0")"

# Path to the virtual environment python
VENV_PYTHON="./.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment not found at ./.venv"
    echo "Please create it first: python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Try to give local user access to X server (fixes Xlib Authorization error)
xhost +local:$(whoami) > /dev/null 2>&1

echo "Starting Camcuts..."
# Run the application using the venv's python
# We pass XAUTHORITY and DISPLAY to ensure GUI connectivity
XAUTHORITY=$XAUTHORITY DISPLAY=$DISPLAY "$VENV_PYTHON" main.py
