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
import shutil
import glob
import psutil
import logging

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_debug.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Create directories
directories = ['PDF', 'PDF_API', 'screenshots']
for directory in directories:
    if not os.path.exists(directory):
        os.mkdir(directory)
        logger.info(f"Created directory: {directory}")

# Load configuration
try:
    with open('Config.json', 'r') as f:
        config = json.load(f)
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

url = config['url']
email = config['email']
pasw = config['password']
apiToken = '6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE'
chatID = '5491808070'

download_directory = os.path.join(os.getcwd(), 'PDF')
logger.info(f"Configuration loaded - URL: {url}, Email: {email}")

def kill_chrome_processes():
    """Kill all Chrome processes to avoid profile conflicts"""
    logger.info("Starting Chrome process cleanup...")
    try:
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] in ['chrome.exe', 'chromedriver.exe']:
                try:
                    proc.kill()
                    logger.debug(f"Killed Chrome process: {proc.info['pid']} ({proc.info['name']})")
                    killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"Could not kill process {proc.info['pid']}: {e}")
        
        if killed_count > 0:
            logger.info(f"Successfully killed {killed_count} Chrome processes")
            time.sleep(2)
        else:
            logger.info("No Chrome processes found to kill")
            
    except Exception as e:
        logger.error(f"Error during Chrome process cleanup: {e}")

def get_chrome_profile_path():
    """Get Chrome profile path for Profile 2"""
    logger.debug("Determining Chrome profile path...")
    username = "Administrator"
    base_path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"
    logger.info(f"Chrome profile base path: {base_path}")
    
    if os.path.exists(base_path):
        logger.info("Chrome profile directory exists")
    else:
        logger.warning(f"Chrome profile directory not found: {base_path}")
    
    return base_path

def get_profile_2_path():
    """Get Profile 2 path directly"""
    logger.info("Setting up Chrome Profile 2...")
    base_path = get_chrome_profile_path()
    
    if not os.path.exists(base_path):
        logger.error(f"Chrome user data directory not found: {base_path}")
        return None, None
    
    profile_2_path = os.path.join(base_path, "Profile 2")
    if os.path.exists(profile_2_path):
        logger.info("Profile 2 found and will be used")
        return base_path, "Profile 2"
    else:
        logger.warning("Profile 2 not found, falling back to Default profile")
        default_path = os.path.join(base_path, "Default")
        if os.path.exists(default_path):
            return base_path, "Default"
        else:
            logger.error("Neither Profile 2 nor Default profile found")
            return None, None

