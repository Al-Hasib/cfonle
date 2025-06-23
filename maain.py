import os
import re
import signal
import sys
import atexit
import logging
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

# Setup enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Global variables
chat_id_vin_number = tuple()
id_vin_list = list()
screenshots = "screenshots"
updater = None

# Load user data with error handling
try:
    df = pd.read_csv("user_handling.csv")
    logger.info("User data loaded successfully")
except FileNotFoundError:
    logger.error("user_handling.csv not found")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error loading user data: {e}")
    sys.exit(1)

def cleanup_on_exit():
    """Cleanup function to run on exit"""
    global updater
    if updater:
        try:
            updater.stop()
            logger.info("Bot stopped cleanly")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

# Register cleanup function
atexit.register(cleanup_on_exit)

def signal_handler(signum, frame):
    """Handle system signals for clean shutdown"""
    logger.info(f"Received signal {signum}, shutting down...")
    cleanup_on_exit()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def is_only_upper_and_number(s):
    """Check if string contains only uppercase letters and numbers"""
    return bool(re.fullmatch(r"(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]+", s))

def check_user_limit(user_id):
    """Check if a specific user has exceeded their limit"""
    daily_available = True
    total_available = True

    try:
        user = df[df['telegram_id'] == int(user_id)]
        if user.empty:
            logger.warning(f"User {user_id} not found in database")
            return False, False, 0, 0
        
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
    except Exception as e:
        logger.error(f"Error checking user limit: {e}")
        return False, False, 0, 0

def is_uuid4(uuid_string):
    """Check if string is a valid UUID4"""
    try:
        val = uuid.UUID(uuid_string, version=4)
        return str(val) == uuid_string
    except ValueError:
        return False

def echo(update: Update, context: CallbackContext) -> None:
    """Handles user messages with enhanced error handling and logging"""
    global chat_id_vin_number, df
    
    try:
        sender_id = str(update.message.chat_id)
        all_ids = df['telegram_id'].to_list()
        message_text = update.message.text
        
        logger.info(f"Received message from {sender_id}: {message_text}")

        # Handle UUID registration
        if is_uuid4(message_text):
            df.loc[df['uuid']==message_text,'telegram_id'] = int(sender_id)
            df.to_csv('user_handling.csv', index=False)
            logger.info(f"UUID {message_text} registered for user {sender_id}")

        daily_available, total_available, daily_used, total_used = check_user_limit(sender_id)
        
        # Check limits and send appropriate messages
        if not daily_available:
            LimitIssueMsg(chat_id=sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE', type='daily')
            logger.info(f"Daily limit exceeded for user {sender_id}")
        if not total_available:
            LimitIssueMsg(chat_id=sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE', type='total')
            logger.info(f"Total limit exceeded for user {sender_id}")
        
        # Process authorized users within limits
        if int(sender_id) in all_ids and daily_available and total_available:
            # Update usage counters
            df.loc[df['telegram_id']== int(sender_id), "daily_used"] = int(daily_used) + 1
            df.loc[df['telegram_id']== int(sender_id), "total_used"] = int(total_used) + 1
            df.to_csv('user_handling.csv', index=False)
            logger.info(f"Updated usage for user {sender_id}: daily={int(daily_used)+1}, total={int(total_used)+1}")
            
            # Process VIN number
            if is_only_upper_and_number(message_text):
                pdf_name = message_text+".pdf"
                
                # Check if PDF exists in S3
                if pdf_exists(object_name=pdf_name):
                    s3_file_path = os.path.join(os.getcwd(),"PDF_S3")
                    download_pdf_s3(file_name=pdf_name, path=s3_file_path)
                    SendPdf_S3(vin=message_text, chat_id=sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE')
                    
                    # Clean up downloaded file
                    try:
                        os.remove(os.path.join(s3_file_path, pdf_name))
                        logger.info("PDF sent from AWS S3 and cleaned up")
                    except Exception as e:
                        logger.error(f"Error removing S3 file: {e}")
                else:
                    # Add to processing queue
                    chat_id_vin_number = chat_id_vin_number + ((sender_id, message_text),)
                    logger.info(f"Added to queue: {chat_id_vin_number}")
                    length_requests = len(chat_id_vin_number)
                    WaitMsg(vin=message_text, chat_id=sender_id, bot_token=context.bot.token, length_requests=length_requests)
            else:
                logger.info(f"Invalid VIN format from user: {sender_id}")
                TryAgainMsg(chat_id=sender_id, bot_token=context.bot.token)
        else:
            logger.warning(f"Unauthorized access attempt from user: {sender_id}")
            NoAccessMsg(chat_id=sender_id, bot_token=context.bot.token)
            
    except Exception as e:
        logger.error(f"Error in echo handler: {e}")
        try:
            # Send error message to user
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text="An error occurred. Please try again later."
            )
        except:
            pass

def process_pdf_send(context: CallbackContext) -> None:
    """Sends PDFs to users based on VIN match with enhanced error handling"""
    global id_vin_list
    bot: Bot = context.bot
    
    try:
        if not os.path.exists("PDF"):
            logger.warning("PDF directory does not exist")
            return
            
        pdf_files = os.listdir("PDF")
        if not pdf_files:
            return
            
        for pdf_file in pdf_files:
            try:
                file_name = pdf_file.split(".")[0]
                logger.info(f"Processing PDF file: {file_name}")

                for item in list(id_vin_list):  # Create copy to avoid modification during iteration
                    if item[1] == file_name:
                        SendPdf(vin=item[1], chat_id=item[0], bot_token=bot.token)
                        logger.info(f"PDF {item[1]} sent to user {item[0]}")
                        
                        # Clean up
                        pdf_path = os.path.join("PDF", pdf_file)
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
                            logger.info("PDF file deleted after sending")
                        
                        id_vin_list.remove((item[0], item[1]))
                        logger.info(f"Removed from queue. Remaining: {id_vin_list}")
                        break
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_file}: {e}")
                
    except Exception as e:
        logger.error(f"Error in PDF sending process: {e}")

def process_main_enhanced(context: CallbackContext):
    """Enhanced process_main with comprehensive error handling and logging"""
    global chat_id_vin_number, id_vin_list
    
    try:
        if not chat_id_vin_number:
            return
            
        # Process one item at a time
        for item in list(chat_id_vin_number):
            try:
                # Remove from queue
                chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0], item[1]))
                logger.info(f"Processing VIN request: {item[1]} for user {item[0]}")
                logger.info(f"Remaining in queue: {len(chat_id_vin_number)}")

                # Process with retry logic
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
                    logger.info(f"VIN processing successful for: {item[1]}")
                    process_pdf_send(context)
                else:
                    logger.warning(f"VIN processing failed for: {item[1]}")
                
                # Process only one item per call to avoid overwhelming
                break
                
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")
                # Continue with next item instead of breaking
                continue
                
    except Exception as e:
        logger.error(f"Error in process_main_enhanced: {e}")

