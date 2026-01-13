import base64
import os.path
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import current_app, session
from concurrent.futures import ThreadPoolExecutor
import time

import json

CONFIG_FILE = 'email_config.json'
DEFAULT_LIMIT = 5

def store_otp_in_session(key, otp):
    """Stores OTP and timestamp in session."""
    session[key] = otp
    session[key + '_time'] = int(time.time())

def verify_otp_in_session(key, input_otp, max_age=600):
    """Verifies OTP and expiration (default 10 mins). Returns (bool, message)."""
    # Check existence
    if key not in session: 
        return False, "OTP not found or expired."
    
    # Check Expiry
    stored_time = session.get(key + '_time', 0)
    if time.time() - stored_time > max_age:
        session.pop(key, None)
        session.pop(key + '_time', None)
        return False, "OTP has expired."
        
    # Check Match
    if str(session.get(key)) == str(input_otp):
        # Clear after success
        session.pop(key, None)
        session.pop(key + '_time', None)
        return True, "Success"
        
    return False, "Invalid OTP."

def load_email_config():
    """Loads email configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading email config: {e}")
    return {'max_workers': DEFAULT_LIMIT}

def save_email_config(config):
    """Saves email configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving email config: {e}")

def get_current_thread_limit():
    return load_email_config().get('max_workers', DEFAULT_LIMIT)

# Initialize Thread Pool with loaded config
_current_config = load_email_config()
email_executor = ThreadPoolExecutor(max_workers=_current_config.get('max_workers', DEFAULT_LIMIT))

def update_email_thread_limit(new_limit):
    """Updates the thread limit and re-initializes the executor."""
    global email_executor
    try:
        new_limit = int(new_limit)
        if new_limit < 1: raise ValueError("Limit must be positive")
        
        # Save config
        save_email_config({'max_workers': new_limit})
        
        # dynamic update: replace executor
        old_executor = email_executor
        email_executor = ThreadPoolExecutor(max_workers=new_limit)
        
        # Gracefully shutdown old executor (stop accepting new, allow pending to finish)
        old_executor.shutdown(wait=False)
        
        return True
    except Exception as e:
        print(f"Failed to update thread limit: {e}")
        return False

def get_gmail_service(token_path):
    """Gets the Gmail API service using explicit path."""
    creds = None
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/gmail.send'])
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Error: Valid token.json not found for Gmail API.")
            return None
            
    return build('gmail', 'v1', credentials=creds)

def _send_email_task(to_email, subject, body, is_html, token_path):
    """Worker function to send email via Gmail API inside a thread."""
    try:
        service = get_gmail_service(token_path)
        if not service:
             # Fallback log if service fails inside thread
             print(f"FAILED (No Service): Email to {to_email}")
             return

        message = EmailMessage()
        message['To'] = to_email
        message['From'] = 'me'
        message['Subject'] = subject
        
        if is_html:
            message.set_content("Please enable HTML to view this message.")
            message.add_alternative(body, subtype='html')
        else:
            message.set_content(body)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        service.users().messages().send(userId="me", body=create_message).execute()
        print(f"SUCCESS: Email sent to {to_email} (Threaded)")
    except Exception as e:
        print(f"ERROR: Failed sending email to {to_email}: {e}")

def send_email_async(to_email, subject, body, is_html=False):
    """Submits email task to the thread pool."""
    try:
        token_path = os.path.join(current_app.root_path, 'token.json')
        email_executor.submit(_send_email_task, to_email, subject, body, is_html, token_path)
        return True
    except Exception as e:
        print(f"Error submitting email task: {e}")
        return False

def send_notification_email(to_email, subject, body):
    """Sends a generic notification email (Assumes HTML if body contains HTML tags, else Text)."""
    # Simple check for HTML tags
    is_html = '<br>' in body or '</p>' in body or '</table>' in body or 'html' in body.lower()
    return send_email_async(to_email, subject, body, is_html=is_html)

def send_otp(email, otp, purpose="Verification"):
    """Sends OTP via Email."""
    subject = f'OnlyElection OTP: {purpose}'
    body = f'Hello,\n\nYour One-Time Password (OTP) for {purpose} is:\n\n{otp}\n\nThis OTP is valid for 10 minutes.\n\nIf you did not request this, please ignore this email.'
    return send_email_async(email, subject, body, is_html=False)

def send_password_email(email, username, password):
    """Sends Generated Credentials via Email."""
    subject = 'Election Admin Credentials'
    body = f'Hello,\n\nYou have been added as an admin.\nUsername: {username}\nPassword: {password}\n\nPlease login and change your password immediately.'
    return send_email_async(email, subject, body, is_html=False)
