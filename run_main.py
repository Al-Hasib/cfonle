import os
import time
import subprocess
import signal
import psutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def kill_existing_processes():
    """Kill only main.py processes, not this script"""
    logger.info("Looking for main.py processes to kill...")
    try:
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe' and 'main.py' in ' '.join(proc.info['cmdline']):
                    proc.kill()
                    logger.info(f"Killed main.py process: {proc.info['pid']}")
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if killed_count > 0:
            logger.info(f"Killed {killed_count} main.py processes")
            time.sleep(3)  # Reduced wait time
        else:
            logger.info("No existing main.py processes found")
        
        return killed_count
    except Exception as e:
        logger.error(f"Error killing processes: {e}")
        return 0

def cleanup_temp_files():
    """Clean up temporary Chrome profile directories"""
    logger.info("Cleaning up temporary files...")
    try:
        # Kill Chrome processes first
        os.system("taskkill /f /im chrome.exe /t >nul 2>&1")
        os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
        time.sleep(1)  # Reduced wait time
        
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        cleaned_count = 0
        # Clean up chrome profile temp directories
        for item in os.listdir(temp_dir):
            if item.startswith('chrome_profile_'):
                temp_path = os.path.join(temp_dir, item)
                try:
                    import shutil
                    shutil.rmtree(temp_path)
                    cleaned_count += 1
                    logger.debug(f"Cleaned temp directory: {temp_path}")
                except Exception as e:
                    logger.warning(f"Could not clean temp directory {temp_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned {cleaned_count} temporary Chrome profiles")
        else:
            logger.info("No temporary Chrome profiles to clean")
            
    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}")

def main():
    logger.info("Starting run_main.py script...")
    
    try:
        cycle_count = 0
        while True:
            cycle_count += 1
            logger.info(f"=== Starting cycle {cycle_count} ===")
            
            # Kill existing processes
            logger.info("Step 1: Killing existing processes...")
            # killed = kill_existing_processes()
            
            # Clean up temporary files
            logger.info("Step 2: Cleaning temporary files...")
            cleanup_temp_files()
            
            # Clean up screenshots
            logger.info("Step 3: Cleaning screenshots...")
            screenshot_count = 0
            if os.path.exists("screenshots"):
                for filename in os.listdir("screenshots"):
                    file_path = os.path.join("screenshots", filename)
                    try:
                        os.remove(file_path)
                        screenshot_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove {file_path}: {e}")
                logger.info(f"Removed {screenshot_count} screenshots")
            else:
                os.makedirs("screenshots")
                logger.info("Created screenshots directory")
            
            # Check if main.py exists
            if not os.path.exists("main.py"):
                logger.error("ERROR: main.py file not found!")
                logger.info("Available files:")
                for file in os.listdir("."):
                    if file.endswith('.py'):
                        logger.info(f"  - {file}")
                input("Press Enter to exit...")
                return
            
            logger.info("Step 4: Starting main.py...")
            # Start with real-time output for debugging
            process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            logger.info(f"Script started with PID {process.pid}")
            
            # Monitor process for first 30 seconds to catch early issues
            logger.info("Monitoring process startup for 30 seconds...")
            start_time = time.time()
            while time.time() - start_time < 30:
                if process.poll() is not None:
                    # Process has terminated
                    stdout, stderr = process.communicate()
                    logger.error(f"Process terminated early with return code: {process.returncode}")
                    if stdout:
                        logger.error(f"STDOUT: {stdout}")
                    if stderr:
                        logger.error(f"STDERR: {stderr}")
                    break
                
                # Check for output
                try:
                    line = process.stdout.readline()
                    if line:
                        logger.info(f"main.py: {line.strip()}")
                except:
                    pass
                
                time.sleep(1)
            
            if process.poll() is None:
                logger.info("Process started successfully, running for 2 hours...")
                # Run for 2 hours (reduced from 3)
                time.sleep(7200)  # 2 hours
                
                logger.info("Time limit reached, terminating process...")
                try:
                    # Graceful shutdown first
                    process.terminate()
                    stdout, stderr = process.communicate(timeout=15)  # Reduced timeout
                    
                    if stdout:
                        logger.info(f"Final STDOUT: {stdout}")
                    if stderr:
                        logger.warning(f"Final STDERR: {stderr}")
                        
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("Force killing process...")
                    process.kill()
                    stdout, stderr = process.communicate()
                    
                    if stdout:
                        logger.info(f"Force kill STDOUT: {stdout}")
                    if stderr:
                        logger.warning(f"Force kill STDERR: {stderr}")
            
            # Clean up after termination
            logger.info("Cleaning up after process termination...")
            kill_existing_processes()
            cleanup_temp_files()
            
            logger.info("Waiting 3 seconds before restart...")
            time.sleep(3)  # Reduced wait time
            logger.info("Restarting the script...")
            
    except KeyboardInterrupt:
        logger.info("\nScript interrupted by user")
        if 'process' in locals() and process.poll() is None:
            logger.info("Terminating main process...")
            process.terminate()
            process.wait()
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