def detect_recaptcha(driver):
    """Detect reCAPTCHA presence on the page"""
    logger.debug("Scanning page for reCAPTCHA elements...")
    try:
        # Check for reCAPTCHA iframe
        recaptcha_iframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha"]')
        if len(recaptcha_iframes) > 0:
            logger.warning(f"reCAPTCHA detected! Found {len(recaptcha_iframes)} reCAPTCHA iframes")
            return True
        
        # Check for hCaptcha
        hcaptcha_iframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="hcaptcha"]')
        if len(hcaptcha_iframes) > 0:
            logger.warning(f"hCAPTCHA detected! Found {len(hcaptcha_iframes)} hCAPTCHA iframes")
            return True
        
        # Check for common CAPTCHA elements
        captcha_selectors = [
            'div.rc-anchor', 'div.g-recaptcha', '#captcha_image',
            '//*[contains(text(), "CAPTCHA")]', '//*[contains(text(), "verify")]'
        ]
        
        for selector in captcha_selectors:
            try:
                if selector.startswith('//'):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.warning(f"CAPTCHA element found with selector: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"Error checking selector {selector}: {e}")
        
        logger.debug("No reCAPTCHA elements detected")
        return False
        
    except Exception as e:
        logger.error(f"Error during reCAPTCHA detection: {e}")
        return False

def wait_for_recaptcha_solution(driver, timeout=30):
    """Wait for human to solve reCAPTCHA"""
    print("reCAPTCHA found")
    logger.warning(f"reCAPTCHA detected! Waiting {timeout} seconds for manual solution...")
    
    start_time = time.time()
    check_interval = 2
    
    while time.time() - start_time < timeout:
        if not detect_recaptcha(driver):
            elapsed = time.time() - start_time
            logger.info(f"reCAPTCHA solved in {elapsed:.1f} seconds! Continuing...")
            return True
        
        remaining = timeout - (time.time() - start_time)
        logger.debug(f"Still waiting for reCAPTCHA solution... {remaining:.0f}s remaining")
        time.sleep(check_interval)
    
    logger.error(f"Timeout after {timeout} seconds waiting for reCAPTCHA solution")
    return False

def clean_chromedriver_cache():
    """Clean and refresh ChromeDriver cache"""
    logger.info("Cleaning ChromeDriver cache...")
    try:
        cache_dir = os.path.expanduser("~/.wdm")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            logger.info("ChromeDriver cache cleared successfully")
        else:
            logger.info("No ChromeDriver cache found to clear")
    except Exception as e:
        logger.error(f"Error clearing ChromeDriver cache: {e}")

def get_fresh_chromedriver():
    """Get a fresh ChromeDriver installation with correct path"""
    logger.info("Obtaining fresh ChromeDriver...")
    try:
        clean_chromedriver_cache()
        
        initial_path = ChromeDriverManager().install()
        logger.info(f"ChromeDriverManager returned: {initial_path}")
        
        if "THIRD_PARTY_NOTICES.chromedriver" in initial_path:
            logger.info("Detected incorrect path, searching for actual chromedriver.exe...")
            driver_dir = os.path.dirname(initial_path)
            logger.debug(f"Searching in directory: {driver_dir}")
            
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
                logger.debug(f"Glob pattern {pattern} found: {matches}")
            
            for path in possible_paths:
                if os.path.exists(path) and os.path.isfile(path):
                    logger.info(f"Found valid ChromeDriver at: {path}")
                    return path
        
        if os.path.exists(initial_path) and os.path.isfile(initial_path):
            logger.info(f"Using initial ChromeDriver path: {initial_path}")
            return initial_path
        
        logger.error("Could not find valid ChromeDriver executable")
        return None
        
    except Exception as e:
        logger.error(f"Error obtaining ChromeDriver: {e}")
        return None

def get_browser(headless=False, proxy=False, strategy=1):
    """Enhanced browser setup with Profile 2 and speed optimizations"""
    logger.info(f"Creating browser instance using strategy {strategy}")
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    
    try:
        if strategy == 1:
            logger.info("Using strategy 1: Undetected ChromeDriver")
            return _get_undetected_browser_fast(headless, proxy, user_agents)
        elif strategy == 2:
            logger.info("Using strategy 2: Selenium Stealth")
            return _get_stealth_browser_fast(headless, proxy, user_agents)
        elif strategy == 3:
            logger.info("Using strategy 3: Fortified Browser")
            return _get_fortified_browser_fast(headless, proxy, user_agents)
        elif strategy == 4:
            logger.info("Using strategy 4: Basic Browser")
            return _get_basic_browser_fast(headless, proxy, user_agents)
        else:
            logger.info("Using strategy 5: Hybrid Browser")
            return _get_hybrid_browser_fast(headless, proxy, user_agents)
            
    except Exception as e:
        logger.error(f"Strategy {strategy} failed with error: {str(e)}")
        return None

def _get_stealth_browser_fast(headless, proxy, user_agents):
    """Strategy 2: Fast Selenium Stealth with Profile 2 - FIXED DevTools issue"""
    logger.info("Initializing stealth browser with Profile 2...")
    
    # Kill existing Chrome processes first
    kill_chrome_processes()
    
    options = Options()
    
    # FIXED: Prevent DevTools hanging
    options.add_argument('--remote-debugging-port=0')
    logger.debug("Added remote debugging port disable to prevent hanging")
    
    # Use Profile 2 directly
    profile_base, profile_dir = get_profile_2_path()
    if profile_base and profile_dir:
        options.add_argument(f'--user-data-dir={profile_base}')
        options.add_argument(f'--profile-directory={profile_dir}')
        logger.info(f"Configured to use Chrome profile: {profile_dir}")
    else:
        logger.warning("No profile configured, using default Chrome settings")
    
    # SPEED OPTIMIZATIONS
    speed_prefs = {
        "profile.managed_default_content_settings.images": 2,  # Block images
        "profile.default_content_setting_values.notifications": 2,  # Block notifications
        "profile.managed_default_content_settings.stylesheets": 2,  # Block CSS
        "profile.managed_default_content_settings.javascript": 1,  # Allow JS (needed)
        "profile.managed_default_content_settings.media_stream": 2,  # Block media
    }
    options.add_experimental_option("prefs", speed_prefs)
    logger.debug("Applied speed optimization preferences")
    
    # Essential Chrome arguments
    chrome_args = [
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--log-level=3',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-gpu',
        '--disable-features=TranslateUI',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows'
    ]
    
    for arg in chrome_args:
        options.add_argument(arg)
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    selected_user_agent = random.choice(user_agents)
    options.add_argument(f'--user-agent={selected_user_agent}')
    options.add_argument('--window-size=1920,1080')
    logger.debug(f"Using user agent: {selected_user_agent}")
    
    if headless:
        options.add_argument('--headless=new')
        logger.info("Running in headless mode")
    
    chromedriver_path = get_fresh_chromedriver()
    if not chromedriver_path:
        logger.error("Failed to obtain ChromeDriver path")
        raise Exception("Could not get valid ChromeDriver path")
    
    logger.info(f"Using ChromeDriver at: {chromedriver_path}")
    service = Service(executable_path=chromedriver_path)
    
    logger.info("Starting Chrome browser...")
    start_time = time.time()
    driver = webdriver.Chrome(service=service, options=options)
    browser_start_time = time.time() - start_time
    logger.info(f"Chrome browser started in {browser_start_time:.2f} seconds")
    
    # Apply stealth settings
    logger.info("Applying stealth configuration...")
    stealth_start = time.time()
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            webdriver=False)
    stealth_time = time.time() - stealth_start
    logger.info(f"Stealth configuration applied in {stealth_time:.2f} seconds")
    
    logger.info("Stealth browser created successfully")
    return driver

