import subprocess
import time
import os
import signal

# Start the script using subprocess.Popen
process = subprocess.Popen(["python", "test3.py"])

# Get the PID of the process
pid = process.pid
print(f"Started main.py with PID {pid}")

# Wait for 5 seconds (or your desired duration)
time.sleep(5)

# Kill the process
os.kill(pid, signal.SIGTERM)  # Send the TERM signal to terminate the process
print(f"Killed process with PID {pid}")
