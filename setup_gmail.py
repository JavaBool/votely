import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def setup_gmail_auth():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("ERROR: 'credentials.json' not found!")
                print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
                print("2. Create a project and enable 'Gmail API'")
                print("3. Go to Credentials -> Create Credentials -> OAuth Client ID -> Desktop App")
                print("4. Download the JSON file, rename it to 'credentials.json', and place it in this folder.")
                return
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            

        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("Successfully authenticated! 'token.json' has been created.")

if __name__ == '__main__':
    setup_gmail_auth()
