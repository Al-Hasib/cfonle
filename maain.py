import os
import re
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, JobQueue
from src.utils import main, email, pasw, apiToken, chatID, get_browser
from src.Tele import SendPdf, WaitMsg, NoAccessMsg, TryAgainMsg, SendPdf_S3, LimitIssueMsg
from src.login_script import login
from download_pdf_api import get_pdf
from src.s3_connection import pdf_exists, download_pdf_s3
import pandas as pd
import uuid
import time
load_dotenv()

chat_id_vin_number = tuple() # key: chat_id, value: vin_number
id_vin_list = list()
screenshots = "screenshots"

df = pd.read_csv("user_handling.csv")

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
    # daily_access = int(daily_limit)-int(daily_limit)
    total_used = user_data['total_used']
    total_limit = user_data['total_limit']
    # total_access = int(daily_limit)-int(daily_limit)

    if int(daily_used) <= int(daily_limit) and int(total_used <= total_limit):
        return daily_available, total_available, daily_used, total_used
    
    elif int(daily_used) <= int(daily_limit) and int(total_used > total_limit):
        total_available = False
        return daily_available, total_available, daily_used, total_used
    
    elif int(daily_used) > int(daily_limit) and int(total_used <= total_limit):
        daily_available = False
        return daily_available, total_available, daily_used, total_used
    else:
        daily_available = False
        total_available = False
        return daily_available, total_available, daily_used, total_used
    


def is_uuid4(uuid_string):
    try:
        val = uuid.UUID(uuid_string, version=4)
        print(val)
        return str(val) == uuid_string
    except ValueError:
        return False

def echo(update: Update, context: CallbackContext) -> None:
    """Handles user messages."""
    global chat_id_vin_number, df
    sender_id = str(update.message.chat_id)
    all_ids = df['telegram_id'].to_list()
    # authorized_ids = os.getenv("IDs") # Convert to list
    message_text = update.message.text

    if is_uuid4(message_text):
        # name = message_text[1:]
        # if int(sender_id) in all_ids:
        #     df.loc[df['Id']== int(sender_id), "name"] = name
        df.loc[df['uuid']==message_text,'telegram_id'] = int(sender_id)
        df.to_csv('user_handling.csv', index=False)

        # else:
        #     new_row_index = len(df)
        #     df.loc[new_row_index] = [name, int(sender_id), 'pending', 100, 0]

    daily_available, total_available, daily_used, total_used  = check_user_limit(sender_id)
    # print(f"Check test: {check_test}\n used:{used} \nrest:{rest}\nlimit:{limit}")
    if not daily_available:
        LimitIssueMsg(chat_id= sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE', type='daily')
    if not total_available:
        LimitIssueMsg(chat_id= sender_id, bot_token='6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE', type='total')
    

    if int(sender_id) in all_ids and daily_available and total_available:
        df.loc[df['telegram_id']== int(sender_id), "daily_used"] = int(daily_used) + 1
        df.loc[df['telegram_id']== int(sender_id), "total_used"] = int(total_used) + 1
        df.to_csv('user_handling.csv', index=False)
        if is_only_upper_and_number(message_text):
            pdf_name = message_text+".pdf"
            if pdf_exists(object_name=pdf_name):
                s3_file_path = os.path.join(os.getcwd(),"PDF_S3")
                download_pdf_s3(file_name=pdf_name, path =s3_file_path)
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

def process_pdf_send(context: CallbackContext) -> None:
    """Sends PDFs to users based on VIN match."""
    # global chat_id_vin_number
    global id_vin_list
    bot: Bot = context.bot
    try:
        for pdf_file in os.listdir("PDF"):
            file_name = pdf_file.split(".")[0]
            print(f"Checking file: {file_name}")

            for item in id_vin_list:
                if item[1] == file_name:
                    print(bot.token)
                    SendPdf(vin=item[1], chat_id=item[0], bot_token=bot.token)
                    print(f" {item[1]} PDF has been sent to {item[0]} user..")
                    os.remove(os.path.join("PDF", pdf_file))
                    id_vin_list.remove((item[0],item[1]))
                    # chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
                    print("PDF has been deleted..")
                    print(f"After Deleting and sending pdf: {id_vin_list}")

    except Exception as e:
        print(f"Raise issue in Sending PDF : {e}")
        pass

    
# Process each chat_id and vin_num
def process_main(context: CallbackContext):
    global chat_id_vin_number
    global id_vin_list
    for item in (chat_id_vin_number):
        chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
        print(f"=== Process main started === \nitem : {item}\n chat_id_vin: {chat_id_vin_number}")

        is_vin_correct = main(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=item[1], api_token=apiToken, chat_id=item[0], driver=driver)
        print("PDF has been saved after main function..")
        if is_vin_correct is False:
            chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
            print(f"Vin number is not correct of main : {chat_id_vin_number}")
        id_vin_list.append((item[0],item[1]))        

        process_pdf_send(context)
        break



def get_pdf_api(context: CallbackContext):
    global chat_id_vin_number
    global id_vin_list

    for index, item in enumerate(chat_id_vin_number):
        if index ==1 and len(chat_id_vin_number)>1:
            chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
            print(f"=== GET PDF API started === \n item : {item} & index : {index}\n Chat_id_vin : {chat_id_vin_number}")
            is_vin_correct = get_pdf(api_url="http://54.225.0.46:8000/generate-pdf_one/", vin_number=item[1], pdf_folder="PDF")
            if is_vin_correct is False:
                chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
                print(f"Vin number is not correct of API: {chat_id_vin_number}")
            id_vin_list.append((item[0],item[1]))
            process_pdf_send(context)


def get_pdf_api_2(context: CallbackContext):
    global chat_id_vin_number
    global id_vin_list

    for index, item in enumerate(chat_id_vin_number):
        if index ==2 and len(chat_id_vin_number)>1:
            chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
            print(f"=== GET PDF API started === \n item : {item} & index : {index}\n Chat_id_vin : {chat_id_vin_number}")
            is_vin_correct = get_pdf(api_url="http://54.225.0.46:8080/generate-pdf_one/", vin_number=item[1], pdf_folder="PDF")
            if is_vin_correct is False:
                chat_id_vin_number = tuple(x for x in chat_id_vin_number if x != (item[0],item[1]))
                print(f"Vin number is not correct of API: {chat_id_vin_number}")
            id_vin_list.append((item[0],item[1]))
            process_pdf_send(context)



def main_task() -> None:
    """Starts the bot and schedules the job queue."""
    updater = Updater("6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE", use_context=True)

    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Start the job queue
    job_queue: JobQueue = updater.job_queue
    # job_queue.run_repeating(process_pdf_send, interval=60, first=30)  # Runs every 60 seconds
    job_queue.run_repeating(process_main, interval=20, first=0)  # Runs every 60 seconds
    job_queue.run_repeating(get_pdf_api, interval=20, first=0)  # Runs every 60 seconds
    job_queue.run_repeating(get_pdf_api_2, interval=20, first=0)  # Runs every 60 seconds

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