def clear_webhook_and_start():
    """Clear webhook and start bot with enhanced error handling"""
    global updater
    
    try:
        # Clear any existing webhook
        bot = Bot(token="6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE")
        bot.delete_webhook()
        logger.info("Webhook cleared successfully")
        time.sleep(2)
        
    except Exception as e:
        logger.error(f"Error clearing webhook: {e}")

    try:
        # Create updater with enhanced configuration
        updater = Updater(
            "6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE", 
            use_context=True,
            request_kwargs={'read_timeout': 20, 'connect_timeout': 20}
        )
        
        dp = updater.dispatcher
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

        # Start job queue with optimized intervals
        job_queue: JobQueue = updater.job_queue
        job_queue.run_repeating(process_main_enhanced, interval=25, first=5)

        logger.info("Enhanced Bot started with anti-detection strategies...")
        
        # Start polling with optimized parameters
        updater.start_polling(
            poll_interval=1.0,
            timeout=20,
            drop_pending_updates=True,
            bootstrap_retries=-1,
            read_latency=2.0,
        )
        
        updater.idle()
        
    except Conflict as e:
        logger.error(f"Conflict error: {e}")
        logger.error("Another bot instance might be running. Please stop all other instances.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)

def main_task() -> None:
    """Main task with comprehensive setup and cleanup"""
    try:
        # Setup directories with error handling
        for dir_name in ["screenshots", "screenshots_api", "screenshots_api_2", "PDF", "PDF_API", "PDF_S3"]:
            try:
                if os.path.exists(dir_name):
                    for filename in os.listdir(dir_name):
                        file_path = os.path.join(dir_name, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    logger.info(f"Cleaned directory: {dir_name}")
                else:
                    os.makedirs(dir_name)
                    logger.info(f"Created directory: {dir_name}")
            except Exception as e:
                logger.error(f"Error setting up directory {dir_name}: {e}")

        logger.info("Starting enhanced telegram bot with comprehensive anti-detection capabilities...")
        clear_webhook_and_start()
        
    except Exception as e:
        logger.error(f"Fatal error in main_task: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main_task()
