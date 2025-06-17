import os, json
import undetected_chromedriver as uc
from selenium_stealth import stealth
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
from src.Tele import SendPdf, TryAgainMsg
from src.img import convert_folder_to_pdf
from src.s3_connection import upload_pdf_s3
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
from seleniumwire import webdriver as wire_driver

if not os.path.exists('PDF'):
    os.mkdir('PDF')

if not os.path.exists('PDF_API'):
    os.mkdir('PDF_API')

with open('Config.json', 'r') as f:
    config = json.load(f)

url = config['url']
email = config['email']
pasw = config['password']
apiToken = '6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE'
chatID = '5491808070'

download_directory = os.path.join(os.getcwd(), 'PDF')

def get_browser(headless=False, proxy=False, strategy=1):
    """
    Enhanced browser setup with multiple anti-detection strategies
    Strategy 1: Undetected ChromeDriver
    Strategy 2: Selenium Stealth
    Strategy 3: Manual Fortification
    Strategy 4: Proxy Rotation
    Strategy 5: Hybrid Approach
    """
    
    # User agents pool for rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    ]
    
    # Proxy pool (add your proxies here)
    proxies = [
        # "http://proxy1:port",
        # "http://proxy2:port",
        # Add your residential proxies here
    ]
    
    try:
        if strategy == 1:
            return _get_undetected_browser(headless, proxy, user_agents, proxies)
        elif strategy == 2:
            return _get_stealth_browser(headless, proxy, user_agents, proxies)
        elif strategy == 3:
            return _get_fortified_browser(headless, proxy, user_agents, proxies)
        elif strategy == 4:
            return _get_proxy_rotated_browser(headless, proxy, user_agents, proxies)
        else:
            return _get_hybrid_browser(headless, proxy, user_agents, proxies)
            
    except Exception as e:
        print(f"Strategy {strategy} failed: {str(e)}")
        return None

def _get_undetected_browser(headless, proxy, user_agents, proxies):
    """Strategy 1: Undetected ChromeDriver approach"""
    options = uc.ChromeOptions()
    
    # Basic stealth options
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins-discovery')
    options.add_argument('--disable-web-security')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--log-level=3')
    options.page_load_strategy = "none"
    options.add_argument('--ignore-certificate-errors-spki-list')
    
    # Random user agent
    options.add_argument(f'--user-agent={random.choice(user_agents)}')
    
    # Window size randomization
    window_sizes = ['1366,768', '1920,1080', '1440,900', '1536,864']
    options.add_argument(f'--window-size={random.choice(window_sizes)}')
    options.add_argument("--force-device-scale-factor=1")
    
    # Image loading preferences
    prefs = {"profile.managed_default_content_settings.images": 1}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    
    if headless:
        options.add_argument('--headless=new')
    
    # Proxy setup
    if proxy and proxies:
        selected_proxy = random.choice(proxies)
        options.add_argument(f'--proxy-server={selected_proxy}')
    
    # Create driver with undetected chromedriver
    driver = uc.Chrome(options=options, use_subprocess=False)
    
    # Additional JavaScript execution to hide automation
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def _get_stealth_browser(headless, proxy, user_agents, proxies):
    """Strategy 2: Selenium Stealth approach"""
    options = Options()
    
    # Anti-detection options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--log-level=3')
    options.page_load_strategy = "none"
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument("--disable-web-security")
    options.add_argument("--force-device-scale-factor=1")
    
    # Image loading preferences
    prefs = {"profile.managed_default_content_settings.images": 1}
    options.add_experimental_option("prefs", prefs)
    
    # Random user agent
    user_agent = random.choice(user_agents)
    options.add_argument(f'--user-agent={user_agent}')
    
    # Random window size
    window_sizes = ['1366,768', '1920,1080', '1440,900', '1536,864']
    options.add_argument(f'--window-size={random.choice(window_sizes)}')
    
    if headless:
        options.add_argument('--headless=new')
    
    # Proxy setup
    if proxy and proxies:
        selected_proxy = random.choice(proxies)
        options.add_argument(f'--proxy-server={selected_proxy}')
    
    # Create driver
    path = ChromeDriverManager().install()
    path = path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver.exe")
    service = Service(executable_path=path)
    driver = webdriver.Chrome(service=service, options=options)
    
    # Apply stealth settings
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            webdriver=False)
    
    return driver

