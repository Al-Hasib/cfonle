import os
import re
import signal
import sys
import atexit
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, JobQueue
from telegram.error import Conflict, NetworkError
from src.utils import main_with_retry, main_api_with_retry, email, pasw, apiToken, chatID
from src.Tele import SendPdf, WaitMsg, NoAccessMsg, TryAgainMsg, SendPdf_S3, LimitIssueMsg
from src.s3_connection import download_pdf_s3, pdf_exists
import pandas as pd
import uuid
import time
import random

load_dotenv()

# Global variables
chat_id_vin_number = tuple()
id_vin_list = list()
screenshots = "screenshots"
updater = None

# Load user data
df = pd.read_csv("user_handling.csv")

def cleanup_on_exit():
    """Cleanup function to run on exit"""
    global updater
    if updater:
        try:
            updater.stop()
            print("Bot stopped cleanly")
        except:
            pass

# Register cleanup function
atexit.register(cleanup_on_exit)

def signal_handler(signum, frame):
    """Handle system signals for clean shutdown"""
    print(f"Received signal {signum}, shutting down...")
    cleanup_on_exit()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def is_only_upper_and_number(s):
    return bool(re.fullmatch(r"(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]+", s))

def check_user_limit(user_id):
    """Check if a specific user has exceeded their limit"""
    daily_available = True
    total_available = True

    user = df[df['telegram_id'] == int(user_id)]
    if user.empty:
        return False,False,0,0
    user_data = user.iloc[0]
    daily_used = user_data['daily_used']
    daily_limit = user_data['daily_limit']
    total_used = user_data['total_used']
    total_limit = user_data['total_limit']

    if int(daily_used) <= int(daily_limit) and int(total_used) <= int(total_limit):
        return daily_available, total_available, daily_used, total_used
    elif int(daily_used) <= int(daily_limit) and int(total_used) > int(total_limit):
        total_available = False
        return daily_available, total_available, daily_used, total_used
    elif int(daily_used) > int(daily_limit) and int(total_used) <= int(total_limit):
        daily_available = False
        return daily_available, total_available, daily_used, total_used
    else:
        daily_available = False
        total_available = False
        return daily_available, total_available, daily_used, total_used

def is_uuid4(uuid_string):
    try:
        val = uuid.UUID(uuid_string, version=4)
        return str(val) == uuid_string
    except ValueError:
        return False

