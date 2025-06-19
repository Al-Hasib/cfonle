import os
import time
import subprocess
import signal
import psutil

def kill_existing_processes():
    """Kill any existing Python processes running the bot"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' and 'maain.py' in ' '.join(proc.info['cmdline']):
                proc.kill()
                print(f"Killed existing process: {proc.info['pid']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def main():
    while True:
        # Kill any existing processes first
        # kill_existing_processes()
        time.sleep(5)  # Wait for processes to fully terminate
        
        # Clean up screenshots
        if os.path.exists("screenshots"):
            for filename in os.listdir("screenshots"):
                file_path = os.path.join("screenshots", filename)
                os.remove(file_path)
        else:
            os.makedirs("screenshots")
        
        print("Starting the script...")
        process = subprocess.Popen(["python", "maain.py"])
        print(f"Script started with PID {process.pid}")
        
        # Run for 1 hour
        time.sleep(3600)
        
        print("Terminating the script...")
        process.terminate()
        process.wait()
        
        time.sleep(3)
        print("Restarting the script...")

if __name__ == "__main__":
    main()