def _get_fortified_browser(headless, proxy, user_agents, proxies):
    """Strategy 3: Manual fortification approach"""
    options = Options()
    
    # Comprehensive anti-detection
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--log-level=3')
    options.page_load_strategy = "none"
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument("--force-device-scale-factor=1")
    
    # Image loading preferences
    prefs = {"profile.managed_default_content_settings.images": 1}
    options.add_experimental_option("prefs", prefs)
    
    # Randomize user agent and window size
    options.add_argument(f'--user-agent={random.choice(user_agents)}')
    window_sizes = ['1366,768', '1920,1080', '1440,900', '1536,864']
    options.add_argument(f'--window-size={random.choice(window_sizes)}')
    
    if headless:
        options.add_argument('--headless=new')
    
    if proxy and proxies:
        selected_proxy = random.choice(proxies)
        options.add_argument(f'--proxy-server={selected_proxy}')
    
    path = ChromeDriverManager().install()
    path = path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver.exe")
    service = Service(executable_path=path)
    driver = webdriver.Chrome(service=service, options=options)
    
    # Execute anti-detection scripts
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
    
    return driver

def _get_proxy_rotated_browser(headless, proxy, user_agents, proxies):
    """Strategy 4: Focus on proxy rotation"""
    try: 
        # Selenium-wire for advanced proxy handling
        seleniumwire_options = {}
        
        if proxy and proxies:
            selected_proxy = random.choice(proxies)
            seleniumwire_options = {
                'proxy': {
                    'http': selected_proxy,
                    'https': selected_proxy,
                }
            }
        
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        options.add_argument('--log-level=3')
        options.page_load_strategy = "none"
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument("--force-device-scale-factor=1")
        
        # Image loading preferences
        prefs = {"profile.managed_default_content_settings.images": 1}
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        
        if headless:
            options.add_argument('--headless=new')
        
        driver = wire_driver.Chrome(
            seleniumwire_options=seleniumwire_options,
            options=options
        )
        
        return driver
    except ImportError:
        # Fallback to regular Chrome if selenium-wire not available
        return _get_fortified_browser(headless, proxy, user_agents, proxies)

def _get_hybrid_browser(headless, proxy, user_agents, proxies):
    """Strategy 5: Hybrid approach combining multiple techniques"""
    try:
        return _get_undetected_browser(headless, proxy, user_agents, proxies)
    except:
        try:
            return _get_stealth_browser(headless, proxy, user_agents, proxies)
        except:
            return _get_fortified_browser(headless, proxy, user_agents, proxies)

def _add_human_behavior(driver):
    """Add human-like behavior patterns"""
    try:
        actions = ActionChains(driver)
        
        # Simulate human-like delays
        time.sleep(random.uniform(2, 5))
        
        # Random viewport adjustments
        driver.set_window_size(
            random.randint(1200, 1920),
            random.randint(800, 1080)
        )
        
        # Random mouse movement
        try:
            actions.move_by_offset(random.randint(10, 100), random.randint(10, 100))
            actions.perform()
        except:
            pass
    except Exception as e:
        print(f"Human behavior simulation failed: {str(e)}")

