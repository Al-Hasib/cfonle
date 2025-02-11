import os
import re
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, JobQueue
from src.utils import main, email, pasw, apiToken, chatID, get_browser
from src.Tele import SendPdf, WaitMsg, NoAccessMsg, TryAgainMsg
from src.login_script import login

load_dotenv()

chat_id_vin_number = tuple() # key: chat_id, value: vin_number
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
            chat_id_vin_number = chat_id_vin_number + ((sender_id, message_text),)
            print(chat_id_vin_number)
            length_requests = len(chat_id_vin_number)
            WaitMsg(vin=message_text, chat_id=sender_id, bot_token=context.bot.token, length_requests=length_requests)
        
        else:
            print(f"Message received: '{message_text}' from user: {sender_id}")
            TryAgainMsg(chat_id=sender_id, bot_token=context.bot.token)

        
    else:
        NoAccessMsg(chat_id=sender_id, bot_token=context.bot.token)
        print(f"Unauthorized message from user: {sender_id}")

def process_pdf_send(context: CallbackContext) -> None:
    """Sends PDFs to users based on VIN match."""
    global chat_id_vin_number
    bot: Bot = context.bot
    try:
        for pdf_file in os.listdir("PDF"):
            file_name = pdf_file.split(".")[0]
            print(f"Checking file: {file_name}")

            for item in chat_id_vin_number:
                if item[1] == file_name:
                    print(bot.token)
                    SendPdf(vin=item[1], chat_id=item[0], bot_token=bot.token)
                    print(f" {item[1]}PDF has been sent to {item[0]}user..")
                    os.remove(os.path.join("PDF", pdf_file))
                    print("PDF has been deleted..")
                    chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
                    print(f"After Deleting and sending pdf: {chat_id_vin_number}")
    except Exception as e:
        print(f"Raise issue in Sending PDF : {e}")
        pass

    
    # Process each chat_id and vin_num
    for item in chat_id_vin_number:
        # Call the main function for each vin_num associated with chat_id
        is_vin_correct = main(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=item[1], api_token=apiToken, chat_id=item[0], driver=driver)
        print("PDF has been saved after main function..")
        if is_vin_correct is False:
            chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
            print(f"Vin number is not correct : {chat_id_vin_number}")
        break

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

