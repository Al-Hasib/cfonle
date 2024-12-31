import time
from datetime import datetime

while True:
    # Get the current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Current time: {current_time}")
    
    # Wait for 5 seconds
    time.sleep(5)

