import os
import time
import subprocess
from psutil import process_iter, Process
from signal import SIGTERM


def cleanup_screenshots(screenshots):
    """Clean up the screenshots directory."""
    if os.path.exists(screenshots):
        for filename in os.listdir(screenshots):
            file_path = os.path.join(screenshots, filename)
            os.remove(file_path)
    else:
        os.makedirs(screenshots)

def quit_specific_browser(subprocess_pid):
    """
    Terminate only the Chrome browser processes spawned by the specific Chromedriver subprocess.
    """
    try:
        # Get the Process object for the subprocess
        parent_process = Process(subprocess_pid)
        # Iterate through child processes of the subprocess
        for child in parent_process.children(recursive=True):
            if "chrome" in child.name().lower():
                try:
                    os.kill(child.pid, SIGTERM)  # Send terminate signal to the Chrome process
                    print(f"Terminated Chrome process (PID: {child.pid})")
                except Exception as e:
                    print(f"Failed to terminate Chrome process (PID: {child.pid}): {e}")
    except Exception as e:
        print(f"Failed to find child processes for subprocess PID {subprocess_pid}: {e}")

while True:
    # Step 1: Clean up screenshots directory
    cleanup_screenshots("screenshots_api")
    cleanup_screenshots("screenshots_api_1")
    cleanup_screenshots("screenshots_api_2")

    # Step 2: Launch the script as a subprocess
    print("Starting the script...")
    process = subprocess.Popen(["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"])  # Launch the script
    print(f"Script started with PID of process: {process.pid}")

    process_1 = subprocess.Popen(["uvicorn", "app_1:app", "--host", "0.0.0.0", "--port", "8080"]) 
    print(f"Script started with PID of process 1: {process_1.pid}")

    # Step 3: Run the subprocess for a specific duration (e.g., 1 hour)
    time.sleep(500000)  # Keep the subprocess running for 1 hour

    # Step 4: Terminate the subprocess
    print("Terminating the script...")
    quit_specific_browser(process.pid)
    process.terminate()
    process.wait()  # Ensure the process has terminated

    quit_specific_browser(process_1.pid)
    process_1.terminate()
    process_1.wait()  # Ensure the process has terminated
    time.sleep(3)

    # Step 5: Quit only Chrome processes associated with this subprocess
    

    print("Restarting the script...")
