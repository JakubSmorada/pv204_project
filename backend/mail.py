from mailersend import emails
from dotenv import load_dotenv
import os

load_dotenv()

# code of function is copied from mailersend documentation https://developers.mailersend.com/api/v1/email.html?_gl=1*1v9az2u*_gcl_aw*R0NMLjE3NDI0MTc4MTQuQ2owS0NRancxdW0tQmhEdEFSSXNBQmpVNXg2N3BPZXJCRmUtM2pYa1hzVXlIMmVsX3dpUUkxVEVCeFlUUWZ0bVlMMjhvQ2RnNkJOb3JpVWFBbFZuRUFMd193Y0I.*_gcl_au*MTczMzU5MzkwNS4xNzQyNDE1MDE2
def send_verification_email(recipient_email, code):
    api_key = os.getenv("MAILERSEND_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    if not api_key:
        raise ValueError("MAILERSEND_API_KEY environment variable is not set")
    if not sender_email:
        raise ValueError("SENDER_EMAIL environment variable is not set")

    mailer = emails.NewEmail(api_key)

    # define an empty dict to populate with mail values
    mail_body = {}

    mail_from = {
        "name": "MarketplaceNostr",
        "email": sender_email,
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

    mailer.send(mail_body)