def _get_basic_browser_fast(headless, proxy, user_agents):
    """Strategy 4: Fast Basic Chrome with Profile 2 - FIXED DevTools issue"""
    logger.info("Initializing basic browser with Profile 2...")
    
    kill_chrome_processes()
    
    options = Options()
    
    # FIXED: Prevent DevTools hanging
    options.add_argument('--remote-debugging-port=0')
    logger.debug("Added remote debugging port disable to prevent hanging")
    
    # Use Profile 2 directly
    profile_base, profile_dir = get_profile_2_path()
    if profile_base and profile_dir:
        options.add_argument(f'--user-data-dir={profile_base}')
        options.add_argument(f'--profile-directory={profile_dir}')
        logger.info(f"Configured to use Chrome profile: {profile_dir}")
    
    # Speed optimizations
    speed_prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", speed_prefs)
    
    # Minimal options for speed
    basic_args = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--log-level=3',
        '--disable-extensions',
        '--disable-gpu'
    ]
    
    for arg in basic_args:
        options.add_argument(arg)
    
    selected_user_agent = random.choice(user_agents)
    options.add_argument(f'--user-agent={selected_user_agent}')
    logger.debug(f"Using user agent: {selected_user_agent}")
    
    if headless:
        options.add_argument('--headless=new')
        logger.info("Running in headless mode")
    
    chromedriver_path = get_fresh_chromedriver()
    if not chromedriver_path:
        logger.error("Failed to obtain ChromeDriver path")
        raise Exception("Could not get valid ChromeDriver path")
    
    service = Service(executable_path=chromedriver_path)
    
    logger.info("Starting basic Chrome browser...")
    start_time = time.time()
    driver = webdriver.Chrome(service=service, options=options)
    browser_start_time = time.time() - start_time
    logger.info(f"Basic browser started in {browser_start_time:.2f} seconds")
    
    return driver

def _get_undetected_browser_fast(headless, proxy, user_agents):
    """Strategy 1: Fast Undetected ChromeDriver with Profile 2 - FIXED DevTools issue"""
    logger.info("Initializing undetected browser with Profile 2...")
    
    kill_chrome_processes()
    
    options = uc.ChromeOptions()
    
    # FIXED: Prevent DevTools hanging
    options.add_argument('--remote-debugging-port=0')
    logger.debug("Added remote debugging port disable to prevent hanging")
    
    # Use Profile 2 directly
    profile_base, profile_dir = get_profile_2_path()
    if profile_base and profile_dir:
        options.add_argument(f'--user-data-dir={profile_base}')
        options.add_argument(f'--profile-directory={profile_dir}')
        logger.info(f"Configured to use Chrome profile: {profile_dir}")
    
    # Speed optimizations
    speed_prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", speed_prefs)
    
    # Minimal options for undetected chromedriver
    undetected_args = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled',
        '--log-level=3',
        '--disable-extensions',
        '--disable-gpu'
    ]
    
    for arg in undetected_args:
        options.add_argument(arg)
    
    selected_user_agent = random.choice(user_agents)
    options.add_argument(f'--user-agent={selected_user_agent}')
    logger.debug(f"Using user agent: {selected_user_agent}")
    
    if headless:
        options.add_argument('--headless=new')
        logger.info("Running in headless mode")
    
    logger.info("Starting undetected Chrome browser...")
    start_time = time.time()
    driver = uc.Chrome(options=options, use_subprocess=False, version_main=None)
    browser_start_time = time.time() - start_time
    logger.info(f"Undetected browser started in {browser_start_time:.2f} seconds")
    
    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        logger.debug("Applied webdriver property hiding")
    except Exception as e:
        logger.warning(f"Could not apply webdriver hiding: {e}")
    
    return driver