def echo(update: Update, context: CallbackContext) -> None:
    """Handles user messages with enhanced error handling"""
    global chat_id_vin_number, df
    
    try:
        sender_id = str(update.message.chat_id)
        all_ids = df['telegram_id'].to_list()
        message_text = update.message.text

        if is_uuid4(message_text):
            df.loc[df['uuid']==message_text,'telegram_id'] = int(sender_id)
            df.to_csv('user_handling.csv', index=False)

        daily_available, total_available, daily_used, total_used = check_user_limit(sender_id)
        
        if not daily_available:
            LimitIssueMsg(chat_id=sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE', type='daily')
        if not total_available:
            LimitIssueMsg(chat_id=sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE', type='total')
        
        if int(sender_id) in all_ids and daily_available and total_available:
            df.loc[df['telegram_id']== int(sender_id), "daily_used"] = int(daily_used) + 1
            df.loc[df['telegram_id']== int(sender_id), "total_used"] = int(total_used) + 1
            df.to_csv('user_handling.csv', index=False)
            
            if is_only_upper_and_number(message_text):
                pdf_name = message_text+".pdf"
                if pdf_exists(object_name=pdf_name):
                    s3_file_path = os.path.join(os.getcwd(),"PDF_S3")
                    download_pdf_s3(file_name=pdf_name, path=s3_file_path)
                    SendPdf_S3(vin=message_text, chat_id=sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE')
                    os.remove(os.path.join(s3_file_path, pdf_name))
                    print("Pdf has been sent from AWS S3...")
                else:
                    chat_id_vin_number = chat_id_vin_number + ((sender_id, message_text),)
                    print(chat_id_vin_number)
                    length_requests = len(chat_id_vin_number)
                    WaitMsg(vin=message_text, chat_id=sender_id, bot_token=context.bot.token, length_requests=length_requests)
            else:
                print(f"Message received: '{message_text}' from user: {sender_id}")
                TryAgainMsg(chat_id=sender_id, bot_token=context.bot.token)
        else:
            print(f"Message received: '{message_text}' from user: {sender_id}")
            NoAccessMsg(chat_id=sender_id, bot_token=context.bot.token)
            print(f"Unauthorized message from user: {sender_id}")
            
    except Exception as e:
        print(f"Error in echo handler: {e}")

def process_pdf_send(context: CallbackContext) -> None:
    """Sends PDFs to users based on VIN match."""
    global id_vin_list
    bot: Bot = context.bot
    try:
        for pdf_file in os.listdir("PDF"):
            file_name = pdf_file.split(".")[0]
            print(f"Checking file: {file_name}")

            for item in id_vin_list:
                if item[1] == file_name:
                    SendPdf(vin=item[1], chat_id=item[0], bot_token=bot.token)
                    print(f" {item[1]} PDF has been sent to {item[0]} user..")
                    os.remove(os.path.join("PDF", pdf_file))
                    id_vin_list.remove((item[0],item[1]))
                    print("PDF has been deleted..")
                    print(f"After Deleting and sending pdf: {id_vin_list}")
    except Exception as e:
        print(f"Error in PDF sending: {e}")

def process_main_enhanced(context: CallbackContext):
    """Enhanced process_main with retry logic"""
    global chat_id_vin_number, id_vin_list
    
    try:
        for item in list(chat_id_vin_number):
            chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0], item[1]))
            print(f"=== Enhanced Process main started === \nitem : {item}\n chat_id_vin: {chat_id_vin_number}")

            is_vin_correct = main_with_retry(
                url='https://www.carfaxonline.com/', 
                email=email, 
                pasw=pasw, 
                vin=item[1], 
                api_token=apiToken, 
                chat_id=item[0]
            )
            
            if is_vin_correct:
                id_vin_list.append((item[0], item[1]))
                process_pdf_send(context)
            else:
                print(f"VIN processing failed for: {item[1]}")
            
            break
    except Exception as e:
        print(f"Error in process_main_enhanced: {e}")

def clear_webhook_and_start():
    """Clear webhook and start bot with proper error handling"""
    global updater
    
    try:
        # Clear any existing webhook
        bot = Bot(token="6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE")
        bot.delete_webhook()
        print("Webhook cleared successfully")
        time.sleep(2)  # Wait a bit after clearing webhook
        
    except Exception as e:
        print(f"Error clearing webhook: {e}")

    try:
        # Create updater with error handling
        updater = Updater("6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE", use_context=True)
        
        dp = updater.dispatcher
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

        # Start job queue
        job_queue: JobQueue = updater.job_queue
        job_queue.run_repeating(process_main_enhanced, interval=20, first=0)

        print("Enhanced Bot started with anti-detection strategies...")
        
        # Start polling with error handling
        updater.start_polling(
            poll_interval=1.0,
            timeout=20,
            drop_pending_updates=True,
            bootstrap_retries=-1,
            read_latency=2.0
        )
        
        updater.idle()
        
    except Conflict as e:
        print(f"Conflict error: {e}")
        print("Another bot instance might be running. Please stop all other instances.")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)

def main_task() -> None:
    """Main task with proper cleanup"""
    # Setup directories
    for dir_name in ["screenshots", "screenshots_api", "screenshots_api_2"]:
        if os.path.exists(dir_name):
            for filename in os.listdir(dir_name):
                file_path = os.path.join(dir_name, filename)
                os.remove(file_path)
        else:
            os.makedirs(dir_name)

    print("Starting enhanced telegram bot with anti-detection capabilities...")
    clear_webhook_and_start()

if __name__ == '__main__':
    main_task()
