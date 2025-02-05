import imaplib
import email
import re


def verfication_code():
    EMAIL = "datacar30@gmail.com"
    PASSWORD = "aqaj kmxm buxb sdtc"
    IMAP_SERVER = "imap.gmail.com"
    key = "FROM"
    from_mail = "CARFAX@noreply.email.carfax.com"

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("Inbox")
    status, ids = mail.search(None, key, from_mail)

    # print(status)
    # print(ids)

    ids_list = ids[0].split()[-1]
    typ, data = mail.fetch(ids_list, '(RFC822)')
    # print(typ, data)
    # print(ids_list)
    # print(len(data))
    for response in data:
        if type(response) is tuple:
            msg = email.message_from_bytes(response[1])
            # print(msg['subject'])
            # print(msg['from'])

            for part in msg.walk():
                if part.get_content_type()=="text/plain":
                    msg_body = part.get_payload()
                    # print(msg_body)
    # Regex pattern for verification code
    CODE_PATTERN = r'\b\d{6}\b'
    code = re.search(CODE_PATTERN, msg_body).group()
    print(f"Verification Code: {code}")
    return code

if __name__=="__main__":
    verfication = verfication_code()
    print(verfication)