import time

while True:
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")  # Get the current time
    print(f"Current time: {current_time}")
    
    # Wait for 2 seconds before checking again
    time.sleep(1)
