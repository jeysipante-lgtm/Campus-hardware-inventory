import os
import random
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, render_template_string

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# Mail Configurations (Brevo API)
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')  # Ang Brevo API / Master Key mo (xsmtpsib-...)
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'jeysipante@gmail.com')

def send_otp_email_brevo(to_email, otp_code, purpose="verification"):
    subject = f"Your {purpose.title()} OTP Code - Campus Hardware Inventory"
    body = f"Your One-Time Password (OTP) for {purpose} is: {otp_code}\n\nThis code will expire shortly."

    # Subukang magpadala gamit ang Brevo HTTP API (Hindi nabablock ng Render)
    if SMTP_PASSWORD:
        try:
            print(f"Sending email via Brevo HTTP API to {to_email}...")
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": SMTP_PASSWORD.strip(),
                "content-type": "application/json"
            }
            payload = {
                "sender": {"name": "Campus Hardware Inventory", "email": SENDER_EMAIL},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": body
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                print(f"SUCCESS: OTP email sent via Brevo API to {to_email}!")
                return True
            else:
                print(f"ERROR: Brevo API failed with status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"ERROR: Failed to connect to Brevo API! Reason: {e}")

    # Fallback log sa Render kapag may problema
    print("\n" + "="*50)
    print(f"=== {purpose.upper()} OTP FOR [{to_email}]: {otp_code} ===")
    print("="*50 + "\n")

    return True