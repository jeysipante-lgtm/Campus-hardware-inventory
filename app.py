import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# Mail Configurations (Switched to Gmail SMTP)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_LOGIN = os.getenv('SMTP_LOGIN')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')

def send_otp_email(to_email, otp_code):
    """Sends OTP using Gmail SMTP with multi-port fallback"""
    subject = "Your Verification Code - Campus Hardware Inventory"
    body = f"Your One-Time Password (OTP) for account verification is: {otp_code}\n\nThis code will expire shortly."

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    ports_to_try = [587, 2525, 25]
    email_sent = False

    for port in ports_to_try:
        try:
            print(f"Attempting to send email via {SMTP_SERVER}:{port}...")
            server = smtplib.SMTP(SMTP_SERVER, port, timeout=10)
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
            server.quit()
            print(f"Successfully sent OTP email via port {port}")
            email_sent = True
            break
        except Exception as e:
            print(f"Failed to send email via port {port}: {e}")

    return email_sent

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

        # Send OTP Email
        if send_otp_email(email, otp_code):
            flash('OTP code sent to your email address. Please verify.', 'info')
            return redirect(url_for('verify_otp_register'))
        else:
            flash('Failed to send OTP email. Please check your email/SMTP setup.', 'danger')
            return redirect(url_for('register'))

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