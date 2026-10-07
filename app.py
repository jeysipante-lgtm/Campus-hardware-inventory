import os
import smtplib
from email.mime.text import MIMEText

# Kunin ang credentials mula sa Render Environment Variables
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'jeysipante@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

def send_otp_email_brevo(to_email, otp_code, purpose="verification"):
    subject = f"Your {purpose.title()} OTP Code - Campus Hardware Inventory"
    body = (
        f"Hello,\n\n"
        f"Your One-Time Password (OTP) for {purpose} is: {otp_code}\n\n"
        f"This code is valid for 10 minutes. Please do not share this code with anyone.\n\n"
        f"Best regards,\nCampus Hardware Inventory Team"
    )

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email

        # Connect to Gmail SMTP SSL server at Port 465
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())
        server.quit()

        print(f"SUCCESS: OTP sent via Gmail SMTP to {to_email}!")
        return True
    except Exception as e:
        print(f"ERROR: Gmail SMTP failed: {e}")

    # Fallback log sa Render console para hindi ma-block ang login/reset flow kung sakaling mag-fail ang SMTP
    print(f"==========================================")
    print(f"=== {purpose.upper()} OTP FOR [{to_email}]: {otp_code} ===")
    print(f"==========================================")
    return True