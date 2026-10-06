import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# Mail Configurations
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_LOGIN = os.getenv('SMTP_LOGIN')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')

def send_otp_email(to_email, otp_code):
    """Attempts SMTP email delivery with automatic fallback to Render Logs"""
    subject = "Your Verification Code - Campus Hardware Inventory"
    body = f"Your One-Time Password (OTP) for account verification is: {otp_code}\n\nThis code will expire shortly."

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL or 'noreply@campus.edu'
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    email_sent = False

    # Attempt SMTP if login credentials exist
    if SMTP_LOGIN and SMTP_PASSWORD:
        try:
            print(f"Connecting via SSL port 465 to {SMTP_SERVER}...")
            with smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=5) as server:
                server.login(SMTP_LOGIN, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
            print("Successfully sent OTP email via SSL 465")
            email_sent = True
        except Exception as e:
            print(f"SMTP delivery unavailable: {e}")

    # Fallback log for development / Render free tier restrictions
    print("\n" + "="*50)
    print(f"=== VERIFICATION OTP FOR [{to_email}]: {otp_code} ===")
    print("="*50 + "\n")

    # Return True so registration proceeds smoothly
    return True

@app.route('/')
def index():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        student_number = request.form.get('student_number', '')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Student')

        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        
        # Save registration data temporarily in session
        session['pending_user'] = {
            'username': username,
            'student_number': student_number,
            'email': email,
            'password': password,
            'role': role,
            'otp': otp_code
        }

        # Handle OTP delivery / fallback
        send_otp_email(email, otp_code)
        flash('Verification code generated! Check your email (or Render Logs).', 'info')
        return redirect(url_for('verify_otp_register'))

    return render_template('register.html')

@app.route('/verify-otp/register', methods=['GET', 'POST'])
def verify_otp_register():
    pending_user = session.get('pending_user')
    if not pending_user:
        flash('Session expired. Please register again.', 'warning')
        return redirect(url_for('register'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp_code')
        if entered_otp == pending_user['otp']:
            # OTP match! Save user to Database here
            session.pop('pending_user', None)
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP code. Please try again.', 'danger')

    return render_template('otp_verify.html', action_url=url_for('verify_otp_register'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return "Welcome to Campus Hardware Inventory Dashboard!"

if __name__ == '__main__':
    app.run(debug=True)