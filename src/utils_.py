import os
import json
import sys
import undetected_chromedriver as uc
from selenium_stealth import stealth
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import random
import shutil
import glob
import logging
import pyautogui
import pywinauto
from pywinauto import Application
from pywinauto.keyboard import send_keys
import win32gui
import win32con
import win32api
import win32process
import win32clipboard
import psutil
import cv2
import numpy as np
from PIL import Image
from src.Tele import SendPdf, TryAgainMsg
from src.img import convert_folder_to_pdf
from src.s3_connection import upload_pdf_s3

# Setup logging
logger = logging.getLogger(__name__)

# Ensure directories exist
for directory in ['PDF', 'PDF_API', 'screenshots', 'screenshots_api', 'screenshots_api_2']:
    if not os.path.exists(directory):
        os.mkdir(directory)

# Load configuration
try:
    with open('Config.json', 'r') as f:
        config = json.load(f)
    
    url = config['url']
    email = config['email']
    pasw = config['password']
    apiToken = '6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE'
    chatID = '5491808070'
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Error loading configuration: {e}")
    raise

# Chrome Profile 2 path
CHROME_PROFILE_PATH = os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\User Data")
PROFILE_NAME = "Profile 2"

# Special characters that need escaping in pywinauto
SPECIAL_CHARS = ['+', '^', '%', '(', ')', '{', '}', '[', ']', '~', '#', '@', '!', '$', '&', '*', '_', '=', ':', ';', ',', '.', '?', '/', '\\']