def _get_fortified_browser_fast(headless, proxy, user_agents):
    """Strategy 3: Fast Manual fortification with Profile 2 - FIXED DevTools issue"""
    logger.info("Initializing fortified browser with Profile 2...")
    
    kill_chrome_processes()
    
    options = Options()
    
    # FIXED: Prevent DevTools hanging
    options.add_argument('--remote-debugging-port=0')
    logger.debug("Added remote debugging port disable to prevent hanging")
    
    # Use Profile 2 directly
    profile_base, profile_dir = get_profile_2_path()
    if profile_base and profile_dir:
        options.add_argument(f'--user-data-dir={profile_base}')
        options.add_argument(f'--profile-directory={profile_dir}')
        logger.info(f"Configured to use Chrome profile: {profile_dir}")
    
    # Speed optimizations
    speed_prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", speed_prefs)
    
    # Fortification arguments
    fortified_args = [
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--log-level=3',
        '--disable-extensions',
        '--disable-gpu'
    ]
    
    for arg in fortified_args:
        options.add_argument(arg)
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    selected_user_agent = random.choice(user_agents)
    options.add_argument(f'--user-agent={selected_user_agent}')
    logger.debug(f"Using user agent: {selected_user_agent}")
    
    if headless:
        options.add_argument('--headless=new')
        logger.info("Running in headless mode")
    
    chromedriver_path = get_fresh_chromedriver()
    if not chromedriver_path:
        logger.error("Failed to obtain ChromeDriver path")
        raise Exception("Could not get valid ChromeDriver path")
    
    service = Service(executable_path=chromedriver_path)
    
    logger.info("Starting fortified Chrome browser...")
    start_time = time.time()
    driver = webdriver.Chrome(service=service, options=options)
    browser_start_time = time.time() - start_time
    logger.info(f"Fortified browser started in {browser_start_time:.2f} seconds")
    
    try:
        # Apply fortification scripts
        fortification_scripts = [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})"
        ]
        
        for script in fortification_scripts:
            driver.execute_script(script)
        
        logger.debug("Applied fortification scripts successfully")
    except Exception as e:
        logger.warning(f"Could not apply fortification scripts: {e}")
    
    return driver

def _get_hybrid_browser_fast(headless, proxy, user_agents):
    """Strategy 5: Fast Hybrid approach with fallback"""
    logger.info("Attempting hybrid browser creation with fallback strategies...")
    
    strategies = [
        ("basic", _get_basic_browser_fast),
        ("stealth", _get_stealth_browser_fast),
        ("undetected", _get_undetected_browser_fast)
    ]
    
    for strategy_name, strategy_func in strategies:
        try:
            logger.info(f"Trying {strategy_name} strategy in hybrid mode...")
            return strategy_func(headless, proxy, user_agents)
        except Exception as e:
            logger.warning(f"Hybrid {strategy_name} strategy failed: {e}")
            continue
    
    logger.error("All hybrid strategies failed")
    raise Exception("All hybrid browser creation strategies failed")

def _add_human_behavior(driver):
    """Add minimal human-like behavior for speed"""
    logger.debug("Applying human-like behavior patterns...")
    try:
        # Reduced delay for speed
        delay = random.uniform(0.5, 1.5)
        logger.debug(f"Adding {delay:.2f}s human delay")
        time.sleep(delay)
        
        # Set consistent window size for speed
        driver.set_window_size(1920, 1080)
        logger.debug("Set window size to 1920x1080")
        
    except Exception as e:
        logger.error(f"Human behavior simulation failed: {str(e)}")

