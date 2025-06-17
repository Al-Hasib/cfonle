import requests, os


def TryAgainMsg(chat_id, bot_token):
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
    "chat_id": chat_id,
    "text": "الرجاء التحقق مما يلي \n رقم الشاصية صحيح \n لا يوجد به فراغات \n اذا كنت متأكد من صحة الرقم \n قم بالتجربة مرة أخرى"
    }

    response = requests.post(api_url, data=data)
    
def WaitMsg(vin, chat_id, bot_token, length_requests):
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
    "chat_id": chat_id,
    "text": f"\n Your serial number is {length_requests}"
    }
    print(f"WaitMsg: {data}")

    response = requests.post(api_url, data=data)


def LimitIssueMsg(chat_id, bot_token, type='daily'):
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    if type=='daily':
        data = {
        "chat_id": chat_id,
        "text": "Dear User, Your daily limit exceeds. Please contact with support team to increase daily limit or try tomorrow. Thank you."
        }
    else:
        data = {
        "chat_id": chat_id,
        "text": "Dear User, Your life time Limit exceeds. Please contact with support team to increase limit. Thank you."
        }


    response = requests.post(api_url, data=data)


def SendPdf(vin, chat_id, bot_token):
    pdf_path = os.path.join(os.getcwd(), 'PDF', vin + '.pdf')
    print(pdf_path)
    url = f'https://api.telegram.org/bot{bot_token}/sendDocument'
    files = {
        'document': open(pdf_path, 'rb')
    }
    params = {
        'chat_id': chat_id,
    }
    response = requests.post(url, files=files, params=params)
    print(response.status_code)
    if response.status_code == 200:
        print('PDF sent successfully!')

def SendPdf_S3(vin, chat_id, bot_token):
    pdf_path = os.path.join(os.getcwd(), 'PDF_S3', vin + '.pdf')
    print(pdf_path)
    url = f'https://api.telegram.org/bot{bot_token}/sendDocument'
    files = {
        'document': open(pdf_path, 'rb')
    }
    params = {
        'chat_id': chat_id,
    }
    response = requests.post(url, files=files, params=params)
    print(response.status_code)
    if response.status_code == 200:
        print('PDF sent successfully!')

def NoAccessMsg(chat_id, bot_token):
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
    "chat_id": chat_id,
    "text": f"نعتذر, الخدمه غير متوفرة حالياً"
    }
    response = requests.post(api_url, data=data)

    

if __name__ == '__main__':
    SendPdf('58ADA1C11MU003498', '5491808070' ,'6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE')