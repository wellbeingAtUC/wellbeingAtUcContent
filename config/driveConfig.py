from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import os
import io
import time
import random
import logging
from config.jsonFiles import DriveFiles

# ----------------------------------
# Logging setup
# ----------------------------------
logging.basicConfig(
    filename="Logging/configLogs/drive_access.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

ROOT_FOLDER = DriveFiles["ROOT"]
LOCAL_DOWNLOAD_DIR = "localStorage/downloads"

#--------------------------------------------------
###RETRY HELPER
#--------------------------------------------------
def retry(func, *args, retries=5, **kwargs):
    """Retries Google API calls with an exponential backoff"""
    delay = 1
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            logging.error(f"HttpError on attempt {attempt}: {e}")
            if attempt == retries:
                logging.error("Max Retries Reached, was unable to access drive")
                raise
            sleepTime = delay + random.uniform(0, 0.5)
            logging.warning(f"Retrying in {sleepTime:.2f}s...")
            time.sleep(sleepTime)
            delay *= 2
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise
#------------------------------------------
#AUTHENTICATION
#------------------------------------------
class GoogleDrive:
    def __init__(self):

        tokenPath = "config/credentials/token.json"
        credPath = "config/credentials/credentialsDrive.json"
        creds = None
        try:
            # Load existing token if available
            if os.path.exists(tokenPath):
                creds = Credentials.from_authorized_user_file(tokenPath, SCOPES)

            # If no creds or invalid, refresh or reauthorize
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    logging.info("Token refreshed successfully.")
                else:
                    logging.warning("No valid credentials found, starting manual authorization...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credPath, SCOPES
                    )
                    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
                    logging.info("Authorization complete, saving new token.")

                # Save (new or refreshed) credentials
                with open(tokenPath, "w") as token:
                    token.write(creds.to_json())

        except Exception as e:
            logging.error(f"Authentication error: {e}")
            raise RuntimeError("Google Drive authentication failed. Please reauthorize.") from e

        os.makedirs(LOCAL_DOWNLOAD_DIR, exist_ok=True)
        try:
            self._client = build("drive", "v3", credentials=creds)
        except HttpError as e:
            logging.error(f"Failed to build Google Drive Client (API Error): {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error creating Drieve client: {e}")
            raise
        self._folders = {}
        for file in self.list_files_in_folder(ROOT_FOLDER):
            self._folders[file["id"]] = file["name"]
        if not self._folders:
            logging.warning(f"No files found in {ROOT_FOLDER}")
    
    #-----------------------------------------
    # DRIVE HELPERS
    #-----------------------------------------
    def list_files_in_folder(self, folder_id):
        def _list():
            query = f"'{folder_id}' in parents"
            results = self._client.files().list(q=query, fields="files(id, name)").execute()
            return results.get("files", [])
        return retry(_list)
    
    def getFolders(self):
        return self._folders
    
    def download_file(self, file_id, filename):
        localName = os.path.join(LOCAL_DOWNLOAD_DIR, filename)
        def _download():
            request = self._client.files().get_media(fileId=file_id)
            fh = io.FileIO(localName, "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logging.info(f"Download {int(status.progress()*100)}%.")
            fh.close()
            return localName
        try:
            path = retry(_download)
            logging.info(f"Downloaded {filename}")
            print(f"Downloaded {filename}")
            return path
        except Exception as e:
            logging.error(f"Failed to download {filename}: {e}")
            return None
    
    def upload_file(self, filename, folder_id, mime_type):
        file_metadata = {"name": os.path.basename(filename), "parents": [folder_id]}
        media = MediaFileUpload(filename, mimetype=mime_type, resumable=True)
        request = self._client.files().create(body=file_metadata, media_body=media, fields = "id")
        print(f"uploaded {filename} to folder {folder_id}")

        response = None
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress()*100)}%")
                    logging.info(f"Uploaded {int(status.progress()*100)}%")
            except HttpError as e:
                logging.error(f"Upload error: {e}")
                raise
        driveId = response.get("id")
        print(driveId)
        logging.info(f"Upload complete {filename} to {driveId}")
        return driveId

    def makePublicLink(self, fileId):
        ##Make the file publicly accessible
        try:
            self._client.permissions().create(
                fileId = fileId,
                body={"role":"reader", "type":"anyone"}
            ).execute()

            ##Return the google drive link
            link = f"https://drive.google.com/file/d/{fileId}/view?usp=sharing"
            logging.info(f"Publink created for file {fileId}: {link}")
            return link
        except Exception as e:
            logging.error(f"Failed to make file public {fileId}:{e}")
            return None
    
    def move_file(self, file_id, target_folder_id):
        # Get the current parents to remove
        try:
            file = self._client.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents", []))
            # Move the file
            file = self._client.files().update(
                fileId=file_id,
                addParents=target_folder_id,
                removeParents=previous_parents,
                fields="id, parents"
            ).execute()
            print(f"Moved file {file_id} to folder {target_folder_id}")
            logging.info(f"Moved file {file_id} to folder {target_folder_id}")
        except Exception as e:
            logging.error(f"Failed to move the file {file_id}: {e}")
            return None
        
    def delete_file(self, fileId):
        """Deletes a file in the google drive by its ID"""
        def _delete():
            return self._client.files().delete(fileId=fileId).execute()
        
        try:
            retry(_delete)
            logging.info(f"Delete file with ID {fileId}")
            print(f"Delete file with ID {fileId}")
            return True
        except HttpError as e:
            logging.error(f"HTTP error while deleting file {fileId}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error while deleting file {fileId}: {e}")
            return False
#Create Instance
driveClient = GoogleDrive()