def _perform_login(driver, url, email, pasw):
    """Use existing login script with comprehensive logging"""
    logger.info("=== STARTING LOGIN PROCESS ===")
    try:
        if driver:
            logger.info("Closing initial driver before login...")
            driver.quit()
        
        logger.info("Importing login script module...")
        from src.login_script import login
        
        logger.info("Calling login function from login_script.py...")
        login_start_time = time.time()
        authenticated_driver = login(quit=False, headless=False)
        login_duration = time.time() - login_start_time
        
        if authenticated_driver is None:
            logger.error("Login function returned None - authentication failed")
            return None
        
        logger.info(f"Login completed successfully in {login_duration:.2f} seconds")
        
        # Check for reCAPTCHA after login
        logger.info("Checking for reCAPTCHA after login...")
        if detect_recaptcha(authenticated_driver):
            logger.warning("reCAPTCHA detected after login")
            if wait_for_recaptcha_solution(authenticated_driver):
                logger.info("reCAPTCHA solved successfully")
            else:
                logger.error("reCAPTCHA solution timeout")
        else:
            logger.info("No reCAPTCHA detected after login")
        
        logger.info("=== LOGIN PROCESS COMPLETED ===")
        return authenticated_driver
        
    except Exception as e:
        logger.error(f"Login process failed with exception: {str(e)}")
        logger.error("=== LOGIN PROCESS FAILED ===")
        return None

def main_with_retry(url, email, pasw, vin, api_token, chat_id, max_retries=3):
    """Enhanced main function with comprehensive logging"""
    logger.info(f"=== STARTING MAIN RETRY PROCESS FOR VIN: {vin} ===")
    logger.info(f"User: {chat_id}, Max retries: {max_retries}")
    
    strategies = [2, 4, 3, 1, 5]  # Start with fastest strategies
    
    for attempt in range(max_retries):
        strategy = strategies[attempt % len(strategies)]
        driver = None
        
        try:
            logger.info(f"--- Attempt {attempt + 1}/{max_retries}: Using strategy {strategy} ---")
            
            browser_start_time = time.time()
            initial_driver = get_browser(headless=False, proxy=False, strategy=strategy)
            browser_creation_time = time.time() - browser_start_time
            
            if initial_driver is None:
                logger.error(f"Strategy {strategy} failed to create browser")
                continue
            
            logger.info(f"Browser created in {browser_creation_time:.2f}s, proceeding to login...")
            
            login_start_time = time.time()
            driver = _perform_login(initial_driver, url, email, pasw)
            login_time = time.time() - login_start_time
            
            if driver is None:
                logger.error(f"Login failed for strategy {strategy} after {login_time:.2f}s")
                continue
            
            logger.info(f"Login successful in {login_time:.2f}s, adding human behavior...")
            _add_human_behavior(driver)
            
            logger.info("Starting main scraping process...")
            scraping_start_time = time.time()
            result = _perform_main_scraping(driver, vin, api_token, chat_id)
            scraping_time = time.time() - scraping_start_time
            
            if result:
                total_time = time.time() - browser_start_time
                logger.info(f"=== SUCCESS: VIN {vin} processed in {total_time:.2f}s total ===")
                logger.info(f"Breakdown - Browser: {browser_creation_time:.1f}s, Login: {login_time:.1f}s, Scraping: {scraping_time:.1f}s")
                return True
            else:
                logger.warning(f"Scraping failed for VIN {vin} with strategy {strategy}")
                
        except Exception as e:
            logger.error(f"Strategy {strategy} failed on attempt {attempt + 1}: {str(e)}")
            
        finally:
            if driver:
                try:
                    logger.debug("Cleaning up driver...")
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error during driver cleanup: {e}")
        
        if attempt < max_retries - 1:  # Don't wait after last attempt
            wait_time = min(2 ** attempt, 10) + random.uniform(0.5, 1.5)
            logger.info(f"Waiting {wait_time:.2f} seconds before next attempt...")
            time.sleep(wait_time)
    
    logger.error(f"=== FAILURE: All {max_retries} attempts failed for VIN: {vin} ===")
    return False

