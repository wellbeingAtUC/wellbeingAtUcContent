import base64
import os.path
from email.message import EmailMessage
from typing import Optional
import logging
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Gmail API scope for sending mail 
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
logging.basicConfig(
    level=logging.INFO,
    filename="Logging/configLogs/gmail_config.log",       # log file name
    filemode="a",                       # "w" to overwrite, "a" to append
    format="%(asctime)s - %(levelname)s - %(message)s",
)

gmailToken = "config/credentials/tokenGmail.json"
credentialsGmail = "config/credentials/credentialsGmail.json"

class GmailClient:
    def __init__(self, tokenFile = gmailToken, credentialsFile = credentialsGmail):
        self._client = None
        self._tokenFile = tokenFile
        self._credentialsFile = credentialsFile
        self._auth()
    def _auth(self):
        creds: Optional[Credentials] = None
        try:
            if os.path.exists(self._tokenFile):
                creds = Credentials.from_authorized_user_file(self._tokenFile, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self._credentialsFile):
                        raise FileNotFoundError(f"Missing credentials file: {self._credentialsFile}")
                    flow = InstalledAppFlow.from_client_secrets_file(self._credentialsFile, SCOPES)
                    creds = flow.run_local_server(
                        port=0,
                        access_type="offline",
                        prompt="consent"
                        )

                with open(self._tokenFile, "w") as token:
                    token.write(creds.to_json())
            
            self._client = build("gmail", "v1", credentials=creds)
            logging.info("Gmail Client successfully established")
        except Exception as e:
            logging.error(f"Gmail authentication failed: {e}")
            self._client = None

    def send_message(self, to:str, subject:str, body:str, html: bool = False):
        """Send an email via the gmail account: wellbeingatuc@gmail.com"""
        
        if self._client is None: ##The client is not authenticated, thus no email can be sent
            logging.error(f"Gmail not authenticated, email could not be sent to: {to}")
            return False
        
        ##Validate email format
        if "@" not in to:
            logging.warning(f"{to} is not an email address, suggest removal - email not sent")
            return False
        
        maxRetries = 5
        for retry in range(1, maxRetries + 1):
            backOff = 2**retry
            try:
                message = EmailMessage()
                message["To"] = to
                message["From"] = "me"
                message["Subject"] = subject

                if html:
                    message.add_alternative(body, subtype="html")
                else:
                    message.set_content(body)

                encodedMessage = base64.urlsafe_b64encode(message.as_bytes()).decode()
                createMessage = {"raw": encodedMessage}

                sendResult = self._client.users().messages().send(userId="me", body=createMessage).execute()
                logging.info(f"Email sent to {to}, Message ID: {sendResult.get('id')}")
                return True ##Break the chain and return that the email is sent
            
            except HttpError as e:
                logging.error(f"Gmail API error: {e} Retrying in {backOff} seconds")
            except Exception as e:
                logging.error(f"Failed to send email: {e}, Retrying in {backOff} seconds")
            time.sleep(backOff)
            
        return False ##Only return False if the email fails all times
    
gmailClient = GmailClient()
