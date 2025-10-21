import os
import logging
import time
import random
import google.auth.transport.requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

##Logging Setup
##---------------------------
logging.basicConfig(
    filename="Logging/configLogs/youtube_config.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

##YT API Scope
SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]


class YoutubeUploader:
    def __init__(self):
        self._credPath = "config/credentials/credentialsYoutube.json"
        self._tokenPath = "config/credentials/tokenYoutube.json"
        self._client = None
        self.authenticate()

    def authenticate(self):
        creds = None
        if os.path.exists(self._tokenPath):
            creds = Credentials.from_authorized_user_file(self._tokenPath, SCOPE)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(google.auth.transport.requests.Request())
                logging.info("Youtube token refreshed successfully.")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credPath, 
                    SCOPE
                )
                creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
                logging.info("Youtube authorisation completed, new token saved.")
            with open(self._tokenPath, "w") as token:
                token.write(creds.to_json())
        self._client = build("youtube", "v3", credentials=creds)

    def upload_video(self, file_path, title, description="", category="22", privacy="unlisted", tags=None):
        """
        Upload a video to YouTube.
        cetegory 22 = People and Blogs (Default)
        privacy can be public, unlisted or private
        """
        try:
            body={
                "snippet":{
                    "title":title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": category
                },
                "status":{"privacyStatus":privacy}
            }

            media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype='video/*')
            request = self._client.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logging.info(f"Upload progress: {int(status.progress()*100)}%")
                    print(f"Upload progress: {int(status.progress()*100)}%")

            videoId = response.get("id")
            youtubeLink = f"https://youtu.be/{videoId}"
            logging.info(f"Uploaded successfully: {youtubeLink}")
            print(f"Uploaded successfully: {youtubeLink}")
            return youtubeLink
        except HttpError as e:
            logging.error(f"Youtube upload error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error when uploading to youtube: {e}")
            return None
        
youtubeUploader = YoutubeUploader()