def _perform_main_scraping(driver, vin, api_token, chat_id):
    """Perform the main scraping with comprehensive logging"""
    logger.info(f"=== STARTING MAIN SCRAPING FOR VIN: {vin} ===")
    driver.implicitly_wait(10)
    
    try:
        # Check for reCAPTCHA before starting
        logger.info("Pre-scraping reCAPTCHA check...")
        if detect_recaptcha(driver):
            logger.warning("reCAPTCHA detected before scraping")
            if not wait_for_recaptcha_solution(driver):
                logger.error("Failed to solve reCAPTCHA before scraping")
                return False
        
        logger.info("Navigating to VIN input...")
        time.sleep(random.uniform(1, 2))
        
        try:
            vin_input = driver.find_element(By.ID, 'vin')
            logger.info("VIN input field found successfully")
        except Exception as e:
            logger.error(f"Could not find VIN input field: {e}")
            return False
        
        vin_input.clear()
        logger.info(f"Entering VIN: {vin}")
        
        # Type VIN with human-like speed
        for i, char in enumerate(vin):
            vin_input.send_keys(char)
            if i % 3 == 0:  # Log progress every 3 characters
                logger.debug(f"VIN input progress: {i+1}/{len(vin)} characters")
            time.sleep(random.uniform(0.05, 0.1))
        
        logger.info("VIN entered successfully")
        time.sleep(random.uniform(0.5, 1))
        
        try:
            submit = driver.find_element(By.ID, 'run_vhr_button')
            logger.info("Submit button found, clicking...")
            driver.execute_script("arguments[0].click();", submit)
            logger.info("Submit button clicked successfully")
        except Exception as e:
            logger.error(f"Could not find or click submit button: {e}")
            return False
        
        logger.info("Waiting for page response...")
        sleep(5)
        
        # Check for reCAPTCHA after form submission
        logger.info("Post-submission reCAPTCHA check...")
        if detect_recaptcha(driver):
            logger.warning("reCAPTCHA detected after form submission")
            if not wait_for_recaptcha_solution(driver):
                logger.error("Failed to solve reCAPTCHA after submission")
                return False
        
        window_count = len(driver.window_handles)
        logger.info(f"Current window count: {window_count}")
        
        if window_count > 1:
            logger.info("New window detected, switching to report window...")
            driver.switch_to.window(driver.window_handles[1])
            logger.info("Successfully switched to report window")
            
            # Check for reCAPTCHA in new window
            logger.info("Checking for reCAPTCHA in report window...")
            if detect_recaptcha(driver):
                logger.warning("reCAPTCHA detected in report window")
                if not wait_for_recaptcha_solution(driver):
                    logger.error("Failed to solve reCAPTCHA in report window")
                    return False
            
            logger.info("Waiting for report to fully load...")
            try:
                wait = WebDriverWait(driver, 60)
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "report-header-print-button")))
                logger.info("Report loaded successfully - print button is clickable")
            except Exception as e:
                logger.error(f"Report failed to load within timeout: {e}")
                return False

            logger.info("Preparing page for screenshot capture...")
            try:
                driver.execute_script("document.querySelector('.do-not-print').style.display='none';")
                logger.debug("Hidden do-not-print elements")
            except Exception as e:
                logger.debug(f"No do-not-print elements found: {e}")
            
            time.sleep(0.5)
            driver.maximize_window()
            logger.info("Window maximized")
            time.sleep(1)
            
            logger.info("Calculating page dimensions...")
            width = driver.execute_script("return Math.max(document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth);")
            height = driver.execute_script("return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
            scroll_height = driver.execute_script("return window.innerHeight")
            
            logger.info(f"Page dimensions - Width: {width}px, Height: {height}px, Scroll height: {scroll_height}px")

            try:
                driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
                logger.debug("Hidden back-to-top button")
            except Exception as e:
                logger.debug("No back-to-top button found")

            # Screenshot capture process
            logger.info("Starting screenshot capture process...")
            scroll_offset = 0
            counter = 1
            estimated_screenshots = max(1, int(height / (scroll_height - 30)) + 1)
            logger.info(f"Estimated {estimated_screenshots} screenshots needed")
            
            screenshot_start_time = time.time()
            driver.save_screenshot('screenshots/Image_1.png')
            logger.debug("Captured initial screenshot")
            
            while scroll_offset - 150 < height:
                try:
                    driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
                except:
                    pass
                
                logger.debug(f"Capturing screenshot {counter} at scroll offset {scroll_offset}")
                driver.execute_script(f"window.scrollTo(0, {scroll_offset})")
                sleep(1.5)
                driver.save_screenshot(f'screenshots/Image_{counter}.png')
                scroll_offset += scroll_height - 30
                counter += 1
                
                if counter % 5 == 0:  # Progress update every 5 screenshots
                    progress = min(100, (scroll_offset / height) * 100)
                    logger.info(f"Screenshot progress: {progress:.1f}% ({counter-1} screenshots)")

            screenshot_time = time.time() - screenshot_start_time
            total_screenshots = counter - 1
            logger.info(f"Screenshot capture completed: {total_screenshots} screenshots in {screenshot_time:.2f}s")

            logger.info("Converting screenshots to PDF...")
            pdf_start_time = time.time()
            input_path = 'screenshots'
            output_path = 'PDF/' + vin + '.pdf'
            
            try:
                convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
                pdf_creation_time = time.time() - pdf_start_time
                logger.info(f'PDF created successfully in {pdf_creation_time:.2f}s')
            except Exception as e:
                logger.error(f"PDF creation failed: {e}")
                return False
            
            logger.info('Uploading PDF to S3...')
            upload_start_time = time.time()
            try:
                upload_pdf_s3(output_path)
                upload_time = time.time() - upload_start_time
                logger.info(f'PDF uploaded to S3 successfully in {upload_time:.2f}s')
            except Exception as e:
                logger.error(f"S3 upload failed: {e}")
                return False
            
            logger.info("Cleaning up browser windows...")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(0.5)
            driver.maximize_window()
            
            logger.info("Cleaning up screenshot files...")
            cleanup_count = 0
            if os.path.exists("screenshots"):
                for filename in os.listdir("screenshots"):
                    file_path = os.path.join("screenshots", filename)
                    try:
                        os.remove(file_path)
                        cleanup_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove {file_path}: {e}")
                logger.info(f"Cleaned up {cleanup_count} screenshot files")
            else:
                os.makedirs("screenshots")
                logger.info("Created screenshots directory")
            
            logger.info(f"=== MAIN SCRAPING COMPLETED SUCCESSFULLY FOR VIN: {vin} ===")
            return True
            
        else:
            logger.warning('No new window detected - no report available')
            logger.info("Sending try again message to user...")
            try:
                TryAgainMsg(chat_id=chat_id, bot_token=api_token)
                logger.info("Try again message sent successfully")
            except Exception as e:
                logger.error(f"Failed to send try again message: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Main scraping failed with exception: {str(e)}")
        logger.error(f"=== MAIN SCRAPING FAILED FOR VIN: {vin} ===")
        return False

def main_api_with_retry(url, email, pasw, vin, screenshot_name="screenshots_api", max_retries=3):
    """Enhanced main_api function with comprehensive logging"""
    logger.info(f"=== STARTING API RETRY PROCESS FOR VIN: {vin} ===")
    logger.info(f"Screenshot directory: {screenshot_name}, Max retries: {max_retries}")
    
    strategies = [2, 4, 3, 1, 5]
    
    for attempt in range(max_retries):
        strategy = strategies[attempt % len(strategies)]
        driver = None
        
        try:
            logger.info(f"--- API Attempt {attempt + 1}/{max_retries}: Using strategy {strategy} ---")
            
            initial_driver = get_browser(headless=False, proxy=False, strategy=strategy)
            
            if initial_driver is None:
                logger.error(f"API strategy {strategy} failed to create browser")
                continue
            
            driver = _perform_login(initial_driver, url, email, pasw)
            if driver is None:
                logger.error(f"API login failed for strategy {strategy}")
                continue
            
            _add_human_behavior(driver)
            
            result = _perform_api_scraping(driver, vin, screenshot_name)
            
            if result:
                logger.info(f"=== API SUCCESS: VIN {vin} processed successfully ===")
                return True
            else:
                logger.warning(f"API scraping failed for VIN {vin} with strategy {strategy}")
                
        except Exception as e:
            logger.error(f"API Strategy {strategy} failed on attempt {attempt + 1}: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error during API driver cleanup: {e}")
        
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 8) + random.uniform(0.5, 1)
            logger.info(f"Waiting {wait_time:.2f} seconds before next API attempt...")
            time.sleep(wait_time)
    
    logger.error(f"=== API FAILURE: All {max_retries} attempts failed for VIN: {vin} ===")
    return False