def _perform_login(driver, url, email, pasw):
    """Perform login with enhanced error handling and proper CarfaxOnline.com authentication"""
    try:
        print("Navigating to login page...")
        driver.get(url)
        
        # Add random delay to simulate human behavior
        time.sleep(random.uniform(3, 7))
        
        # Wait for page to load completely
        driver.implicitly_wait(10)
        
        # Check if we're already logged in by looking for logout elements or user dashboard
        try:
            # Look for elements that indicate we're already logged in
            logged_in_indicator = driver.find_element(By.XPATH, "//a[contains(@href, 'logout') or contains(text(), 'Logout') or contains(text(), 'Dashboard')]")
            if logged_in_indicator:
                print("Already logged in, skipping login process...")
                return True
        except:
            # Not logged in, proceed with login
            pass
        
        # Look for login form elements - try multiple possible selectors
        email_field = None
        password_field = None
        login_button = None
        
        # Try to find email/username field with various selectors
        email_selectors = [
            "//input[@type='email']",
            "//input[@name='email']",
            "//input[@id='email']",
            "//input[@name='username']",
            "//input[@id='username']",
            "//input[@placeholder='Email']",
            "//input[@placeholder='Username']",
            "//input[contains(@class, 'email')]",
            "//input[contains(@class, 'username')]"
        ]
        
        for selector in email_selectors:
            try:
                email_field = driver.find_element(By.XPATH, selector)
                print(f"Found email field with selector: {selector}")
                break
            except:
                continue
        
        # Try to find password field with various selectors
        password_selectors = [
            "//input[@type='password']",
            "//input[@name='password']",
            "//input[@id='password']",
            "//input[@placeholder='Password']",
            "//input[contains(@class, 'password')]"
        ]
        
        for selector in password_selectors:
            try:
                password_field = driver.find_element(By.XPATH, selector)
                print(f"Found password field with selector: {selector}")
                break
            except:
                continue
        
        # Try to find login button with various selectors
        login_selectors = [
            "//button[@type='submit']",
            "//input[@type='submit']",
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'Sign In')]",
            "//input[@value='Login']",
            "//input[@value='Sign In']",
            "//button[contains(@class, 'login')]",
            "//button[contains(@class, 'signin')]",
            "//a[contains(@class, 'login')]"
        ]
        
        for selector in login_selectors:
            try:
                login_button = driver.find_element(By.XPATH, selector)
                print(f"Found login button with selector: {selector}")
                break
            except:
                continue
        
        # Check if we found all required elements
        if not email_field:
            print("Could not find email/username field")
            return False
        
        if not password_field:
            print("Could not find password field")
            return False
        
        if not login_button:
            print("Could not find login button")
            return False
        
        # Clear fields and enter credentials with human-like typing
        print("Clearing and filling email field...")
        email_field.clear()
        time.sleep(random.uniform(0.5, 1.5))
        
        # Type email with human-like speed
        for char in email:
            email_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(random.uniform(1, 2))
        
        print("Clearing and filling password field...")
        password_field.clear()
        time.sleep(random.uniform(0.5, 1.5))
        
        # Type password with human-like speed
        for char in pasw:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(random.uniform(1, 3))
        
        # Click login button
        print("Clicking login button...")
        driver.execute_script("arguments[0].click();", login_button)
        
        # Wait for login to process
        time.sleep(random.uniform(3, 6))
        
        # Verify login success by checking for various indicators
        login_success = False
        
        # Check for successful login indicators
        success_indicators = [
            "//a[contains(@href, 'logout')]",
            "//a[contains(text(), 'Logout')]",
            "//div[contains(@class, 'dashboard')]",
            "//div[contains(@class, 'user')]",
            "//span[contains(@class, 'username')]",
            "//div[contains(@class, 'profile')]"
        ]
        
        for indicator in success_indicators:
            try:
                element = driver.find_element(By.XPATH, indicator)
                if element:
                    print(f"Login success detected with indicator: {indicator}")
                    login_success = True
                    break
            except:
                continue
        
        # Alternative check: see if we're redirected away from login page
        if not login_success:
            current_url = driver.current_url.lower()
            if 'login' not in current_url and 'signin' not in current_url:
                print("Login appears successful - redirected away from login page")
                login_success = True
        
        # Check for error messages
        error_selectors = [
            "//div[contains(@class, 'error')]",
            "//div[contains(@class, 'alert')]",
            "//span[contains(@class, 'error')]",
            "//p[contains(@class, 'error')]",
            "//div[contains(text(), 'Invalid')]",
            "//div[contains(text(), 'incorrect')]",
            "//div[contains(text(), 'failed')]"
        ]
        
        for selector in error_selectors:
            try:
                error_element = driver.find_element(By.XPATH, selector)
                if error_element and error_element.is_displayed():
                    print(f"Login error detected: {error_element.text}")
                    return False
            except:
                continue
        
        if login_success:
            print("Login completed successfully!")
            return True
        else:
            print("Login status unclear, assuming success...")
            return True
        
    except Exception as e:
        print(f"Login failed with exception: {str(e)}")
        
        # Try to take a screenshot for debugging
        try:
            driver.save_screenshot(f'login_error_{int(time.time())}.png')
            print("Screenshot saved for debugging")
        except:
            pass
        
        return False

        
    except Exception as e:
        print(f"Login failed: {str(e)}")
        return False

