import os
import re
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, JobQueue
from src.utils import main, email, pasw, apiToken, chatID, get_browser
from src.Tele import SendPdf, WaitMsg, NoAccessMsg
from src.login_script import login
from collections import defaultdict

load_dotenv()

chat_id_vin_number = defaultdict(list) # key: chat_id, value: vin_number
screenshots = "screenshots"


def is_only_upper_and_number(s):
    return bool(re.fullmatch(r"(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]+", s))


def echo(update: Update, context: CallbackContext) -> None:
    """Handles user messages."""
    global chat_id_vin_number
    sender_id = str(update.message.chat_id)
    authorized_ids = os.getenv("IDs") # Convert to list
    message_text = update.message.text

    if sender_id in authorized_ids:
        if is_only_upper_and_number(message_text):
            chat_id_vin_number[sender_id].append(message_text)
            print(chat_id_vin_number)

        length_requests = sum(len(vin_list) for vin_list in chat_id_vin_number.values())
        print(f"Message received: '{message_text}' from user: {sender_id}")
        WaitMsg(vin=message_text, chat_id=sender_id, bot_token=context.bot.token, length_requests=length_requests)
    else:
        NoAccessMsg(chat_id=sender_id, bot_token=context.bot.token)
        print(f"Unauthorized message from user: {sender_id}")


def process_pdf_send(context: CallbackContext) -> None:
    """Sends PDFs to users based on VIN match."""
    global chat_id_vin_number
    bot: Bot = context.bot

    if not chat_id_vin_number:
        return

    # Create a copy of keys to avoid dictionary modification errors
    keys_to_delete = []
    files_to_delete = []

    for pdf_file in os.listdir("PDF"):
        file_name = pdf_file.split(".")[0]
        print(f"Checking file: {file_name}")

        for chat_id, vin_number in chat_id_vin_number.items():
            if vin_number == file_name:
                print(bot.token)
                SendPdf(vin=vin_number, chat_id=chat_id, bot_token=bot.token)
                keys_to_delete.append(chat_id)
                files_to_delete.append(file_name)
                os.remove(os.path.join("PDF", pdf_file))

    # Remove keys after iteration
    for key in keys_to_delete:
        for remove_vin in files_to_delete:
            if remove_vin in chat_id_vin_number[key]:
                print(f"remove vin {remove_vin} from key {key}")
                chat_id_vin_number[key].remove(remove_vin)
    
    # Process each chat_id and vin_num
    for chat_id, vin_nums in chat_id_vin_number.items():
        for vin_num in vin_nums:
            # Call the main function for each vin_num associated with chat_id
            main(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=vin_num, api_token=apiToken, chat_id=chat_id, driver=driver)


def main_task() -> None:
    """Starts the bot and schedules the job queue."""
    updater = Updater("6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE", use_context=True)

    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Start the job queue
    job_queue: JobQueue = updater.job_queue
    job_queue.run_repeating(process_pdf_send, interval=60, first=0)  # Runs every 60 seconds

    print("Bot started...")
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    if os.path.exists(screenshots):
        for filename in os.listdir(screenshots):
            file_path = os.path.join(screenshots, filename)
            os.remove(file_path)  # Remove files
    else:
        os.makedirs(screenshots)

    driver = login(quit=False, headless=False)
    main_task()
