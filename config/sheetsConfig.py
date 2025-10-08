import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import SpreadsheetNotFound, APIError

# ----------------------------------
# Logging setup
# ----------------------------------
logging.basicConfig(
    filename="Logging/configLogs/sheets_access.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

credFile = "config/credentials/credentialsSheets.json"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credFile, SCOPE)
except FileNotFoundError: ##If there is no credentials file
    logging.error("No credentials file found for the google sheets, login to google cloud and set up")
    raise
except Exception as e: ##If there is an error with loading the credentials
    logging.error(f"Error loading credentials: {e}")
    raise

try:
    client = gspread.authorize(credentials)
    logging.info("successfully authorised Google Sheets CLient")
except Exception as e: ##If there is any issue with loading the google sheets file
    logging.error(f"Failed to authorise Google Sheets client: {e}")
    raise

##Function to safely open google sheets
def openSheet(sheetName):
    """Safely open a Google Sheet by name with error handling."""
    try:
        sheet = client.open(sheetName).sheet1
        logging.info(f"Successfully opened sheet: {sheetName}")
        return sheet
    except SpreadsheetNotFound:
        logging.error(f"Spreadsheet '{sheetName}' not found or access denied.")
        return None
    except APIError as e:
        logging.error(f"APIError while accessing '{sheetName}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error opening '{sheetName}': {e}")
        return None

##Google Sheets Returned
contentThemes = openSheet("Content Themes")
scripts = openSheet("Scripts")
slaList = openSheet("SLA Emails")

if not all([contentThemes, scripts, slaList]):
    logging.warning("One or more sheets failed to open. Check logs for details.")