def main_with_retry(url, email, pasw, vin, api_token, chat_id, max_retries=5):
    """Enhanced main function with retry logic and multiple strategies"""
    
    strategies = [1, 2, 3, 4, 5]  # All available strategies
    
    for attempt in range(max_retries):
        strategy = strategies[attempt % len(strategies)]
        driver = None
        
        try:
            print(f"Attempt {attempt + 1}: Using strategy {strategy}")
            
            # Get browser with current strategy
            driver = get_browser(headless=False, proxy=False, strategy=strategy)
            
            if driver is None:
                continue
            
            # Add human-like behavior
            _add_human_behavior(driver)
            
            # Login first
            success = _perform_login(driver, url, email, pasw)
            if not success:
                continue
            
            # Perform main scraping with your existing logic
            result = _perform_main_scraping(driver, vin, api_token, chat_id)
            
            if result:
                return True
                
        except Exception as e:
            print(f"Strategy {strategy} failed on attempt {attempt + 1}: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        # Wait before retry with exponential backoff
        wait_time = (2 ** attempt) + random.uniform(1, 3)
        print(f"Waiting {wait_time:.2f} seconds before retry...")
        time.sleep(wait_time)
    
    return False

def _perform_main_scraping(driver, vin, api_token, chat_id):
    """Perform the main scraping with your existing logic"""
    driver.implicitly_wait(30)
    try:
        print("scraping vin search page....")
        
        # Add random delay before interaction
        time.sleep(random.uniform(2, 5))
        
        vin_input = driver.find_element(By.ID, 'vin')
        vin_input.clear()
        
        # Type with human-like speed
        for char in vin:
            vin_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        time.sleep(random.uniform(1, 3))
        
        submit = driver.find_element(By.ID, 'run_vhr_button')
        driver.execute_script("arguments[0].click();", submit)
        sleep(8)
        
        if len(driver.window_handles) > 1:
            print("inside if condition")
            driver.switch_to.window(driver.window_handles[1])
            
            print("web driver wait")
            wait = WebDriverWait(driver, 120)
            print("web driver wait for t seconds")
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "report-header-print-button")))
            print("executing script")

            driver.execute_script("document.querySelector('.do-not-print').style.display='none';")
            time.sleep(1)
            driver.maximize_window()
            time.sleep(3)
            
            width = driver.execute_script("return Math.max(document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth);")
            height = driver.execute_script("return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
            print("width: ", width)
            print("height:", height)

            window_size = driver.get_window_size()
            print(f"Browser window size: Width = {window_size['width']}, Height = {window_size['height']}")
            
            scroll_height = driver.execute_script("return window.innerHeight")
            print('scroll_height: ', scroll_height)

            try:
                driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
            except Exception as e:
                print("no back to top button")

            scroll_offset = 0
            counter = 1
            print("saving screenshot")
            driver.save_screenshot('screenshots/Image_1.png')
            
            while scroll_offset-150 < (height):
                try:
                    driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
                except Exception as e:
                    print("no back to top button")
                
                print("running while")
                driver.execute_script(f"window.scrollTo(0, {scroll_offset})")
                sleep(3)
                driver.save_screenshot(f'screenshots/Image_{counter}.png')
                scroll_offset += scroll_height - 30
                counter += 1

            input_path = 'screenshots'
            output_path = 'PDF/' + vin + '.pdf'
            convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
            print('Pdf Formatting...')
            upload_pdf_s3(output_path)
            
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(1)
            driver.maximize_window()
            
            if os.path.exists("screenshots"):
                for filename in os.listdir("screenshots"):
                    file_path = os.path.join("screenshots", filename)
                    os.remove(file_path)
            else:
                os.makedirs("screenshots")
            return True
        else:
            print('Nothing found...')
            TryAgainMsg(chat_id=chat_id, bot_token=api_token)
            return False
        
    except Exception as e:
        print("exception: ", str(e))
        return False

def main_api_with_retry(url, email, pasw, vin, screenshot_name="screenshots_api", max_retries=5):
    """Enhanced main_api function with retry logic and multiple strategies"""
    
    strategies = [1, 2, 3, 4, 5]
    
    for attempt in range(max_retries):
        strategy = strategies[attempt % len(strategies)]
        driver = None
        
        try:
            print(f"API Attempt {attempt + 1}: Using strategy {strategy}")
            
            driver = get_browser(headless=False, proxy=False, strategy=strategy)
            
            if driver is None:
                continue
            
            _add_human_behavior(driver)
            
            success = _perform_login(driver, url, email, pasw)
            if not success:
                continue
            
            result = _perform_api_scraping(driver, vin, screenshot_name)
            
            if result:
                return True
                
        except Exception as e:
            print(f"API Strategy {strategy} failed on attempt {attempt + 1}: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        wait_time = (2 ** attempt) + random.uniform(1, 3)
        print(f"Waiting {wait_time:.2f} seconds before retry...")
        time.sleep(wait_time)
    
    return False

def _perform_api_scraping(driver, vin, screenshot_name):
    """Perform API scraping with your existing logic"""
    driver.implicitly_wait(30)
    try:
        print("scraping vin search page....")
        
        time.sleep(random.uniform(2, 5))
        
        vin_input = driver.find_element(By.ID, 'vin')
        vin_input.clear()
        
        # Human-like typing
        for char in vin:
            vin_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        submit = driver.find_element(By.ID, 'run_vhr_button')
        driver.execute_script("arguments[0].click();", submit)
        sleep(10)
        
        if len(driver.window_handles) > 1:
            print("inside if condition")
            driver.switch_to.window(driver.window_handles[len(driver.window_handles)-1])
            
            print("web driver wait")
            wait = WebDriverWait(driver, 120)
            print("web driver wait for t seconds")
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "report-header-print-button")))
            print("executing script")

            driver.execute_script("document.querySelector('.do-not-print').style.display='none';")
            time.sleep(2)
            driver.maximize_window()
            time.sleep(4)

            width = driver.execute_script("return Math.max(document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth);")
            height = driver.execute_script("return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
            print("width: ", width)
            print("height:", height)
            
            scroll_height = driver.execute_script("return window.innerHeight")

            try:
                driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
            except Exception as e:
                print("no back to top button")

            scroll_offset = 0
            counter = 1
            print("saving screenshot")
            driver.save_screenshot(f'{screenshot_name}/Image_1.png')
            
            while scroll_offset-150 < (height):
                try:
                    driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
                except Exception as e:
                    print("no back to top button")
            
                print("running while")
                driver.execute_script(f"window.scrollTo(0, {scroll_offset})")
                sleep(4)
                driver.save_screenshot(f'{screenshot_name}/Image_{counter}.png')
                scroll_offset += scroll_height - 30
                counter += 1

            input_path = screenshot_name
            output_path = 'PDF_API/' + vin + '.pdf'
            convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
            print('Pdf Formatting...')
            upload_pdf_s3(output_path)
            
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(1)
            driver.maximize_window()
            
            if os.path.exists(screenshot_name):
                for filename in os.listdir(screenshot_name):
                    file_path = os.path.join(screenshot_name, filename)
                    os.remove(file_path)
            else:
                os.makedirs(screenshot_name)
            return True
        else:
            print('Nothing found...')
            return False
            
    except Exception as e:
        print("exception: ", str(e))
        return False

# Legacy function for backward compatibility
def main(url, email, pasw, vin, api_token, chat_id, driver):
    """Legacy main function - redirects to enhanced version"""
    return main_with_retry(url, email, pasw, vin, api_token, chat_id)

def main_api(url, email, pasw, vin, driver, screenshot_name="screenshots_api"):
    """Legacy main_api function - redirects to enhanced version"""
    return main_api_with_retry(url, email, pasw, vin, screenshot_name)

if __name__ == '__main__':
    vin = input('Enter Vin Number: ').strip()
    success = main_with_retry(
        url='https://www.carfaxonline.com/', 
        email=email, 
        pasw=pasw, 
        vin=vin, 
        api_token=apiToken, 
        chat_id=chatID
    )
    
    if success:
        print("Successfully completed!")
    else:
        print("All strategies failed. Please check your setup.")
