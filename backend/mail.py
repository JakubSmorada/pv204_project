from mailersend import emails
from dotenv import load_dotenv
from secrets import randbelow
import os

load_dotenv()

API_KEY = os.getenv("MAILERSEND_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
if not API_KEY:
    raise ValueError("mail module: MAILERSEND_API_KEY environment variable is not set")
if not SENDER_EMAIL:
    raise ValueError("mail module: SENDER_EMAIL environment variable is not set")

# debugging info
print(f"mail module: Sender email configured: {'Yes' if SENDER_EMAIL else 'No'}")
print(f"mail module: API key configured: {'Yes' if API_KEY else 'No (key required)'}")

def generate_verification_code_str():
    return str(randbelow(900000) + 100000)

# code of function is copied from mailersend documentation https://developers.mailersend.com/api/v1/email.html?_gl=1*1v9az2u*_gcl_aw*R0NMLjE3NDI0MTc4MTQuQ2owS0NRancxdW0tQmhEdEFSSXNBQmpVNXg2N3BPZXJCRmUtM2pYa1hzVXlIMmVsX3dpUUkxVEVCeFlUUWZ0bVlMMjhvQ2RnNkJOb3JpVWFBbFZuRUFMd193Y0I.*_gcl_au*MTczMzU5MzkwNS4xNzQyNDE1MDE2
async def send_verification_email(recipient_email, code):
    mailer = emails.NewEmail(API_KEY)

    # define an empty dict to populate with mail values
    mail_body = {}

    mail_from = {
        "name": "MarketplaceNostr",
        "email": SENDER_EMAIL,
    }

    recipients = [
        {
            "email": recipient_email,
        }
    ]

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject("MarketplaceNostr Verification", mail_body)
    mailer.set_html_content(f"Code: {code}", mail_body)

    return mailer.send(mail_body)

def test_connection():
    try:
        mailer = emails.NewEmail(API_KEY)
        print("mail module: Connection test successful!")
        return True
    except Exception as e:
        print(f"mail module: Connection test failed: {str(e)}")
        return False

test_connection()