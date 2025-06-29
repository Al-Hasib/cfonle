import pyautogui
import pygetwindow as gw
import time
import random
import os
from PIL import Image
import hashlib
from src.img import convert_folder_to_pdf
import os
import glob
from src.s3_connection import upload_pdf_s3

pyautogui.FAILSAFE = False

def move_mouse_smoothly(x, y):
    pyautogui.moveTo(x, y, duration=random.uniform(0.5, 1.2), tween=pyautogui.easeInOutQuad)

def get_dynamic_position(chrome_window, relative_x_percent, relative_y_percent):
    """
    Calculate dynamic position based on window size and position
    relative_x_percent: 0.0 to 1.0 (left to right)
    relative_y_percent: 0.0 to 1.0 (top to bottom)
    """
    x = chrome_window.left + int(chrome_window.width * relative_x_percent)
    y = chrome_window.top + int(chrome_window.height * relative_y_percent)
    return x, y


def remove_all_files(folder_path):
    """Remove all files in a folder (keeps the folder)"""
    try:
        files = glob.glob(os.path.join(folder_path, "*"))
        for file in files:
            if os.path.isfile(file):
                os.remove(file)
                print(f"Deleted: {file}")
        print(f"✅ All files removed from {folder_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

# Usage


# Step 1: Find the Chrome window
def main(vin):
    windows = gw.getWindowsWithTitle("Chrome")
    if not windows:
        print("❌ No Chrome window found.")
    else:
        print(f"Found {len(windows)} Chrome window(s)")
        chrome = windows[0]
        width, height = chrome.width, chrome.height
        x, y = chrome.left, chrome.top
        print(f"✅ Chrome Window Found")
        print(f"Position: ({x}, {y})")
        print(f"Size: {width}x{height}")
        pyautogui.click(x,y)
        
        # Step 2: Activate and get window info
        try:
            chrome.activate()
            time.sleep(3)
            
        except Exception as e:
            print(f"⚠️ Warning: Could not activate window normally ({e})")
            # Alternative activation method - click on the window
            width, height = chrome.width, chrome.height
            x, y = chrome.left, chrome.top
            print(f"✅ Chrome Window Found")
            print(f"Position: ({x}, {y})")
            print(f"Size: {width}x{height}")
            pyautogui.click(x,y)
            center_x = chrome.left + chrome.width // 2
            center_y = chrome.top + chrome.height // 2
            pyautogui.click(center_x, center_y)
            print("✅ Activated window by clicking")
        
        time.sleep(1)  # give time to focus
        
        
        
        # Refresh the page (commented out as in your code)
        pyautogui.hotkey('ctrl', 'r')
        time.sleep(5)
        
        # Step 3: Dynamic positioning based on window size
        # Dynamic scroll operations based on window height
        initial_scroll_up = int(height)  # Scroll up window height
        scroll_back_down = int(-50)   # Scroll back down 50 pixels
        time.sleep(2)
        
        pyautogui.scroll(initial_scroll_up)
        pyautogui.scroll(scroll_back_down)
        
        for first_click_x, first_click_y in zip(range(330,390,10), range(430, 490,10)):
            move_mouse_smoothly(first_click_x, first_click_y)
            pyautogui.click(first_click_x, first_click_y)
            pyautogui.write(vin)
            pyautogui.press('enter')
            time.sleep(2)
            
        # Second click position - dynamic as in your code
        second_click_x, second_click_y = get_dynamic_position(chrome, 0.31, 0.87)  # 31% from left, 87% from top
        
        move_mouse_smoothly(second_click_x, second_click_y)
        print("done")
        
        time.sleep(5)
        
        # Switch to tab 2
        pyautogui.hotkey('ctrl', '2')
        
        # Dynamic mouse positioning for scrolling area (fixed your typo)
        mouse_x = chrome.left + 200
        mouse_y = chrome.top + 300
        pyautogui.moveTo(mouse_x, mouse_y)
        time.sleep(0.5)
        
        scroll_amount = -int(height * 0.95)  # Scroll down 95% of window height each time
        output_dir = 'screenshots'
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Enhanced scroll loop with end detection
        max_scrolls = 20 # Increased from 2 to allow for end detection
        
        print("🔄 Starting intelligent scrolling with end detection...")
        
        for i in range(max_scrolls):
            # Take screenshot
            try:
                screenshot = pyautogui.screenshot()
            except OSError:
                print(f"❌ Screenshot {i+1} failed, trying alternative method...")
                try:
                    import PIL.ImageGrab as ImageGrab
                    screenshot = ImageGrab.grab()
                
                except Exception as e:
                    # print(f"❌ All screenshot methods failed for {i+1}")
                    print(f"Exception arise: {e}")
                    continue
            file_path = os.path.join(output_dir, f"screenshot_{i+1:03}.png")
            screenshot.save(file_path)
            print(f"✅ Saved: {file_path}")
            
            pyautogui.scroll(scroll_amount)
            time.sleep(2)  # Increased wait time to let content load
            
        print("✅ Done scrolling and saving screenshots.")
        
        # Step 5: Close the Chrome tab (commented out as in your code)
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'w')
        print("✅ Tab closed.")

        convert_folder_to_pdf(output_dir, f"PDF/{vin}.pdf")
        remove_all_files("screenshots")
        # upload_pdf_s3(f"PDF/{vin}.pdf")



if __name__=="__main__":
    main("1FMJU1K80PEA29105")

