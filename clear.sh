#!/bin/bash

# Find and kill process using port 5002
echo "Looking for process using port 5002..."

# For macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Get the process ID
    PID=$(lsof -i:5002 -t)
    
    if [ -z "$PID" ]; then
        echo "No process found using port 5002."
    else
        echo "Found process with PID $PID. Killing process..."
        kill -9 $PID
        echo "Process killed successfully."
    fi
# For Linux/Unix
else
    # Get the process ID
    PID=$(netstat -tulpn 2>/dev/null | grep ":5002 " | awk '{print $7}' | cut -d'/' -f1)
    
    if [ -z "$PID" ]; then
        echo "No process found using port 5002."
    else
        echo "Found process with PID $PID. Killing process..."
        kill -9 $PID
        echo "Process killed successfully."
    fi
fi
# Check if port is now available
sleep 1
if lsof -i:5002 >/dev/null 2>&1; then
    echo "Warning: Port 5002 is still in use. You may need to manually terminate the process."
else
    echo "Port 5002 is now available."
fi