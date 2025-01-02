from src.utils import get_browser, email, pasw, url, By, sleep
from selenium.common.exceptions import NoSuchElementException


def login(quit=False, headless=False):
    print("getting browser.....")
    driver = get_browser(headless=headless)
    print("got browser")
    driver.implicitly_wait(50)
    driver.get(url)
    driver.find_element(By.ID, 'username').send_keys(email)
    driver.find_element(By.ID, 'password').send_keys(pasw)
    
    # Locate the login button by class
    # login_button = driver.find_element(By.CLASS_NAME, 'cb2e18c4c')
    # login_button = driver.find_element_by_css_selector('button[type="submit"]')
    login_button = driver.find_element(By.XPATH, "//button[@type='submit' and @name='action']")

    # Method 2: Using JavaScript executor
    driver.execute_script("arguments[0].click();", login_button)
    print("Login Complete...")


    # check if there is a verification level
    # change verification method
    try:
        try_another_method_btn = driver.find_element(By.XPATH, "//button[@type='submit' and @name='action' and @value='pick-authenticator']")
    except Exception as e:
        try_another_method_btn = None

    if try_another_method_btn: 
        driver.execute_script("arguments[0].click();", try_another_method_btn)
        # select email as an verification method
        email_btn = driver.find_element(By.XPATH, "//button[@type='submit' and @name='action' and @value='email::1']")
        driver.execute_script("arguments[0].click();", email_btn)

        # take verification code from the user and put it in the input field
        try:
            has_code_field = driver.find_element(By.ID, "code")
        except Exception as e:
            has_code_field = None
        
        while has_code_field:
            verification_code = input("Enter verification code: ") 
            driver.find_element(By.ID, "code").send_keys(verification_code)

            continue_btn = driver.find_element(By.XPATH, "//button[@type='submit' and @name='action']")
            driver.execute_script("arguments[0].click();", continue_btn)

            # check if user has provided the correct verification code or not
            try:
                has_code_field = driver.find_element(By.ID, "code")
                print("invalid verification code !!")
            except NoSuchElementException:
                has_code_field = None
                
    driver.maximize_window()
    if quit:
        driver.quit()
    else:
        return driver


if __name__ == "__main__":
    login()
