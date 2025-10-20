from config.sheetsConfig import scripts, published
from config.driveConfig import driveClient
from config.jsonFiles import DriveFiles
import logging
from Logging.ErrorReporting import ErrorNotify
import datetime
from config.gmailConfig import gmailClient
from config.openaiConfig import openaiClient
from openai import RateLimitError, APIError, APIConnectionError, Timeout
import time

logging.basicConfig(
    level=logging.INFO,
    filename="Logging/automationLogs/prepare_videos.log",       # log file name
    filemode="a",                       # "w" to overwrite, "a" to append
    format="%(asctime)s - %(levelname)s - %(message)s",
    force = True
)

##Set up the handler/ Logger
handler = ErrorNotify()
logging.getLogger().addHandler(handler)

logging.info("\n\n************************PREPARING VIDEOS*************************")
activeScripts = scripts.get_all_records()
DEST_FOLDER = DriveFiles["Automation"]["4. Publish to Youtube"]

for item in activeScripts:
    if item["Publish"] == "yes":
        ##Move to the publishing file
        driveClient.move_file(item["Id"], DEST_FOLDER)
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") ##Get date time from now
        scriptText = item["Script"]
        if scriptText != "":
            ##Generate a description paragraph
            ##Load up the chatGPT request
            maxRetries = 5 ###Set the number of retries for the API requests
            ##Loop that retries the request to openai api
            description = None
            prompt = f"Could you generate a one paragraph description for a youtube video using the attached script, this is an automated process so the answer should just be the description. The script is here: {scriptText}"
            for retry in range(1, maxRetries + 1):
                backOff = 2**retry
                try:
                    response = openaiClient.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    description = response.choices[0].message.content
                    break ##No need to resume the loop
                except(RateLimitError, APIError, APIConnectionError, Timeout) as e:
                    logging.warning(
                        f"OpenAI API: {e}. Retrying in {backOff}... "
                    )
                    description = None
                    time.sleep(backOff)
                except Exception as e:
                    logging.warning(f"Unexpected Error during OpenAI request: {e}, retrying in {backOff}")
                    description = None
            if description is not None:
                prompt = f"Could you please remove any extra text from the attached description of a youtube video, the result should only be the one paragraph description and no other text. The paragraph is here: {description}"
                for retry in range(1, maxRetries + 1):
                        backOff = 2**retry
                        try:
                            response = openaiClient.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": prompt}]
                            )
                            description = response.choices[0].message.content
                            break ##No need to resume the loop
                        except(RateLimitError, APIError, APIConnectionError, Timeout) as e:
                            logging.warning(
                                f"OpenAI API: {e}. Retrying in {backOff}... "
                            )
                            description = ""
                            time.sleep(backOff)
                        except Exception as e:
                            logging.warning(f"Unexpected Error during OpenAI request: {e}, retrying in {backOff}")
                            description = ""
        else:
            description = None
        ##Update the current data for the publishing spreadsheet
        if description is None:
            description = ""
        published.append_row([item["Id"], "", "", item["Feedback"], today, "Awaiting Upload", item["Content Type"], "", item["Script"], description,"No"])

        ##Remove from the scripts spreadsheet
        idColumn = 5 ##The fifth column is the Id
        idCell = scripts.find(item["Id"], in_column=idColumn) ##Find the cell with the id
        logging.info("Updating the scripts spreadsheet")

        if idCell:
            scripts.delete_rows(idCell.row)
            logging.info("{} removed from scripts".format(item["Id"]))
        else:
            logging.warning("{} is not present in the script".format(item["Id"]))
        
        ##Record in the archive
    elif item["Publish"] == "no":
        ##Remove the element from the script
        idColumn = 5 ##THe fifth column is the ID
        idCell = scripts.find(item["Id"], in_column=idColumn)
        if idCell:
            scripts.delete_rows(idCell.row)
            logging.info("{} removed from scripts".format(item["Id"]))
        else:
            logging.warning("{} is not present in the script".format(item["Id"]))

        ##Remove the video in the content file
        driveClient.delete_file(item["Id"]) ##Remove the file from the 

logging.info("***********************VIDEOS PREPARED*********************\n\n")


