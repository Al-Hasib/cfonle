import time
import schedule
from selenium import webdriver

def run_selenium_script():
    driver = None
    try:
        # Initialize the Selenium WebDriver
        driver = webdriver.Chrome()  # Replace with your WebDriver (e.g., ChromeDriver)
        driver.get("https://www.w3schools.com/")  # Replace with your target URL
        print("Page title:", driver.title)
        
        # Keep the driver running until 11:59 PM
        while True:
            current_time = time.localtime()  # Get the current time
            if current_time.tm_hour == 23 and current_time.tm_min == 59:
                break  # Exit loop at 11:59 PM
            time.sleep(1)  # Wait for 1 second before checking time again

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Quit the driver at 11:59 PM
        if driver:
            driver.quit()
            print("WebDriver has been quit.")

def schedule_script():
    while True:
        # Schedule the Selenium script to run once at 12:00 AM
        schedule.every().day.at("00:00").do(run_selenium_script)

        # Wait for the task to trigger
        schedule.run_pending()

        # Wait for the next check (it will check every second)
        time.sleep(1)

if __name__ == "__main__":
    print("Scheduler started. Waiting for 12:00 AM...")
    schedule_script()
