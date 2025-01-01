# 6126785176:AAFJenSo3Ag79kJ1Z8V6ARyUiXzrFDH9zfQ
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from src.utils import main, email, pasw, apiToken, chatID, get_browser
from src.Tele import SendPdf, WaitMsg
import os
from src.login_script import login
import schedule
import time


screenshots = "screenshots"
driver = None
# is_quit = False

def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    global driver
    sender_id = update.message.chat_id
    message_text = update.message.text
    print(f"Message received: '{message_text}' from user: {sender_id}")
    WaitMsg(vin=message_text, chat_id=sender_id, bot_token="6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE")
    driver = main(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=message_text, api_token=apiToken, chat_id=sender_id, driver=driver)


def main_task() -> None:
    """Start the bot."""
    print(time.time())
    updater = Updater("6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE", use_context=True)

    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    

    updater.start_polling()
    updater.idle()

def CronJob(secondsPassed):
    global driver
    print(driver)
    print(f"In cronJOB: {secondsPassed}")
    # Keep the driver running for 58 seconds
    if secondsPassed == 57 and driver != None:
        driver.quit()
        print("58 seconds elapsed. Closing the WebDriver.")
    # Check if the directory exists
    if os.path.exists(screenshots):
        # Directory exists, remove files within it
        for filename in os.listdir(screenshots):
            file_path = os.path.join(screenshots, filename)
            os.remove(file_path)  # Remove individual files
    else:
        # Directory doesn't exist, create it
        os.makedirs(screenshots)


    driver = login(quit=False, headless=False)
    main_task()

    

def schedule_script():
    start_time = time.time()
    while True:
        secondsPassed = int(time.time()-start_time)
        schedule.every(1).minute.do(CronJob, secondsPassed=secondsPassed)
        schedule.run_pending()
        print(f"Time after schedule : {secondsPassed}")
        time.sleep(1)

if __name__ == '__main__':
    print("starting...")
    schedule_script()
    