def kill_all_chrome_instances():
    """Enhanced Chrome process killer - FIXED"""
    try:
        logger.info("Killing all existing Chrome instances...")
        killed_count = 0
        
        # Kill Chrome processes more aggressively
        chrome_process_names = [
            'chrome.exe', 'chromedriver.exe', 'undetected_chromedriver.exe',
            'chrome', 'chromedriver', 'Google Chrome'
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                proc_info = proc.info
                if proc_info['name']:
                    # Check process name
                    if any(chrome_name in proc_info['name'].lower() for chrome_name in chrome_process_names):
                        proc.terminate()  # Try graceful termination first
                        time.sleep(0.5)
                        
                        if proc.is_running():
                            proc.kill()  # Force kill if still running
                        
                        killed_count += 1
                        logger.info(f"Killed process: {proc_info['name']} (PID: {proc_info['pid']})")
                        
                    # Check command line for chrome-related processes
                    elif proc_info['cmdline']:
                        cmdline_str = ' '.join(proc_info['cmdline']).lower()
                        if any(chrome_name in cmdline_str for chrome_name in chrome_process_names):
                            proc.terminate()
                            time.sleep(0.5)
                            
                            if proc.is_running():
                                proc.kill()
                            
                            killed_count += 1
                            logger.info(f"Killed Chrome-related process: {proc_info['name']} (PID: {proc_info['pid']})")
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logger.warning(f"Error killing process: {e}")
                continue
        
        if killed_count > 0:
            logger.info(f"Total Chrome processes killed: {killed_count}")
            time.sleep(5)  # Wait longer for processes to fully terminate
        else:
            logger.info("No Chrome processes found to kill")
        
        # Clean up temp directories
        import tempfile
        temp_dir = tempfile.gettempdir()
        for item in os.listdir(temp_dir):
            if item.startswith('chrome_profile_') or item.startswith('chrome_pywin_'):
                try:
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logger.info(f"Cleaned temp Chrome profile: {item}")
                except Exception as e:
                    logger.warning(f"Could not clean temp profile {item}: {e}")
            
    except Exception as e:
        logger.error(f"Error killing Chrome instances: {e}")


def detect_page_state_advanced(driver):
    """Advanced page detection based on actual CARFAX Online structure"""
    try:
        current_url = driver.current_url.lower()
        page_source = driver.page_source.lower()
        page_title = driver.title.lower()
        
        logger.info(f"Analyzing page - URL: {current_url}, Title: {page_title}")
        
        # Based on your actual PDFs and HTML files:
        
        # 1. Login page detection (auth.carfax.com)
        if ('auth.carfax.com' in current_url or 
            'login' in current_url or
            'log in with carfax' in page_source or
            'email address' in page_source and 'password' in page_source):
            logger.info("Detected: LOGIN PAGE")
            return 'login_page'
        
        # 2. Landing/Dealer page detection
        elif ('carfaxonline.com/landing' in current_url or
              'dealer account sign in' in page_title or
              'carfax provides the most accident' in page_source):
            logger.info("Detected: LANDING PAGE")
            return 'landing_page'
        
        # 3. Home/Search page detection (main CARFAX Online page)
        elif ('carfaxonline.com' in current_url and 
              'login' not in current_url and
              ('search by vin' in page_source or
               'get carfax report' in page_source or
               'carfax online | home' in page_title)):
            logger.info("Detected: HOME/SEARCH PAGE")
            return 'home_page'
        
        # 4. Vehicle History Report page detection
        elif ('carfax vehicle history report' in page_title or
              'vehicle history report' in page_source or
              'carfax report provided' in page_source or
              '/vhr/' in current_url):
            logger.info("Detected: REPORT PAGE")
            return 'report_page'
        
        # 5. Error page detection
        elif ('error' in page_title or
              '404' in page_source or
              '500' in page_source or
              'something went wrong' in page_source):
            logger.info("Detected: ERROR PAGE")
            return 'error_page'
        
        logger.warning(f"Unknown page state - URL: {current_url}")
        return 'unknown_page'
        
    except Exception as e:
        logger.error(f"Error detecting page state: {e}")
        return 'unknown_page'

def find_element_with_verification(driver, element_configs, timeout=15):
    """Find elements with multiple strategies and verification"""
    wait = WebDriverWait(driver, timeout)
    
    for config in element_configs:
        element_type = config.get('type', 'unknown')
        selectors = config.get('selectors', [])
        expected_attributes = config.get('attributes', {})
        
        logger.info(f"Searching for {element_type} element...")
        
        for selector_info in selectors:
            by_method = selector_info['by']
            value = selector_info['value']
            
            try:
                element = wait.until(EC.presence_of_element_located((by_method, value)))
                
                if element and element.is_displayed():
                    # Verify element attributes
                    if _verify_element_attributes(element, expected_attributes):
                        logger.info(f"Found and verified {element_type} using {by_method}: {value}")
                        return element
                    else:
                        logger.warning(f"Element found but attributes don't match for {element_type}")
                        
            except TimeoutException:
                continue
            except Exception as e:
                logger.warning(f"Error with selector {by_method}:{value} - {e}")
                continue
    
    logger.error(f"Could not find element with any of the provided selectors")
    return None

def _verify_element_attributes(element, expected_attributes):
    """Verify element has expected attributes"""
    try:
        for attr_name, expected_values in expected_attributes.items():
            actual_value = element.get_attribute(attr_name) or ''
            
            if isinstance(expected_values, list):
                if not any(expected in actual_value.lower() for expected in expected_values):
                    return False
            else:
                if expected_values.lower() not in actual_value.lower():
                    return False
        return True
    except Exception as e:
        logger.error(f"Error verifying attributes: {e}")
        return False

def verify_text_input_with_retry(element, expected_text, max_retries=3):
    """Verify text input with retry logic"""
    for attempt in range(max_retries):
        try:
            # Clear the field first
            element.clear()
            time.sleep(random.uniform(0.3, 0.7))
            
            # Type the text
            for char in expected_text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            time.sleep(random.uniform(0.5, 1.0))
            
            # Verify the text was entered correctly
            actual_value = element.get_attribute('value') or ''
            
            if actual_value.strip() == expected_text.strip():
                logger.info(f"Text verification successful: '{expected_text}' == '{actual_value}'")
                return True
            else:
                logger.warning(f"Text verification failed on attempt {attempt + 1}: expected '{expected_text}', got '{actual_value}'")
                
                if attempt < max_retries - 1:
                    # Try alternative input methods
                    if attempt == 1:
                        # Try clipboard method
                        try:
                            win32clipboard.OpenClipboard()
                            win32clipboard.EmptyClipboard()
                            win32clipboard.SetClipboardText(expected_text)
                            win32clipboard.CloseClipboard()
                            
                            element.clear()
                            time.sleep(0.3)
                            element.send_keys(Keys.CONTROL + 'v')
                            time.sleep(0.5)
                            
                        except Exception as clipboard_error:
                            logger.error(f"Clipboard method failed: {clipboard_error}")
                    
                    elif attempt == 2:
                        # Try JavaScript input
                        try:
                            driver = element._parent
                            driver.execute_script("arguments[0].value = arguments[1];", element, expected_text)
                            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
                            time.sleep(0.5)
                        except Exception as js_error:
                            logger.error(f"JavaScript method failed: {js_error}")
                
        except Exception as e:
            logger.error(f"Error during text input attempt {attempt + 1}: {e}")
    
    return False

def get_login_page_elements():
    """Get login page element configurations based on actual HTML"""
    return [
        {
            'type': 'email_field',
            'selectors': [
                {'by': By.ID, 'value': 'username'},  # From actual login HTML
                {'by': By.NAME, 'value': 'username'},
                {'by': By.CSS_SELECTOR, 'value': 'input[type="email"]'},
                {'by': By.CSS_SELECTOR, 'value': 'input[placeholder*="email"]'},
                {'by': By.XPATH, 'value': '//input[@type="email" or @type="text"]'},
            ],
            'attributes': {
                'type': ['email', 'text'],
                'placeholder': ['email']
            }
        },
        {
            'type': 'password_field',
            'selectors': [
                {'by': By.ID, 'value': 'password'},
                {'by': By.NAME, 'value': 'password'},
                {'by': By.CSS_SELECTOR, 'value': 'input[type="password"]'},
                {'by': By.XPATH, 'value': '//input[@type="password"]'},
            ],
            'attributes': {
                'type': ['password']
            }
        },
        {
            'type': 'login_button',
            'selectors': [
                {'by': By.CSS_SELECTOR, 'value': 'button[type="submit"]'},
                {'by': By.CSS_SELECTOR, 'value': 'input[type="submit"]'},
                {'by': By.XPATH, 'value': '//button[contains(text(), "Log In") or contains(text(), "Sign In")]'},
                {'by': By.CSS_SELECTOR, 'value': 'button[data-action-button-primary="true"]'},  # From actual HTML
            ],
            'attributes': {}
        }
    ]

def get_home_page_elements():
    """Get home page element configurations based on actual HTML and PDF"""
    return [
        {
            'type': 'vin_input',
            'selectors': [
                {'by': By.ID, 'value': 'vin'},  # Most likely based on CARFAX structure
                {'by': By.NAME, 'value': 'vin'},
                {'by': By.CSS_SELECTOR, 'value': 'input[placeholder*="VIN"]'},
                {'by': By.CSS_SELECTOR, 'value': 'input[name*="vin"]'},
                {'by': By.XPATH, 'value': '//input[@type="text" and contains(@placeholder, "VIN")]'},
                {'by': By.XPATH, 'value': '//input[@type="text"][1]'},  # First text input on page
            ],
            'attributes': {
                'type': ['text'],
                'maxlength': ['17', '20']  # VIN is typically 17 characters
            }
        },
        {
            'type': 'submit_button',
            'selectors': [
                {'by': By.XPATH, 'value': '//button[contains(text(), "Get CARFAX Report")]'},  # From PDF
                {'by': By.CSS_SELECTOR, 'value': 'button[type="submit"]'},
                {'by': By.CSS_SELECTOR, 'value': 'input[type="submit"]'},
                {'by': By.XPATH, 'value': '//input[@value="Get CARFAX Report"]'},
                {'by': By.XPATH, 'value': '//button[contains(@class, "submit") or contains(@class, "btn")]'},
            ],
            'attributes': {}
        }
    ]

def handle_login_intelligently_enhanced(driver, email, pasw):
    """Enhanced intelligent login with deep verification"""
    try:
        page_state = detect_page_state_advanced(driver)
        logger.info(f"Current page state: {page_state}")
        
        # Navigate to correct login page if needed
        if page_state == 'landing_page':
            # Look for login link or navigate directly
            try:
                # Try to find login link on landing page
                login_link = driver.find_element(By.XPATH, '//a[contains(@href, "login") or contains(text(), "Log In")]')
                login_link.click()
                time.sleep(random.uniform(3, 5))
            except:
                # Navigate directly to auth page
                driver.get("https://auth.carfax.com/u/login")
                time.sleep(random.uniform(3, 5))
        
        elif page_state == 'home_page':
            logger.info("Already logged in - on home page")
            return driver
            
        elif page_state != 'login_page':
            # Navigate to login page
            driver.get("https://auth.carfax.com/u/login")
            time.sleep(random.uniform(3, 5))
        
        # Verify we're on login page
        page_state = detect_page_state_advanced(driver)
        if page_state != 'login_page':
            logger.error("Could not reach login page")
            return None
        
        # Check for reCAPTCHA
        wait_for_recaptcha_solution(driver)
        
        # Get login elements
        login_elements = get_login_page_elements()
        
        # Find email field
        email_element = find_element_with_verification(driver, [login_elements[0]])
        if not email_element:
            logger.error("Could not find email field")
            return None
        
        # Find password field
        password_element = find_element_with_verification(driver, [login_elements[1]])
        if not password_element:
            logger.error("Could not find password field")
            return None
        
        # Check for pre-filled credentials
        email_value = email_element.get_attribute('value') or ''
        password_value = password_element.get_attribute('value') or ''
        
        if email_value and password_value:
            logger.info(f"Found pre-filled credentials - Email: {email_value[:3]}***")
            
            # Try login with pre-filled credentials
            login_button = find_element_with_verification(driver, [login_elements[2]])
            if login_button:
                login_button.click()
                time.sleep(random.uniform(5, 8))
                
                # Check if login was successful
                if detect_page_state_advanced(driver) == 'home_page':
                    logger.info("Login successful with pre-filled credentials")
                    return driver
        
        # Use provided credentials with verification
        logger.info("Using provided credentials for login")
        
        # Enter email with verification
        if not verify_text_input_with_retry(email_element, email):
            logger.error("Failed to enter email correctly")
            return None
        
        # Enter password with verification
        if not verify_text_input_with_retry(password_element, pasw):
            logger.error("Failed to enter password correctly")
            return None
        
        # Check for reCAPTCHA again
        wait_for_recaptcha_solution(driver)
        
        # Find and click login button
        login_button = find_element_with_verification(driver, [login_elements[2]])
        if not login_button:
            logger.error("Could not find login button")
            return None
        
        login_button.click()
        time.sleep(random.uniform(5, 8))
        
        # Verify login success
        final_page_state = detect_page_state_advanced(driver)
        if final_page_state == 'home_page':
            logger.info("Login successful with provided credentials")
            return driver
        else:
            logger.error(f"Login failed - ended up on: {final_page_state}")
            return None
        
    except Exception as e:
        logger.error(f"Error in enhanced intelligent login: {e}")
        return None

def handle_vin_search_intelligently_enhanced(driver, vin):
    """Enhanced VIN search with deep verification"""
    try:
        page_state = detect_page_state_advanced(driver)
        logger.info(f"Current page state for VIN search: {page_state}")
        
        # Navigate to home page if needed
        if page_state != 'home_page':
            driver.get("https://www.carfaxonline.com/")
            time.sleep(random.uniform(3, 5))
            
            # Verify we're on home page
            page_state = detect_page_state_advanced(driver)
            if page_state != 'home_page':
                logger.error("Could not reach home page for VIN search")
                return False
        
        # Check for reCAPTCHA
        wait_for_recaptcha_solution(driver)
        
        # Get home page elements
        home_elements = get_home_page_elements()
        
        # Find VIN input field with verification
        vin_input = find_element_with_verification(driver, [home_elements[0]])
        if not vin_input:
            logger.error("Could not find VIN input field")
            return False
        
        # Enter VIN with verification
        if not verify_text_input_with_retry(vin_input, vin):
            logger.error("Failed to enter VIN correctly")
            return False
        
        logger.info(f"VIN '{vin}' entered and verified successfully")
        
        # Wait a moment before submitting
        time.sleep(random.uniform(1, 2))
        
        # Check for reCAPTCHA again
        wait_for_recaptcha_solution(driver)
        
        # Find and click submit button
        submit_button = find_element_with_verification(driver, [home_elements[1]])
        if not submit_button:
            logger.error("Could not find submit button")
            return False
        
        # Click submit button
        submit_button.click()
        logger.info("Submit button clicked successfully")
        time.sleep(8)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in enhanced VIN search: {e}")
        return False

def handle_report_capture_intelligently_enhanced(driver, vin):
    """Enhanced report capture with intelligent detection"""
    try:
        # Wait for report to load
        time.sleep(10)
        
        # Check if we're on a report page or if a new window opened
        if len(driver.window_handles) > 1:
            logger.info("Report opened in new window")
            driver.switch_to.window(driver.window_handles[-1])
        
        # Verify we're on report page
        page_state = detect_page_state_advanced(driver)
        if page_state != 'report_page':
            logger.warning(f"Expected report page, but got: {page_state}")
            # Continue anyway as report might still be loading
        
        # Wait for report content to load intelligently
        wait = WebDriverWait(driver, 120)
        
        # Try to detect report content based on actual HTML structure
        report_loaded = False
        report_indicators = [
            "//div[contains(@class, 'report')]",
            "//div[contains(text(), 'CARFAX Vehicle History Report')]",
            "//div[contains(text(), 'Vehicle History Report')]",
            "//*[contains(text(), 'This CARFAX Report')]",
            "//div[contains(@class, 'vehicle-history')]"
        ]
        
        for indicator in report_indicators:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                report_loaded = True
                logger.info(f"Report loaded - found indicator: {indicator}")
                break
            except TimeoutException:
                continue
        
        if not report_loaded:
            logger.warning("Report indicators not found, proceeding with capture anyway")
            time.sleep(15)
        
        # Maximize window for better screenshots
        driver.maximize_window()
        time.sleep(3)
        
        # Hide elements that shouldn't be printed (based on actual CARFAX structure)
        elements_to_hide = [
            '.do-not-print',
            '.no-print', 
            '.print-hide',
            '.back-to-top-button',
            '.navigation',
            '.header-nav',
            '.footer',
            '.ads',
            '.advertisement',
            '[class*="nav"]',
            '[class*="header"]',
            '[class*="footer"]'
        ]
        
        for element_selector in elements_to_hide:
            try:
                driver.execute_script(f"""
                    var elements = document.querySelectorAll('{element_selector}');
                    elements.forEach(function(el) {{ 
                        el.style.display = 'none'; 
                        el.style.visibility = 'hidden';
                    }});
                """)
            except Exception as e:
                logger.warning(f"Could not hide elements with selector {element_selector}: {e}")
        
        time.sleep(2)
        
        # Get page dimensions for intelligent scrolling
        try:
            height = driver.execute_script("""
                return Math.max(
                    document.body.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.clientHeight,
                    document.documentElement.scrollHeight,
                    document.documentElement.offsetHeight
                );
            """)
            scroll_height = driver.execute_script("return window.innerHeight")
            logger.info(f"Page dimensions - height: {height}, viewport: {scroll_height}")
        except:
            height = 8000  # Conservative estimate for CARFAX reports
            scroll_height = 800
        
        # Intelligent screenshot capture with overlap
        scroll_offset = 0
        counter = 1
        
        # Take first screenshot
        driver.save_screenshot(f'screenshots/Image_1.png')
        logger.info("Captured screenshot 1")
        
        # Scroll and capture with proper overlap
        while scroll_offset < height - 200:  # Leave some margin
            scroll_offset += scroll_height - 150  # 150px overlap for continuity
            
            # Scroll to position smoothly
            driver.execute_script(f"window.scrollTo({{top: {scroll_offset}, behavior: 'smooth'}});")
            time.sleep(4)  # Wait for smooth scroll and content to settle
            
            # Hide floating elements again after scroll
            for element_selector in elements_to_hide:
                try:
                    driver.execute_script(f"""
                        var elements = document.querySelectorAll('{element_selector}');
                        elements.forEach(function(el) {{ 
                            el.style.display = 'none'; 
                            el.style.visibility = 'hidden';
                        }});
                    """)
                except:
                    pass
            
            counter += 1
            driver.save_screenshot(f'screenshots/Image_{counter}.png')
            logger.info(f"Captured screenshot {counter} at scroll position {scroll_offset}")
            
            # Safety limit for very long reports
            if counter > 35:
                logger.warning("Reached maximum screenshot limit")
                break
        
        # Convert screenshots to PDF
        input_path = 'screenshots'
        output_path = f'PDF/{vin}.pdf'
        convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
        logger.info('PDF formatting completed')
        
        # Upload to S3
        upload_pdf_s3(output_path)
        
        # Clean up
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        
        # Clean screenshots directory
        if os.path.exists("screenshots"):
            for filename in os.listdir("screenshots"):
                file_path = os.path.join("screenshots", filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        logger.info("Enhanced report capture completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Enhanced report capture failed: {e}")
        return False

# Include all the previous browser setup functions (unchanged)
def escape_special_chars_for_pywinauto(text):
    """Escape special characters for pywinauto type_keys"""
    escaped = ''
    for ch in text:
        if ch in SPECIAL_CHARS:
            escaped += '{' + ch + '}'
        else:
            escaped += ch
    return escaped

def type_url_safely(url_text, method='clipboard'):
    """Type URL safely using different methods"""
    try:
        if method == 'clipboard':
            return _type_url_clipboard(url_text)
        elif method == 'pyautogui':
            return _type_url_pyautogui(url_text)
        elif method == 'pywinauto':
            return _type_url_pywinauto(url_text)
        elif method == 'win32':
            return _type_url_win32(url_text)
        else:
            return _type_url_clipboard(url_text)
    except Exception as e:
        logger.error(f"Error typing URL with method {method}: {e}")
        return False

def _type_url_clipboard(url_text):
    """Type URL using clipboard (most reliable method)"""
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(url_text)
        win32clipboard.CloseClipboard()
        
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)
        
        logger.info(f"URL typed using clipboard method: {url_text}")
        return True
    except Exception as e:
        logger.error(f"Clipboard method failed: {e}")
        return False

def _type_url_pyautogui(url_text):
    """Type URL using pyautogui with proper interval"""
    try:
        pyautogui.typewrite(url_text, interval=0.05)
        logger.info(f"URL typed using pyautogui: {url_text}")
        return True
    except Exception as e:
        logger.error(f"PyAutoGUI method failed: {e}")
        return False

def _type_url_pywinauto(url_text):
    """Type URL using pywinauto with escaped characters"""
    try:
        escaped_url = escape_special_chars_for_pywinauto(url_text)
        send_keys(escaped_url, with_spaces=True)
        logger.info(f"URL typed using pywinauto: {url_text}")
        return True
    except Exception as e:
        logger.error(f"PyWinAuto method failed: {e}")
        return False

def _type_url_win32(url_text):
    """Type URL using Win32 API character by character"""
    try:
        for char in url_text:
            if char == ':':
                pyautogui.hotkey('shift', ';')
            elif char == '/':
                pyautogui.press('/')
            elif char == '.':
                pyautogui.press('.')
            elif char == '?':
                pyautogui.hotkey('shift', '/')
            elif char == '=':
                pyautogui.press('=')
            elif char == '&':
                pyautogui.hotkey('shift', '7')
            else:
                pyautogui.typewrite(char)
            
            time.sleep(random.uniform(0.05, 0.1))
        
        logger.info(f"URL typed using Win32 method: {url_text}")
        return True
    except Exception as e:
        logger.error(f"Win32 method failed: {e}")
        return False

def detect_recaptcha(driver):
    """Detect if reCAPTCHA is present on the page"""
    try:
        recaptcha_selectors = [
            "iframe[src*='recaptcha']",
            ".g-recaptcha",
            "#recaptcha",
            "[data-sitekey]",
            ".recaptcha-checkbox",
            "iframe[title*='reCAPTCHA']"
        ]
        
        for selector in recaptcha_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logger.warning("reCAPTCHA detected!")
                print("reCAPTCHA found")
                return True
        return False
    except Exception as e:
        logger.error(f"Error detecting reCAPTCHA: {e}")
        return False

def wait_for_recaptcha_solution(driver, timeout=30):
    """Wait for human to solve reCAPTCHA"""
    if detect_recaptcha(driver):
        logger.info(f"Waiting {timeout} seconds for human to solve reCAPTCHA...")
        time.sleep(timeout)
        return True
    return False

def clean_chromedriver_cache():
    """Clean and refresh ChromeDriver cache"""
    try:
        cache_dir = os.path.expanduser("~/.wdm")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            logger.info("Cleared ChromeDriver cache")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")

def get_fresh_chromedriver():
    """Get a fresh ChromeDriver installation with correct path"""
    try:
        clean_chromedriver_cache()
        initial_path = ChromeDriverManager().install()
        logger.info(f"Initial path from ChromeDriverManager: {initial_path}")
        
        if "THIRD_PARTY_NOTICES.chromedriver" in initial_path:
            driver_dir = os.path.dirname(initial_path)
            possible_paths = [
                os.path.join(driver_dir, "chromedriver.exe"),
                os.path.join(driver_dir, "chromedriver-win32", "chromedriver.exe"),
                os.path.join(driver_dir, "chromedriver"),
            ]
            
            glob_patterns = [
                os.path.join(driver_dir, "**/chromedriver.exe"),
                os.path.join(driver_dir, "**/chromedriver"),
            ]
            
            for pattern in glob_patterns:
                matches = glob.glob(pattern, recursive=True)
                possible_paths.extend(matches)
            
            for path in possible_paths:
                if os.path.exists(path) and os.path.isfile(path):
                    logger.info(f"Found valid ChromeDriver at: {path}")
                    return path
        
        if os.path.exists(initial_path) and os.path.isfile(initial_path):
            logger.info(f"Using initial path: {initial_path}")
            return initial_path
        
        logger.error("Could not find valid ChromeDriver executable")
        return None
        
    except Exception as e:
        logger.error(f"Error getting ChromeDriver: {e}")
        return None

def get_browser(headless=False, proxy=False, strategy=1):
    """Enhanced browser setup with Profile 2 and multiple anti-detection strategies"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    try:
        if strategy == 1:
            return _get_undetected_browser(headless, proxy, user_agents)
        elif strategy == 2:
            return _get_stealth_browser(headless, proxy, user_agents)
        elif strategy == 3:
            return _get_fortified_browser(headless, proxy, user_agents)
        elif strategy == 4:
            return _get_basic_browser(headless, proxy, user_agents)
        elif strategy == 5:
            return _get_hybrid_browser(headless, proxy, user_agents)
        elif strategy == 6:
            return _get_pywinauto_browser()
        elif strategy == 7:
            return _get_pywin32_browser()
        else:
            return _get_hybrid_browser(headless, proxy, user_agents)
            
    except Exception as e:
        logger.error(f"Strategy {strategy} failed: {str(e)}")
        return None

def _get_undetected_browser(headless, proxy, user_agents):
    """Strategy 1: Undetected ChromeDriver with Profile 2"""
    try:
        options = uc.ChromeOptions()
        
        # Use Profile 2
        options.add_argument(f'--user-data-dir={CHROME_PROFILE_PATH}')
        options.add_argument(f'--profile-directory={PROFILE_NAME}')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--log-level=3')
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        window_sizes = ['1366,768', '1920,1080', '1440,900']
        options.add_argument(f'--window-size={random.choice(window_sizes)}')
        
        if headless:
            options.add_argument('--headless=new')
        
        driver = uc.Chrome(options=options, use_subprocess=False, version_main=None)
        
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except:
            pass
        
        logger.info("Undetected browser created with Profile 2")
        return driver
    except Exception as e:
        logger.error(f"Error creating undetected browser: {e}")
        return None

def _get_stealth_browser(headless, proxy, user_agents):
    """Strategy 2: Selenium Stealth with Profile 2 - FIXED"""
    try:
        options = Options()
        
        # Create unique temp profile to avoid conflicts
        import tempfile
        temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
        
        # Use temp profile instead of Profile 2 to avoid conflicts
        options.add_argument(f'--user-data-dir={temp_profile}')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-default-apps')
        
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--log-level=3')
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        window_sizes = ['1366,768', '1920,1080', '1440,900']
        options.add_argument(f'--window-size={random.choice(window_sizes)}')
        
        if headless:
            options.add_argument('--headless=new')
        
        chromedriver_path = get_fresh_chromedriver()
        if not chromedriver_path:
            raise Exception("Could not get valid ChromeDriver path")
        
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                webdriver=False)
        
        logger.info("Stealth browser created with temp profile")
        return driver
    except Exception as e:
        logger.error(f"Error creating stealth browser: {e}")
        return None


def _get_fortified_browser(headless, proxy, user_agents):
    """Strategy 3: Manual fortification with Profile 2"""
    try:
        options = Options()
        
        # Use Profile 2
        options.add_argument(f'--user-data-dir={CHROME_PROFILE_PATH}')
        options.add_argument(f'--profile-directory={PROFILE_NAME}')
        
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--log-level=3')
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        window_sizes = ['1366,768', '1920,1080', '1440,900']
        options.add_argument(f'--window-size={random.choice(window_sizes)}')
        
        if headless:
            options.add_argument('--headless=new')
        
        chromedriver_path = get_fresh_chromedriver()
        if not chromedriver_path:
            raise Exception("Could not get valid ChromeDriver path")
        
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        except:
            pass
        
        logger.info("Fortified browser created with Profile 2")
        return driver
    except Exception as e:
        logger.error(f"Error creating fortified browser: {e}")
        return None

def _get_basic_browser(headless, proxy, user_agents):
    """Strategy 4: Basic Chrome with Profile 2"""
    try:
        options = Options()
        
        # Use Profile 2
        options.add_argument(f'--user-data-dir={CHROME_PROFILE_PATH}')
        options.add_argument(f'--profile-directory={PROFILE_NAME}')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--log-level=3')
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        if headless:
            options.add_argument('--headless=new')
        
        chromedriver_path = get_fresh_chromedriver()
        if not chromedriver_path:
            raise Exception("Could not get valid ChromeDriver path")
        
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        logger.info("Basic browser created with Profile 2")
        return driver
    except Exception as e:
        logger.error(f"Error creating basic browser: {e}")
        return None

def _get_hybrid_browser(headless, proxy, user_agents):
    """Strategy 5: Hybrid approach with Profile 2"""
    try:
        return _get_stealth_browser(headless, proxy, user_agents)
    except:
        try:
            return _get_basic_browser(headless, proxy, user_agents)
        except:
            return _get_undetected_browser(headless, proxy, user_agents)

def _get_pywinauto_browser():
    """Strategy 6: PyWinAuto approach - FIXED"""
    try:
        # Launch Chrome with Profile 2 using pywinauto
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
        if not os.path.exists(chrome_path):
            logger.error("Chrome executable not found")
            return None
        
        # Create unique temp profile to avoid conflicts
        import tempfile
        temp_profile = tempfile.mkdtemp(prefix="chrome_pywin_")
        
        # Launch Chrome with temp profile
        cmd = f'"{chrome_path}" --user-data-dir="{temp_profile}" --no-first-run --disable-default-apps'
        
        try:
            app = Application().start(cmd)
            time.sleep(5)  # Wait longer for Chrome to start
            
            # Connect to Chrome window with retry
            for attempt in range(3):
                try:
                    chrome_window = app.top_window()
                    chrome_window.maximize()
                    logger.info("PyWinAuto browser launched successfully")
                    return PyWinAutoDriver(chrome_window, app)  # Pass app reference
                except Exception as e:
                    logger.warning(f"PyWinAuto connection attempt {attempt + 1} failed: {e}")
                    time.sleep(2)
            
            logger.error("Could not connect to Chrome window after 3 attempts")
            return None
            
        except Exception as e:
            logger.error(f"Failed to start Chrome with PyWinAuto: {e}")
            return None
        
    except Exception as e:
        logger.error(f"Error creating PyWinAuto browser: {e}")
        return None

class PyWinAutoDriver:
    """PyWinAuto-based driver for human-like automation - FIXED"""
    
    def __init__(self, window, app):
        self.window = window
        self.app = app  # Store app reference directly
        
    def get(self, url):
        """Navigate to URL using PyWinAuto with enhanced URL typing"""
        try:
            # Bring window to front
            self.window.set_focus()
            time.sleep(1)
            
            # Click address bar (Ctrl+L)
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(random.uniform(0.5, 1.0))
            
            # Try different methods to type URL
            success = False
            methods = ['clipboard', 'pyautogui']
            
            for method in methods:
                if type_url_safely(url, method):
                    success = True
                    break
                time.sleep(0.5)
            
            if not success:
                logger.error("All URL typing methods failed")
                return False
            
            # Press Enter
            time.sleep(random.uniform(0.5, 1.0))
            pyautogui.press('enter')
            time.sleep(random.uniform(3, 5))
            
            logger.info(f"Navigated to {url} using PyWinAuto")
            return True
        except Exception as e:
            logger.error(f"Error navigating with PyWinAuto: {e}")
            return False


def _get_pywin32_browser():
    """Strategy 7: PyWin32 approach - Direct Windows API"""
    try:
        # Launch Chrome using win32api
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
        if not os.path.exists(chrome_path):
            logger.error("Chrome executable not found")
            return None
        
        # Create command with profile
        cmd = f'"{chrome_path}" --user-data-dir="{CHROME_PROFILE_PATH}" --profile-directory="{PROFILE_NAME}"'
        
        # Start process
        startup_info = win32process.STARTUPINFO()
        process_info = win32process.CreateProcess(
            None, cmd, None, None, False, 0, None, None, startup_info
        )
        
        time.sleep(3)  # Wait for Chrome to start
        
        # Find Chrome window
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if "Chrome" in window_text:
                    windows.append(hwnd)
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if windows:
            chrome_hwnd = windows[0]
            win32gui.ShowWindow(chrome_hwnd, win32con.SW_MAXIMIZE)
            logger.info("PyWin32 browser launched with Profile 2")
            return PyWin32Driver(chrome_hwnd, process_info[2])  # Pass PID
        else:
            logger.error("Could not find Chrome window")
            return None
            
    except Exception as e:
        logger.error(f"Error creating PyWin32 browser: {e}")
        return None

# Include PyWinAuto and PyWin32 driver classes (unchanged from previous version)
class PyWinAutoDriver:
    """PyWinAuto-based driver for human-like automation"""
    
    def __init__(self, window):
        self.window = window
        self.app = window.application()
        
    def get(self, url):
        """Navigate to URL using PyWinAuto with enhanced URL typing"""
        try:
            # Click address bar (Ctrl+L)
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(random.uniform(0.5, 1.0))
            
            # Try different methods to type URL
            success = False
            methods = ['clipboard', 'pyautogui', 'pywinauto']
            
            for method in methods:
                if type_url_safely(url, method):
                    success = True
                    break
                time.sleep(0.5)
            
            if not success:
                logger.error("All URL typing methods failed")
                return False
            
            # Press Enter
            time.sleep(random.uniform(0.5, 1.0))
            pyautogui.press('enter')
            time.sleep(random.uniform(2, 4))
            
            logger.info(f"Navigated to {url} using PyWinAuto")
            return True
        except Exception as e:
            logger.error(f"Error navigating with PyWinAuto: {e}")
            return False
    
    def find_element_by_id(self, element_id):
        """Find element by ID using PyWinAuto"""
        try:
            return PyWinAutoElement(self, element_id)
        except Exception as e:
            logger.error(f"Error finding element {element_id}: {e}")
            return None
    
    def execute_script(self, script):
        """Execute JavaScript (limited functionality)"""
        try:
            # Open developer console
            pyautogui.hotkey('ctrl', 'shift', 'i')
            time.sleep(1)
            
            # Click console tab
            pyautogui.click(100, 100)  # Approximate position
            time.sleep(0.5)
            
            # Type script using clipboard method
            type_url_safely(script, 'clipboard')
            pyautogui.press('enter')
            time.sleep(1)
            
            # Close developer console
            pyautogui.hotkey('ctrl', 'shift', 'i')
            return True
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return False
    
    def save_screenshot(self, filename):
        """Save screenshot using PyAutoGUI"""
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            logger.info(f"Screenshot saved: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return False
    
    def quit(self):
        """Close browser"""
        try:
            pyautogui.hotkey('ctrl', 'shift', 'q')
            time.sleep(2)
            logger.info("Browser closed using PyWinAuto")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

class PyWinAutoElement:
    """PyWinAuto element wrapper"""
    
    def __init__(self, driver, element_id):
        self.driver = driver
        self.element_id = element_id
    
    def clear(self):
        """Clear element content"""
        try:
            # Select all and delete
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.press('delete')
            return True
        except Exception as e:
            logger.error(f"Error clearing element: {e}")
            return False
    
    def send_keys(self, text):
        """Send keys to element with human-like typing"""
        try:
            # Try clipboard method first for reliability
            if type_url_safely(text, 'clipboard'):
                return True
            
            # Fallback to character-by-character typing
            for char in text:
                pyautogui.typewrite(char)
                time.sleep(random.uniform(0.1, 0.3))
            return True
        except Exception as e:
            logger.error(f"Error sending keys: {e}")
            return False
    
    def click(self):
        """Click element"""
        try:
            # Use Tab to navigate to element, then Enter
            pyautogui.press('tab')
            time.sleep(0.5)
            pyautogui.press('enter')
            return True
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False

class PyWin32Driver:
    """PyWin32-based driver for Windows API automation"""
    
    def __init__(self, hwnd, pid):
        self.hwnd = hwnd
        self.pid = pid
    
    def get(self, url):
        """Navigate to URL using Win32 API with enhanced URL typing"""
        try:
            # Bring window to front
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(1)
            
            # Send Ctrl+L to focus address bar
            win32api.keybd_event(0x11, 0, 0, 0)  # Ctrl down
            win32api.keybd_event(0x4C, 0, 0, 0)  # L down
            win32api.keybd_event(0x4C, 0, win32con.KEYEVENTF_KEYUP, 0)  # L up
            win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl up
            
            time.sleep(0.5)
            
            # Try different methods to type URL
            success = False
            methods = ['clipboard', 'win32']
            
            for method in methods:
                if type_url_safely(url, method):
                    success = True
                    break
                time.sleep(0.5)
            
            if not success:
                logger.error("All URL typing methods failed for Win32")
                return False
            
            # Press Enter
            time.sleep(0.5)
            win32api.keybd_event(0x0D, 0, 0, 0)  # Enter down
            win32api.keybd_event(0x0D, 0, win32con.KEYEVENTF_KEYUP, 0)  # Enter up
            
            time.sleep(3)
            logger.info(f"Navigated to {url} using PyWin32")
            return True
        except Exception as e:
            logger.error(f"Error navigating with PyWin32: {e}")
            return False
    
    def find_element_by_id(self, element_id):
        """Find element by ID using Win32 API"""
        return PyWin32Element(self, element_id)
    
    def save_screenshot(self, filename):
        """Save screenshot using Win32 API"""
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            logger.info(f"Screenshot saved: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return False
    
    def quit(self):
        """Close browser using Win32 API"""
        try:
            # Send Alt+F4
            win32api.keybd_event(0x12, 0, 0, 0)  # Alt down
            win32api.keybd_event(0x73, 0, 0, 0)  # F4 down
            win32api.keybd_event(0x73, 0, win32con.KEYEVENTF_KEYUP, 0)  # F4 up
            win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)  # Alt up
            
            time.sleep(2)
            logger.info("Browser closed using PyWin32")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

class PyWin32Element:
    """PyWin32 element wrapper"""
    
    def __init__(self, driver, element_id):
        self.driver = driver
        self.element_id = element_id
    
    def clear(self):
        """Clear element content"""
        try:
            # Select all and delete
            win32api.keybd_event(0x11, 0, 0, 0)  # Ctrl down
            win32api.keybd_event(0x41, 0, 0, 0)  # A down
            win32api.keybd_event(0x41, 0, win32con.KEYEVENTF_KEYUP, 0)  # A up
            win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl up
            
            time.sleep(0.2)
            
            win32api.keybd_event(0x2E, 0, 0, 0)  # Delete down
            win32api.keybd_event(0x2E, 0, win32con.KEYEVENTF_KEYUP, 0)  # Delete up
            
            return True
        except Exception as e:
            logger.error(f"Error clearing element: {e}")
            return False
    
    def send_keys(self, text):
        """Send keys to element"""
        try:
            # Try clipboard method first
            if type_url_safely(text, 'clipboard'):
                return True
            
            # Fallback to character-by-character
            for char in text:
                if char.isalnum():
                    vk_code = ord(char.upper())
                    win32api.keybd_event(vk_code, 0, 0, 0)
                    win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(random.uniform(0.1, 0.3))
            return True
        except Exception as e:
            logger.error(f"Error sending keys: {e}")
            return False
    
    def click(self):
        """Click element"""
        try:
            # Press Tab to navigate, then Enter
            win32api.keybd_event(0x09, 0, 0, 0)  # Tab down
            win32api.keybd_event(0x09, 0, win32con.KEYEVENTF_KEYUP, 0)  # Tab up
            time.sleep(0.5)
            
            win32api.keybd_event(0x0D, 0, 0, 0)  # Enter down
            win32api.keybd_event(0x0D, 0, win32con.KEYEVENTF_KEYUP, 0)  # Enter up
            
            return True
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False

def _add_human_behavior(driver):
    """Add human-like behavior patterns"""
    try:
        if hasattr(driver, 'execute_script'):
            # Random viewport adjustments for Selenium drivers
            driver.set_window_size(
                random.randint(1200, 1920),
                random.randint(800, 1080)
            )
            
            # Random mouse movement
            actions = ActionChains(driver)
            actions.move_by_offset(random.randint(10, 100), random.randint(10, 100))
            actions.perform()
        
        # Human-like delays
        time.sleep(random.uniform(2, 5))
        
    except Exception as e:
        logger.error(f"Human behavior simulation failed: {str(e)}")

def main_with_retry(url, email, pasw, vin, api_token, chat_id, max_retries=7):
    """Enhanced main function with fully intelligent system"""
    
    # Kill all Chrome instances before starting
    kill_all_chrome_instances()
    
    # Prioritize Selenium strategies for better control, then PyWin for stealth
    # strategies = [2, 3, 4, 1, 5, 6, 7]
    strategies = [6,7]
    
    for attempt in range(max_retries):
        strategy = strategies[attempt % len(strategies)]
        driver = None
        
        try:
            logger.info(f"Attempt {attempt + 1}: Using strategy {strategy}")
            
            # Kill Chrome instances before each strategy
            if attempt > 0:
                kill_all_chrome_instances()
            
            # Get initial browser with current strategy
            initial_driver = get_browser(headless=False, proxy=False, strategy=strategy)
            logger.info("initial_driver get_browser")
            
            if initial_driver is None:
                logger.warning("Failed to create initial driver")
                continue
            
            # For PyWinAuto/PyWin32, handle differently
            if strategy in [6, 7]:
                driver = initial_driver
                result = _perform_pywin_intelligent_scraping_enhanced(driver, vin, api_token, chat_id, url, email, pasw)
            else:
                # Use enhanced intelligent login function for Selenium drivers

                driver = handle_login_intelligently_enhanced(initial_driver, email, pasw)
                if driver is None:
                    logger.warning("Login failed, trying next strategy")
                    continue
                
                # Add human-like behavior
                _add_human_behavior(driver)
                
                # Perform enhanced intelligent VIN search
                if handle_vin_search_intelligently_enhanced(driver, vin):
                    result = handle_report_capture_intelligently_enhanced(driver, vin)
                else:
                    result = False
            
            if result:
                logger.info(f"Successfully completed with strategy {strategy}")
                return True
                
        except Exception as e:
            logger.error(f"Strategy {strategy} failed on attempt {attempt + 1}: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        # Wait before retry with exponential backoff
        wait_time = min((2 ** attempt) + random.uniform(1, 3), 30)  # Cap at 30 seconds
        logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
        time.sleep(wait_time)
    
    logger.error("All strategies failed")
    return False

def _perform_pywin_intelligent_scraping_enhanced(driver, vin, api_token, chat_id, url, email, pasw):
    """Enhanced PyWin scraping with better VIN field detection - FIXED"""
    try:
        logger.info("Starting enhanced PyWin intelligent scraping process")
        
        # Navigate to CARFAX and handle whatever page we land on
        if not driver.get("https://www.carfaxonline.com/"):
            return False
        
        time.sleep(random.uniform(5, 8))
        
        # Enhanced login logic (keeping existing login code but improving VIN detection)
        login_successful = _perform_enhanced_pywin_login(driver, email, pasw)
        
        if not login_successful:
            logger.error("Login failed for PyWin scraping")
            return False

      
        # Navigate to home page
        if not driver.get("https://www.carfaxonline.com/"):
            return False

     
        time.sleep(random.uniform(3, 5))
        
        # IMPROVED VIN input detection with better verification
        vin_entered = _enter_vin_with_enhanced_detection(driver, vin)
        
        if not vin_entered:
            logger.error("Could not enter and verify VIN at any location")
            return False
    
  
        # IMPROVED submit button detection
        submitted = _click_submit_with_enhanced_detection(driver)
        
        if not submitted:
            logger.info("Used Enter key as fallback for submit")
            pyautogui.press('enter')
        
        time.sleep(8)
        
        # Handle report generation and screenshot capture
        return _handle_pywin_intelligent_capture(driver, vin)
        
    except Exception as e:
        logger.error(f"PyWin intelligent scraping enhanced failed: {e}")
        return False

def _perform_enhanced_pywin_login(driver, email, pasw):
    """Enhanced PyWin login with better field detection and verification"""
    try:
        logger.info("Starting enhanced PyWin login process")
        
        # Take screenshot to analyze current state
        screenshot = pyautogui.screenshot()
        
        # Try multiple login approaches based on different possible page states
        login_attempts = [
            # Attempt 1: Look for email/password fields at common locations
            {'email_coords': [(400, 300), (500, 350), (450, 400)], 'password_offset': (0, 50)},
            # Attempt 2: Try different areas of the page
            {'email_coords': [(600, 300), (350, 450), (550, 380)], 'password_offset': (0, 40)},
            # Attempt 3: Try clicking login links first
            {'login_links': [(200, 100), (300, 150), (400, 200)], 'email_coords': [(400, 350)], 'password_offset': (0, 50)},
            # Attempt 4: Center-focused approach
            {'email_coords': [(960, 400), (683, 400), (800, 350)], 'password_offset': (0, 60)},
            # Attempt 5: Try common login form positions
            {'email_coords': [(500, 250), (600, 280), (700, 320)], 'password_offset': (0, 45)}
        ]
        
        login_successful = False
        
        for attempt_idx, attempt_config in enumerate(login_attempts):
            try:
                logger.info(f"Trying login attempt {attempt_idx + 1}")
                
                # Try clicking login links if specified
                if 'login_links' in attempt_config:
                    for link_x, link_y in attempt_config['login_links']:
                        try:
                            pyautogui.click(link_x, link_y)
                            time.sleep(2)
                            logger.info(f"Clicked potential login link at ({link_x}, {link_y})")
                        except Exception as e:
                            logger.warning(f"Failed to click login link at ({link_x}, {link_y}): {e}")
                
                # Try email input at different locations
                for email_x, email_y in attempt_config['email_coords']:
                    try:
                        logger.info(f"Trying email field at ({email_x}, {email_y})")
                        
                        # Click on potential email field
                        pyautogui.click(email_x, email_y)
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        # Test if this is an input field by typing a test character
                        pyautogui.typewrite('t')
                        time.sleep(0.2)
                        
                        # Check if character was entered
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.2)
                        pyautogui.hotkey('ctrl', 'c')
                        time.sleep(0.3)
                        
                        try:
                            win32clipboard.OpenClipboard()
                            test_content = win32clipboard.GetClipboardData()
                            win32clipboard.CloseClipboard()
                            
                            # If we got the test character back, this is likely an input field
                            if 't' in test_content.lower():
                                logger.info(f"Confirmed input field at ({email_x}, {email_y})")
                                
                                # Clear the test character
                                pyautogui.hotkey('ctrl', 'a')
                                time.sleep(0.2)
                                pyautogui.press('delete')
                                time.sleep(0.2)
                                
                                # Enter email with verification
                                email_entered = False
                                for method in ['clipboard', 'pyautogui']:
                                    if type_url_safely(email, method):
                                        time.sleep(0.5)
                                        
                                        # Verify by copying back the content
                                        pyautogui.hotkey('ctrl', 'a')
                                        time.sleep(0.2)
                                        pyautogui.hotkey('ctrl', 'c')
                                        time.sleep(0.5)
                                        
                                        try:
                                            win32clipboard.OpenClipboard()
                                            clipboard_content = win32clipboard.GetClipboardData()
                                            win32clipboard.CloseClipboard()
                                            
                                            if email.lower() in clipboard_content.lower():
                                                email_entered = True
                                                logger.info(f"Email verified successfully at ({email_x}, {email_y})")
                                                break
                                        except Exception as verify_error:
                                            logger.warning(f"Email verification failed: {verify_error}")
                                    
                                    if email_entered:
                                        break
                                
                                if not email_entered:
                                    logger.warning(f"Could not enter email at ({email_x}, {email_y})")
                                    continue
                                
                                # Move to password field
                                password_offset = attempt_config['password_offset']
                                password_x = email_x + password_offset[0]
                                password_y = email_y + password_offset[1]
                                
                                # Try Tab first to move to password field
                                pyautogui.press('tab')
                                time.sleep(0.5)
                                
                                # Verify we're in password field by typing a test character
                                pyautogui.typewrite('*')
                                time.sleep(0.2)
                                
                                # Check if we can see the character (shouldn't in password field)
                                pyautogui.hotkey('ctrl', 'a')
                                time.sleep(0.2)
                                pyautogui.hotkey('ctrl', 'c')
                                time.sleep(0.3)
                                
                                try:
                                    win32clipboard.OpenClipboard()
                                    pwd_test_content = win32clipboard.GetClipboardData()
                                    win32clipboard.CloseClipboard()
                                    
                                    # In password field, we might not see the character or see asterisks
                                    is_password_field = ('*' in pwd_test_content or len(pwd_test_content) == 0 or pwd_test_content == '*')
                                    
                                    if is_password_field:
                                        logger.info("Confirmed password field via Tab")
                                    else:
                                        # Try clicking password coordinates if Tab didn't work
                                        pyautogui.click(password_x, password_y)
                                        time.sleep(0.5)
                                        logger.info(f"Clicked password field at ({password_x}, {password_y})")
                                    
                                    # Clear any test characters
                                    pyautogui.hotkey('ctrl', 'a')
                                    time.sleep(0.2)
                                    pyautogui.press('delete')
                                    time.sleep(0.2)
                                    
                                    # Enter password
                                    password_entered = False
                                    for method in ['clipboard', 'pyautogui']:
                                        if type_url_safely(pasw, method):
                                            password_entered = True
                                            logger.info("Password entered successfully")
                                            break
                                    
                                    if not password_entered:
                                        logger.warning("Could not enter password")
                                        continue
                                    
                                    # If both email and password entered successfully, try to submit
                                    if email_entered and password_entered:
                                        logger.info("Both email and password entered, attempting login")
                                        
                                        # Try multiple submit methods
                                        submit_methods = [
                                            lambda: pyautogui.press('enter'),
                                            lambda: pyautogui.press('tab') or pyautogui.press('enter'),
                                            lambda: pyautogui.click(email_x + 100, email_y + 100),  # Click submit button area
                                            lambda: pyautogui.click(password_x + 100, password_y + 50)  # Another submit area
                                        ]
                                        
                                        for submit_method in submit_methods:
                                            try:
                                                submit_method()
                                                time.sleep(random.uniform(3, 5))
                                                
                                                # Check if login was successful by trying to navigate to home page
                                                if driver.get("https://www.carfaxonline.com/"):
                                                    time.sleep(3)
                                                    login_successful = True
                                                    logger.info("Login successful - reached home page")
                                                    break
                                            except Exception as submit_error:
                                                logger.warning(f"Submit method failed: {submit_error}")
                                                continue
                                        
                                        if login_successful:
                                            break
                                
                                except Exception as pwd_error:
                                    logger.warning(f"Password field verification failed: {pwd_error}")
                                    continue
                            else:
                                logger.warning(f"No input detected at ({email_x}, {email_y})")
                                continue
                                
                        except Exception as clipboard_error:
                            logger.warning(f"Clipboard test failed at ({email_x}, {email_y}): {clipboard_error}")
                            continue
                    
                    except Exception as e:
                        logger.warning(f"Login attempt failed at ({email_x}, {email_y}): {e}")
                        continue
                    
                    if login_successful:
                        break
                
                if login_successful:
                    break
                    
            except Exception as attempt_error:
                logger.warning(f"Login attempt configuration {attempt_idx + 1} failed: {attempt_error}")
                continue
        
        if login_successful:
            logger.info("Enhanced PyWin login completed successfully")
        else:
            logger.error("All enhanced PyWin login attempts failed")
        
        return login_successful
        
    except Exception as e:
        logger.error(f"Enhanced PyWin login failed: {e}")
        return False


def _enter_vin_with_enhanced_detection(driver, vin):
    """Enhanced VIN entry with better field detection"""
    try:
        # Take screenshot for analysis
        screenshot = pyautogui.screenshot()
        
        # More comprehensive VIN field locations based on common web layouts
        potential_vin_locations = [
            # Center area (most common for VIN fields)
            (960, 400), (960, 450), (960, 500),  # Assuming 1920x1080 screen
            (683, 400), (683, 450), (683, 500),  # For 1366x768 screen
            
            # Left-center area
            (400, 400), (450, 400), (500, 400),
            (400, 450), (450, 450), (500, 450),
            
            # Right-center area  
            (600, 400), (650, 400), (700, 400),
            (600, 450), (650, 450), (700, 450),
            
            # Upper center
            (500, 300), (550, 300), (600, 300),
            (500, 350), (550, 350), (600, 350),
        ]
        
        for x, y in potential_vin_locations:
            try:
                # Click on potential VIN field
                pyautogui.click(x, y)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Test if this is an input field by typing a test character
                pyautogui.typewrite('1')
                time.sleep(0.2)
                
                # Check if character was entered by selecting and copying
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.3)
                
                try:
                    win32clipboard.OpenClipboard()
                    clipboard_content = win32clipboard.GetClipboardData()
                    win32clipboard.CloseClipboard()
                    
                    # If we got the test character back, this is likely an input field
                    if '1' in clipboard_content:
                        logger.info(f"Found input field at ({x}, {y})")
                        
                        # Clear the test character and enter actual VIN
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.2)
                        pyautogui.press('delete')
                        time.sleep(0.2)
                        
                        # Enter VIN with verification
                        for method in ['clipboard', 'pyautogui']:
                            if type_url_safely(vin, method):
                                time.sleep(0.5)
                                
                                # Verify VIN was entered correctly
                                pyautogui.hotkey('ctrl', 'a')
                                time.sleep(0.2)
                                pyautogui.hotkey('ctrl', 'c')
                                time.sleep(0.5)
                                
                                try:
                                    win32clipboard.OpenClipboard()
                                    verify_content = win32clipboard.GetClipboardData()
                                    win32clipboard.CloseClipboard()
                                    
                                    if vin.upper() in verify_content.upper():
                                        logger.info(f"VIN verified successfully at ({x}, {y}): {vin}")
                                        return True
                                except:
                                    pass
                        
                except Exception as clipboard_error:
                    logger.warning(f"Clipboard verification failed at ({x}, {y}): {clipboard_error}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Failed to test input field at ({x}, {y}): {e}")
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"Enhanced VIN detection failed: {e}")
        return False

def _click_submit_with_enhanced_detection(driver):
    """Enhanced submit button detection"""
    try:
        # More comprehensive submit button locations
        potential_submit_locations = [
            # Common button positions relative to center
            (1060, 400), (1060, 450), (1060, 500),  # Right of center for 1920x1080
            (783, 400), (783, 450), (783, 500),     # Right of center for 1366x768
            
            # Below VIN field
            (960, 550), (683, 550), (500, 550),
            (960, 500), (683, 500), (500, 500),
            
            # Standard button positions
            (650, 400), (700, 400), (750, 400),
            (650, 450), (700, 450), (750, 450),
            (650, 500), (700, 500), (750, 500),
        ]
        
        for x, y in potential_submit_locations:
            try:
                # Take screenshot before clicking
                before_screenshot = pyautogui.screenshot()
                
                pyautogui.click(x, y)
                time.sleep(2)
                
                # Take screenshot after clicking to see if page changed
                after_screenshot = pyautogui.screenshot()
                
                # Simple comparison - if screenshots are different, button probably worked
                if before_screenshot.size == after_screenshot.size:
                    # Convert to numpy arrays for comparison
                    before_array = np.array(before_screenshot)
                    after_array = np.array(after_screenshot)
                    
                    # Calculate difference
                    diff = np.sum(np.abs(before_array - after_array))
                    
                    # If significant difference, button click was successful
                    if diff > 1000000:  # Threshold for page change
                        logger.info(f"Submit button clicked successfully at ({x}, {y})")
                        return True
                
            except Exception as e:
                logger.warning(f"Failed to click submit at ({x}, {y}): {e}")
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"Enhanced submit detection failed: {e}")
        return False


def _handle_pywin_intelligent_capture(driver, vin):
    """Handle intelligent report capture for PyWin drivers"""
    try:
        # Wait for report to load
        time.sleep(10)
        
        # Maximize window
        pyautogui.hotkey('alt', 'space')
        time.sleep(0.5)
        pyautogui.press('x')
        time.sleep(2)
        
        # Hide elements that shouldn't be printed using developer tools
        pyautogui.hotkey('ctrl', 'shift', 'i')  # Open dev tools
        time.sleep(2)
        
        # Type script to hide elements using safe method
        script = """
        var elementsToHide = ['.do-not-print', '.no-print', '.print-hide', '.back-to-top-button', '.ads'];
        elementsToHide.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function(el) { el.style.display = 'none'; });
        });
        """
        type_url_safely(script, 'clipboard')
        pyautogui.press('enter')
        time.sleep(1)
        
        # Close dev tools
        pyautogui.hotkey('ctrl', 'shift', 'i')
        time.sleep(1)
        
        # Intelligent screenshot capture
        counter = 1
        
        # Take first screenshot
        driver.save_screenshot(f'screenshots/Image_{counter}.png')
        counter += 1
        
        # Scroll and capture with intelligent stopping
        for i in range(25):  # Increased limit for longer reports
            pyautogui.scroll(-3)  # Scroll down
            time.sleep(3)  # Longer wait for content to settle
            
            driver.save_screenshot(f'screenshots/Image_{counter}.png')
            counter += 1
            
            # Intelligent stopping - check if we've reached the bottom
            # This is a simplified approach
            if i > 20:  # Reasonable limit for most reports
                break
        
        # Convert screenshots to PDF
        input_path = 'screenshots'
        output_path = f'PDF/{vin}.pdf'
        convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
        logger.info('PDF formatting completed')
        
        # Upload to S3
        upload_pdf_s3(output_path)
        
        # Clean up screenshots
        if os.path.exists("screenshots"):
            for filename in os.listdir("screenshots"):
                file_path = os.path.join("screenshots", filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        logger.info("PyWin intelligent report capture completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"PyWin intelligent report capture failed: {e}")
        return False

def _perform_intelligent_api_scraping(driver, vin, screenshot_name):
    """Perform API scraping with enhanced reCAPTCHA detection for CARFAX Online"""
    try:
        driver.implicitly_wait(30)
        logger.info("Starting API scraping process for CARFAX Online")
        
        # Ensure we're on the home page
        page_state = detect_page_state_advanced(driver)
        if page_state != 'home_page':
            driver.get("https://www.carfaxonline.com/")
            time.sleep(random.uniform(3, 5))
        
        # Add random delay before interaction
        time.sleep(random.uniform(2, 5))
        
        # Check for reCAPTCHA before proceeding
        wait_for_recaptcha_solution(driver)
        
        # Get home page elements
        home_elements = get_home_page_elements()
        
        # Find VIN input field with verification
        vin_input = find_element_with_verification(driver, [home_elements[0]])
        if not vin_input:
            logger.error("Could not find VIN input field for API")
            return False
        
        # Enter VIN with verification
        if not verify_text_input_with_retry(vin_input, vin):
            logger.error("Failed to enter VIN correctly for API")
            return False
        
        logger.info(f"API VIN '{vin}' entered and verified successfully")
        
        # Wait a moment before submitting
        time.sleep(random.uniform(1, 3))
        
        # Check for reCAPTCHA again
        wait_for_recaptcha_solution(driver)
        
        # Find and click submit button
        submit_button = find_element_with_verification(driver, [home_elements[1]])
        if not submit_button:
            logger.error("Could not find submit button for API")
            return False
        
        # Click submit button
        submit_button.click()
        logger.info("API Submit button clicked successfully")
        time.sleep(10)
        
        # Handle report capture for API
        return _handle_intelligent_api_capture(driver, vin, screenshot_name)
        
    except Exception as e:
        logger.error(f"API scraping failed: {str(e)}")
        return False

def _handle_intelligent_api_capture(driver, vin, screenshot_name):
    """Handle intelligent API report capture"""
    try:
        # Wait for report to load
        time.sleep(10)
        
        # Check if report opened in new window
        if len(driver.window_handles) > 1:
            logger.info("API report opened in new window")
            driver.switch_to.window(driver.window_handles[-1])
        
        # Verify we're on report page
        page_state = detect_page_state_advanced(driver)
        if page_state != 'report_page':
            logger.warning(f"Expected API report page, but got: {page_state}")
            # Continue anyway as report might still be loading
        
        # Wait for content intelligently
        wait = WebDriverWait(driver, 120)
        
        # Try to detect report content
        report_loaded = False
        report_indicators = [
            "//div[contains(@class, 'report')]",
            "//div[contains(text(), 'CARFAX Vehicle History Report')]",
            "//div[contains(text(), 'Vehicle History Report')]",
            "//*[contains(text(), 'This CARFAX Report')]",
            "//div[contains(@class, 'vehicle-history')]"
        ]
        
        for indicator in report_indicators:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                report_loaded = True
                logger.info(f"API Report loaded - found indicator: {indicator}")
                break
            except TimeoutException:
                continue
        
        if not report_loaded:
            logger.warning("API Report indicators not found, proceeding anyway")
            time.sleep(15)
        
        driver.maximize_window()
        time.sleep(4)
        
        # Hide print elements intelligently
        elements_to_hide = [
            '.do-not-print', '.no-print', '.print-hide', '.back-to-top-button',
            '.ads', '.advertisement', '.navigation', '.header-nav', '.footer'
        ]
        
        for element_selector in elements_to_hide:
            try:
                driver.execute_script(f"""
                    var elements = document.querySelectorAll('{element_selector}');
                    elements.forEach(function(el) {{ 
                        el.style.display = 'none'; 
                        el.style.visibility = 'hidden';
                    }});
                """)
            except Exception as e:
                logger.warning(f"Could not hide API elements with selector {element_selector}: {e}")
        
        # Get page dimensions intelligently
        try:
            height = driver.execute_script("""
                return Math.max(
                    document.body.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.clientHeight,
                    document.documentElement.scrollHeight,
                    document.documentElement.offsetHeight
                );
            """)
            scroll_height = driver.execute_script("return window.innerHeight")
        except:
            height = 8000
            scroll_height = 800
        
        logger.info(f"API page height: {height}")
        
        # Capture screenshots intelligently
        scroll_offset = 0
        counter = 1
        logger.info("Starting intelligent API screenshot capture")
        driver.save_screenshot(f'{screenshot_name}/Image_1.png')
        
        while scroll_offset < height - 200:
            scroll_offset += scroll_height - 150
            
            logger.info(f"API scrolling - offset: {scroll_offset}")
            driver.execute_script(f"window.scrollTo({{top: {scroll_offset}, behavior: 'smooth'}});")
            time.sleep(4)
            
            # Hide floating elements again after scroll
            for element_selector in elements_to_hide:
                try:
                    driver.execute_script(f"""
                        var elements = document.querySelectorAll('{element_selector}');
                        elements.forEach(function(el) {{ 
                            el.style.display = 'none'; 
                            el.style.visibility = 'hidden';
                        }});
                    """)
                except:
                    pass
            
            counter += 1
            driver.save_screenshot(f'{screenshot_name}/Image_{counter}.png')
            
            if counter > 35:  # Safety limit
                break
        
        # Convert to PDF and upload
        input_path = screenshot_name
        output_path = f'PDF_API/{vin}.pdf'
        convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
        logger.info('Intelligent API PDF formatting completed')
        upload_pdf_s3(output_path)
        
        # Clean up
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        
        # Clean screenshots directory
        if os.path.exists(screenshot_name):
            for filename in os.listdir(screenshot_name):
                file_path = os.path.join(screenshot_name, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        else:
            os.makedirs(screenshot_name)
        
        logger.info("Intelligent API scraping completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Intelligent API report capture failed: {e}")
        return False

def main_api_with_retry(url, email, pasw, vin, screenshot_name="screenshots_api", max_retries=7):
    """Enhanced main_api function with intelligent automation and Chrome management"""
    
    # Kill all Chrome instances before starting
    kill_all_chrome_instances()
    
    # Prioritize Selenium strategies for better control, then PyWin for stealth
    strategies = [2, 3, 4, 1, 5, 6, 7]
    
    for attempt in range(max_retries):
        strategy = strategies[attempt % len(strategies)]
        driver = None
        
        try:
            logger.info(f"API Attempt {attempt + 1}: Using strategy {strategy}")
            
            # Kill Chrome instances before each strategy
            if attempt > 0:
                kill_all_chrome_instances()
            
            initial_driver = get_browser(headless=False, proxy=False, strategy=strategy)
            
            if initial_driver is None:
                logger.warning("Failed to create initial driver for API")
                continue
            
            # For PyWinAuto/PyWin32, handle differently
            if strategy in [6, 7]:
                driver = initial_driver
                result = _perform_pywin_intelligent_api_scraping_enhanced(driver, vin, screenshot_name, url, email, pasw)
            else:
                # Use intelligent login function for Selenium drivers
                driver = handle_login_intelligently_enhanced(initial_driver, email, pasw)
                if driver is None:
                    logger.warning("API Login failed, trying next strategy")
                    continue
                
                # Add human-like behavior
                _add_human_behavior(driver)
                
                # Perform intelligent API scraping
                result = _perform_intelligent_api_scraping(driver, vin, screenshot_name)
            
            if result:
                logger.info(f"API completed successfully with strategy {strategy}")
                return True
                
        except Exception as e:
            logger.error(f"API Strategy {strategy} failed on attempt {attempt + 1}: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        # Wait before retry with exponential backoff
        wait_time = min((2 ** attempt) + random.uniform(1, 3), 30)  # Cap at 30 seconds
        logger.info(f"API waiting {wait_time:.2f} seconds before retry...")
        time.sleep(wait_time)
    
    logger.error("All API strategies failed")
    return False

def _perform_pywin_intelligent_api_scraping_enhanced(driver, vin, screenshot_name, url, email, pasw):
    """Enhanced API scraping using PyWinAuto/PyWin32 drivers with field verification"""
    try:
        logger.info("Starting enhanced PyWin API scraping process")
        
        # Use the same enhanced login logic as main scraping
        if not driver.get("https://www.carfaxonline.com/"):
            return False
        
        time.sleep(random.uniform(3, 5))
        
        # Reuse the enhanced login logic from main scraping
        login_attempts = [
            {'email_coords': [(400, 300), (500, 350), (450, 400)], 'password_offset': (0, 50)},
            {'email_coords': [(600, 300), (350, 450), (550, 380)], 'password_offset': (0, 40)},
            {'login_links': [(200, 100), (300, 150), (400, 200)], 'email_coords': [(400, 350)], 'password_offset': (0, 50)}
        ]
        
        login_successful = False
        
        for attempt_config in login_attempts:
            try:
                if 'login_links' in attempt_config:
                    for link_x, link_y in attempt_config['login_links']:
                        pyautogui.click(link_x, link_y)
                        time.sleep(2)
                
                for email_x, email_y in attempt_config['email_coords']:
                    try:
                        pyautogui.click(email_x, email_y)
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.2)
                        
                        # Verify email input
                        email_entered = False
                        for method in ['clipboard', 'pyautogui']:
                            if type_url_safely(email, method):
                                time.sleep(0.5)
                                
                                pyautogui.hotkey('ctrl', 'a')
                                time.sleep(0.2)
                                pyautogui.hotkey('ctrl', 'c')
                                time.sleep(0.5)
                                
                                try:
                                    win32clipboard.OpenClipboard()
                                    clipboard_content = win32clipboard.GetClipboardData()
                                    win32clipboard.CloseClipboard()
                                    
                                    if email.lower() in clipboard_content.lower():
                                        email_entered = True
                                        logger.info(f"API Email verified at ({email_x}, {email_y})")
                                        break
                                except:
                                    pass
                            
                            if email_entered:
                                break
                        
                        if not email_entered:
                            continue
                        
                        # Password entry with verification
                        password_offset = attempt_config['password_offset']
                        password_x = email_x + password_offset[0]
                        password_y = email_y + password_offset[1]
                        
                        pyautogui.press('tab')
                        time.sleep(0.5)
                        
                        password_entered = False
                        for method in ['clipboard', 'pyautogui']:
                            if type_url_safely(pasw, method):
                                password_entered = True
                                logger.info("API Password entered successfully")
                                break
                        
                        if email_entered and password_entered:
                            pyautogui.press('enter')
                            time.sleep(random.uniform(5, 8))
                            
                            if driver.get("https://www.carfaxonline.com/"):
                                time.sleep(3)
                                login_successful = True
                                logger.info("API Login successful")
                                break
                    
                    except Exception as e:
                        logger.warning(f"API Login attempt failed at ({email_x}, {email_y}): {e}")
                        continue
                
                if login_successful:
                    break
                    
            except Exception as attempt_error:
                logger.warning(f"API Login attempt configuration failed: {attempt_error}")
                continue
        
        # Navigate to home page
        if not driver.get("https://www.carfaxonline.com/"):
            return False
        
        time.sleep(random.uniform(3, 5))
        
        # VIN entry with verification (same as main scraping)
        potential_vin_locations = [
            (500, 400), (600, 350), (450, 450), (550, 380), (400, 420), (520, 410)
        ]
        
        vin_entered = False
        for x, y in potential_vin_locations:
            try:
                pyautogui.click(x, y)
                time.sleep(random.uniform(0.5, 1.0))
                
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                pyautogui.press('delete')
                time.sleep(0.2)
                
                for method in ['clipboard', 'pyautogui']:
                    if type_url_safely(vin, method):
                        time.sleep(0.5)
                        
                        # Verify VIN input
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.2)
                        pyautogui.hotkey('ctrl', 'c')
                        time.sleep(0.5)
                        
                        try:
                            win32clipboard.OpenClipboard()
                            clipboard_content = win32clipboard.GetClipboardData()
                            win32clipboard.CloseClipboard()
                            
                            if vin.upper() in clipboard_content.upper():
                                vin_entered = True
                                logger.info(f"API VIN verified at ({x}, {y}): {vin}")
                                break
                        except:
                            pass
                
                if vin_entered:
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to enter API VIN at ({x}, {y}): {e}")
                continue
        
        if not vin_entered:
            logger.error("Could not enter and verify API VIN at any location")
            return False
        
        time.sleep(random.uniform(1, 2))
        
        # Submit button clicking (same as main scraping)
        potential_submit_locations = [
            (650, 400), (500, 450), (600, 420), (700, 380), (550, 480), (580, 440)
        ]
        
        submitted = False
        for x, y in potential_submit_locations:
            try:
                pyautogui.click(x, y)
                time.sleep(3)
                submitted = True
                logger.info(f"API Submit button clicked at ({x}, {y})")
                break
            except Exception as e:
                logger.warning(f"Failed to click API submit at ({x}, {y}): {e}")
                continue
        
        if not submitted:
            pyautogui.press('enter')
            logger.info("Used Enter key as fallback for API submit")
        
        time.sleep(10)
        
        # Handle report generation and screenshot capture
        return _handle_pywin_intelligent_api_capture(driver, vin, screenshot_name)
        
    except Exception as e:
        logger.error(f"PyWin intelligent API scraping enhanced failed: {e}")
        return False

def _handle_pywin_intelligent_api_capture(driver, vin, screenshot_name):
    """Handle intelligent API report capture for PyWin drivers"""
    try:
        # Wait for report to load
        time.sleep(10)
        
        # Maximize window
        pyautogui.hotkey('alt', 'space')
        time.sleep(0.5)
        pyautogui.press('x')
        time.sleep(2)
        
        # Hide elements that shouldn't be printed
        pyautogui.hotkey('ctrl', 'shift', 'i')  # Open dev tools
        time.sleep(2)
        
        script = """
        var elementsToHide = ['.do-not-print', '.no-print', '.print-hide', '.back-to-top-button', '.ads'];
        elementsToHide.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function(el) { el.style.display = 'none'; });
        });
        """
        type_url_safely(script, 'clipboard')
        pyautogui.press('enter')
        time.sleep(1)
        
        # Close dev tools
        pyautogui.hotkey('ctrl', 'shift', 'i')
        time.sleep(2)
        
        # Capture screenshots
        counter = 1
        
        # Take first screenshot
        driver.save_screenshot(f'{screenshot_name}/Image_1.png')
        counter += 1
        
        # Scroll and capture
        for i in range(25):  # Increased limit for longer reports
            pyautogui.scroll(-3)  # Scroll down
            time.sleep(4)
            
            driver.save_screenshot(f'{screenshot_name}/Image_{counter}.png')
            counter += 1
            
            # Check if we've reached the bottom
            if i > 20:  # Reasonable limit
                break
        
        # Convert screenshots to PDF
        input_path = screenshot_name
        output_path = f'PDF_API/{vin}.pdf'
        convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
        logger.info('API PDF formatting completed')
        
        # Upload to S3
        upload_pdf_s3(output_path)
        
        # Clean up screenshots
        if os.path.exists(screenshot_name):
            for filename in os.listdir(screenshot_name):
                file_path = os.path.join(screenshot_name, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        else:
            os.makedirs(screenshot_name)
        
        logger.info("PyWin intelligent API report capture completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"PyWin intelligent API report capture failed: {e}")
        return False

def _perform_intelligent_api_scraping(driver, vin, screenshot_name):
    """Perform API scraping with enhanced reCAPTCHA detection for CARFAX Online"""
    try:
        driver.implicitly_wait(30)
        logger.info("Starting API scraping process for CARFAX Online")
        
        # Ensure we're on the home page
        page_state = detect_page_state_advanced(driver)
        if page_state != 'home_page':
            driver.get("https://www.carfaxonline.com/")
            time.sleep(random.uniform(3, 5))
        
        # Add random delay before interaction
        time.sleep(random.uniform(2, 5))
        
        # Check for reCAPTCHA before proceeding
        wait_for_recaptcha_solution(driver)
        
        # Get home page elements
        home_elements = get_home_page_elements()
        
        # Find VIN input field with verification
        vin_input = find_element_with_verification(driver, [home_elements[0]])
        if not vin_input:
            logger.error("Could not find VIN input field for API")
            return False
        
        # Enter VIN with verification
        if not verify_text_input_with_retry(vin_input, vin):
            logger.error("Failed to enter VIN correctly for API")
            return False
        
        logger.info(f"API VIN '{vin}' entered and verified successfully")
        
        # Wait a moment before submitting
        time.sleep(random.uniform(1, 3))
        
        # Check for reCAPTCHA again
        wait_for_recaptcha_solution(driver)
        
        # Find and click submit button
        submit_button = find_element_with_verification(driver, [home_elements[1]])
        if not submit_button:
            logger.error("Could not find submit button for API")
            return False
        
        # Click submit button
        submit_button.click()
        logger.info("API Submit button clicked successfully")
        time.sleep(10)
        
        # Handle report capture for API
        return _handle_intelligent_api_capture(driver, vin, screenshot_name)
        
    except Exception as e:
        logger.error(f"API scraping failed: {str(e)}")
        return False

def _handle_intelligent_api_capture(driver, vin, screenshot_name):
    """Handle intelligent API report capture"""
    try:
        # Wait for report to load
        time.sleep(10)
        
        # Check if report opened in new window
        if len(driver.window_handles) > 1:
            logger.info("API report opened in new window")
            driver.switch_to.window(driver.window_handles[-1])
        
        # Verify we're on report page
        page_state = detect_page_state_advanced(driver)
        if page_state != 'report_page':
            logger.warning(f"Expected API report page, but got: {page_state}")
            # Continue anyway as report might still be loading
        
        # Wait for content intelligently
        wait = WebDriverWait(driver, 120)
        
        # Try to detect report content
        report_loaded = False
        report_indicators = [
            "//div[contains(@class, 'report')]",
            "//div[contains(text(), 'CARFAX Vehicle History Report')]",
            "//div[contains(text(), 'Vehicle History Report')]",
            "//*[contains(text(), 'This CARFAX Report')]",
            "//div[contains(@class, 'vehicle-history')]"
        ]
        
        for indicator in report_indicators:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                report_loaded = True
                logger.info(f"API Report loaded - found indicator: {indicator}")
                break
            except TimeoutException:
                continue
        
        if not report_loaded:
            logger.warning("API Report indicators not found, proceeding anyway")
            time.sleep(15)
        
        driver.maximize_window()
        time.sleep(4)
        
        # Hide print elements intelligently
        elements_to_hide = [
            '.do-not-print', '.no-print', '.print-hide', '.back-to-top-button',
            '.ads', '.advertisement', '.navigation', '.header-nav', '.footer'
        ]
        
        for element_selector in elements_to_hide:
            try:
                driver.execute_script(f"""
                    var elements = document.querySelectorAll('{element_selector}');
                    elements.forEach(function(el) {{ 
                        el.style.display = 'none'; 
                        el.style.visibility = 'hidden';
                    }});
                """)
            except Exception as e:
                logger.warning(f"Could not hide API elements with selector {element_selector}: {e}")
        
        # Get page dimensions intelligently
        try:
            height = driver.execute_script("""
                return Math.max(
                    document.body.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.clientHeight,
                    document.documentElement.scrollHeight,
                    document.documentElement.offsetHeight
                );
            """)
            scroll_height = driver.execute_script("return window.innerHeight")
        except:
            height = 8000
            scroll_height = 800
        
        logger.info(f"API page height: {height}")
        
        # Capture screenshots intelligently
        scroll_offset = 0
        counter = 1
        logger.info("Starting intelligent API screenshot capture")
        driver.save_screenshot(f'{screenshot_name}/Image_1.png')
        
        while scroll_offset < height - 200:
            scroll_offset += scroll_height - 150
            
            logger.info(f"API scrolling - offset: {scroll_offset}")
            driver.execute_script(f"window.scrollTo({{top: {scroll_offset}, behavior: 'smooth'}});")
            time.sleep(4)
            
            # Hide floating elements again after scroll
            for element_selector in elements_to_hide:
                try:
                    driver.execute_script(f"""
                        var elements = document.querySelectorAll('{element_selector}');
                        elements.forEach(function(el) {{ 
                            el.style.display = 'none'; 
                            el.style.visibility = 'hidden';
                        }});
                    """)
                except:
                    pass
            
            counter += 1
            driver.save_screenshot(f'{screenshot_name}/Image_{counter}.png')
            
            if counter > 35:  # Safety limit
                break
        
        # Convert to PDF and upload
        input_path = screenshot_name
        output_path = f'PDF_API/{vin}.pdf'
        convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
        logger.info('Intelligent API PDF formatting completed')
        upload_pdf_s3(output_path)
        
        # Clean up
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        
        # Clean screenshots directory
        if os.path.exists(screenshot_name):
            for filename in os.listdir(screenshot_name):
                file_path = os.path.join(screenshot_name, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        else:
            os.makedirs(screenshot_name)
        
        logger.info("Intelligent API scraping completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Intelligent API report capture failed: {e}")
        return False

# Legacy function for backward compatibility
def main(url, email, pasw, vin, api_token, chat_id, driver):
    """Legacy main function - redirects to enhanced version"""
    return main_with_retry(url, email, pasw, vin, api_token, chat_id)

def main_api(url, email, pasw, vin, driver, screenshot_name="screenshots_api"):
    """Legacy main_api function - redirects to enhanced version"""
    return main_api_with_retry(url, email, pasw, vin, screenshot_name)

if __name__ == '__main__':
    try:
        vin = input('Enter VIN Number: ').strip()
        if not vin:
            logger.error("No VIN provided")
            sys.exit(1)
        
        logger.info(f"Starting fully intelligent enhanced automation for VIN: {vin}")
        
        success = main_with_retry(
            url='https://www.carfaxonline.com/', 
            email=email, 
            pasw=pasw, 
            vin=vin, 
            api_token=apiToken, 
            chat_id=chatID
        )
        
        if success:
            logger.info("Successfully completed with fully intelligent enhanced anti-detection!")
            print("Successfully completed!")
        else:
            logger.error("All intelligent enhanced strategies failed")
            print("All strategies failed. Please check your setup.")
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {e}")
        print(f"Unexpected error: {e}")