def _perform_api_scraping(driver, vin, screenshot_name):
    """Perform API scraping with comprehensive logging"""
    logger.info(f"=== STARTING API SCRAPING FOR VIN: {vin} ===")
    driver.implicitly_wait(10)
    
    try:
        # Ensure screenshot directory exists
        if not os.path.exists(screenshot_name):
            os.makedirs(screenshot_name)
            logger.info(f"Created screenshot directory: {screenshot_name}")
        
        # Check for reCAPTCHA before starting
        if detect_recaptcha(driver):
            logger.warning("API: reCAPTCHA detected before scraping")
            if not wait_for_recaptcha_solution(driver):
                return False
        
        time.sleep(random.uniform(1, 2))
        
        try:
            vin_input = driver.find_element(By.ID, 'vin')
            logger.info("API: VIN input field found")
        except Exception as e:
            logger.error(f"API: Could not find VIN input field: {e}")
            return False
        
        vin_input.clear()
        logger.info(f"API: Entering VIN: {vin}")
        
        for char in vin:
            vin_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.1))
        
        try:
            submit = driver.find_element(By.ID, 'run_vhr_button')
            driver.execute_script("arguments[0].click();", submit)
            logger.info("API: Submit button clicked")
        except Exception as e:
            logger.error(f"API: Could not click submit button: {e}")
            return False
        
        sleep(6)
        
        # Check for reCAPTCHA after form submission
        if detect_recaptcha(driver):
            logger.warning("API: reCAPTCHA detected after form submission")
            if not wait_for_recaptcha_solution(driver):
                return False
        
        if len(driver.window_handles) > 1:
            logger.info("API: New window detected, switching...")
            driver.switch_to.window(driver.window_handles[len(driver.window_handles)-1])
            
            # Check for reCAPTCHA in new window
            if detect_recaptcha(driver):
                logger.warning("API: reCAPTCHA detected in report window")
                if not wait_for_recaptcha_solution(driver):
                    return False
            
            wait = WebDriverWait(driver, 60)
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "report-header-print-button")))
            logger.info("API: Report loaded successfully")

            driver.execute_script("document.querySelector('.do-not-print').style.display='none';")
            time.sleep(1)
            driver.maximize_window()
            time.sleep(2)

            width = driver.execute_script("return Math.max(document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth);")
            height = driver.execute_script("return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
            scroll_height = driver.execute_script("return window.innerHeight")
            
            logger.info(f"API: Page dimensions - Width: {width}px, Height: {height}px")

            try:
                driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
            except:
                pass

            scroll_offset = 0
            counter = 1
            logger.info("API: Starting screenshot capture...")
            driver.save_screenshot(f'{screenshot_name}/Image_1.png')
            
            while scroll_offset - 150 < height:
                try:
                    driver.execute_script("document.querySelector('.back-to-top-button').style.display='none';")
                except:
                    pass
            
                driver.execute_script(f"window.scrollTo(0, {scroll_offset})")
                sleep(2)
                driver.save_screenshot(f'{screenshot_name}/Image_{counter}.png')
                scroll_offset += scroll_height - 30
                counter += 1

            logger.info(f"API: Captured {counter-1} screenshots")

            input_path = screenshot_name
            output_path = 'PDF_API/' + vin + '.pdf'
            
            logger.info("API: Converting to PDF...")
            convert_folder_to_pdf(folder_path=input_path, output_path=output_path)
            logger.info('API: Uploading to S3...')
            upload_pdf_s3(output_path)
            
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(0.5)
            driver.maximize_window()
            
            # Cleanup screenshots
            cleanup_count = 0
            if os.path.exists(screenshot_name):
                for filename in os.listdir(screenshot_name):
                    file_path = os.path.join(screenshot_name, filename)
                    try:
                        os.remove(file_path)
                        cleanup_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove {file_path}: {e}")
                logger.info(f"API: Cleaned up {cleanup_count} screenshot files")
            else:
                os.makedirs(screenshot_name)
            
            logger.info(f"=== API SCRAPING COMPLETED SUCCESSFULLY FOR VIN: {vin} ===")
            return True
        else:
            logger.warning('API: No new window found')
            return False
            
    except Exception as e:
        logger.error(f"API scraping failed: {str(e)}")
        logger.error(f"=== API SCRAPING FAILED FOR VIN: {vin} ===")
        return False

# Legacy function for backward compatibility
def main(url, email, pasw, vin, api_token, chat_id, driver):
    """Legacy main function - redirects to enhanced version"""
    logger.info("Legacy main function called, redirecting to enhanced version")
    return main_with_retry(url, email, pasw, vin, api_token, chat_id)

def main_api(url, email, pasw, vin, driver, screenshot_name="screenshots_api"):
    """Legacy main_api function - redirects to enhanced version"""
    logger.info("Legacy main_api function called, redirecting to enhanced version")
    return main_api_with_retry(url, email, pasw, vin, screenshot_name)

if __name__ == '__main__':
    logger.info("Running utils.py directly for testing...")
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
        logger.info("Direct execution completed successfully!")
    else:
        logger.error("Direct execution failed. Check logs for details.")
