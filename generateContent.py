from config.sheetsConfig import contentThemes, production
from config.openaiConfig import openaiClient
from config.driveConfig import driveClient
from config.elevenlabsConfig import elClient
from openai import RateLimitError, APIError, APIConnectionError, Timeout
import os
import pdfplumber
import logging
import time
from Logging.ErrorReporting import ErrorNotify
from config.jsonFiles import DriveFiles
import datetime


logging.basicConfig(
    level=logging.INFO,
    filename="Logging/automationLogs/generate_content.log",       # log file name
    filemode="a",                       # "w" to overwrite, "a" to append
    format="%(asctime)s - %(levelname)s - %(message)s",
    force = True
)

##Set up the handler/ Logger
handler = ErrorNotify()
logging.getLogger().addHandler(handler)

AUDIO_DEST_FOLDER = DriveFiles["Automation"]["1. Add Audio"]
COMPRESSED_AUDIO_FOLDER = "compressedAudio"
AUDIO_DRAFTS_FOLDER = "localStorage/audioDrafts"

def getTodaysTheme(contentThemes): ##Sould only ever return 1 dictionary for todays theme
    count = 2
    outRow = []
    rows = contentThemes.get_all_records()
    ##Return all the items in the spreadsheet that have Used == 1
    
    for row in rows:
        try:
            used = int(row["Used"]) ##Test that the data value for the Used column is valid
        except Exception as e:
            logging.warning(f"Used value for row {count} of the Content Themes spreadsheet is not 1 or 0")
            contentThemes.update_cell(count, 4, 0) ###Set the invalid Used row to 0
            used = 0
        if used >= 1:
            outRow.append(row)
            row["id"] = count
        count += 1
    ##Error handling
    if len(outRow) == 0: ##If all the Used rows are 0, return to the top row
        contentThemes.update_cell(2, 4, 1) ##Set the top row to 1
        outRow = rows[0] ##Return the top row for content generation
        outRow["id"] = 2 ##Record the position of the row
    elif len(outRow) > 1: ##If there are more than 1 rows with the Used column set to 1
        topRow = outRow[0] ##Save the top most element
        for row in outRow: ##Set all row elements with 1 back to 0
            contentThemes.update_cell(row["id"], 4, 0)
        contentThemes.update_cell(topRow["id"], 4, 1) ##Set the top element with used 1 back to 1
        outRow = topRow
    else:
        outRow = outRow[0]
    return outRow, len(rows)

def main():
    print("Loading todays theme")
    logging.info("\n\n*****************GENERATING CONTENT*********************")
    todaysTheme, rowCount = getTodaysTheme(contentThemes) ##Return todays theme for content generation
    logging.info("(1/8) -> Theme successfully generated: {}".format(todaysTheme["Theme"]))

    ##Load the book chapter from the drive
    #-------------------------------------
    bookChapters = {
        3: '1vfwQt9MgaE2J6tiN0mxFHjh-KkzjZ2cx',
        2: '1uqBKCtpzxCcoFKbbz8-NnTLPnksrXi3G',
        1: '108DBJkVciwSwnnCCphIdZvMOXUevmH85',
    }

    ##Select the book chapter based on the data from todays theme
    print("Loading the book")
    chapterId = bookChapters[todaysTheme["Chapter"]]
    workingChapter = driveClient.download_file(chapterId, "workingChapter.pdf")
    if workingChapter is None:
        logging.error("Could not download chapter, see drive_config.log for details")
        return False ##Log where the error occurred and stop the iteration
    logging.info(f"(2/8) -> Successfully downloaded {workingChapter}")

    ##Extract the text from the pdf file to be fed into chat gpt
    print("extracting the text")
    chapterText = ""
    try:
        with pdfplumber.open(workingChapter) as pdf:
            for page in pdf.pages:
                chapterText += page.extract_text() + "\n"
    except Exception as e:
        logging.error(f"unexpected error with pdfplumber: {e}")
        return False
    logging.info("(3/8) -> Pdf successfully extracted")

    ##Generate the prompt for the script
    theme = todaysTheme["Theme"]
    activity = todaysTheme["Activity"]

    ##This will generate a prompt for chat gpt for if there is or is not a prompt
    print("GPT prompt sent off")
    if not activity:
        prompt = f"Are you able to read the below text and create a 30 second to 1 minute text to speech script about {theme} The video should include an activiy that relates to the topic, preferbably with reference to the text. This request is automated so it would be great if you just return the script. The text is: {chapterText}"
    else:
        prompt = f"Are you able to read the below text and create a 30 second to 1 minute text to speech script about {theme}. The video should include an activity for the viewer based around {activity}. This request is automated so it would be great if you just return the script. The text is: {chapterText}"

    ##Load up the chatGPT request
    maxRetries = 5 ###Set the number of retries for the API requests
    ##Loop that retries the request to openai api
    for retry in range(1, maxRetries + 1):
        backOff = 2**retry
        try:
            response = openaiClient.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            draftScript = response.choices[0].message.content
            break ##No need to resume the loop
        except(RateLimitError, APIError, APIConnectionError, Timeout) as e:
            logging.warning(
                f"OpenAI API: {e}. Retrying in {backOff}... "
            )
            draftScript = None
            time.sleep(backOff)
        except Exception as e:
            logging.warning(f"Unexpected Error during OpenAI request: {e}, retrying in {backOff}")
            draftScript = None

    ##Stop execution if the script is not generated 
    if draftScript is None:
        logging.error("Failed to generate Draft script")
        return False    

    logging.info(f"(4/8) -> Draft Script Successfully generated")
    prompt = f"Could you please clean this script up to be entered directly into Elevenlabs text-to-speech. The result should just have the script with no directions, and please remove any title if there is one. the script is:  {draftScript}"

    ##Ask Chat gpt to edit the script
    print("GPT Edit prompt sent off")

    for retry in range(maxRetries + 1):
        backOff = 2**retry
        try:
            response = openaiClient.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            ##This will be the script for the new content audio
            script = response.choices[0].message.content
            break ##No need to re execute the loop
        except(RateLimitError, APIError, APIConnectionError, Timeout) as e:
            logging.warning(
                f"OpenAI API: {e}. Retrying in {backOff}... "
            )
            script = None
            time.sleep(backOff)
        except Exception as e:
            logging.warning(f"Unexpected Error during OpenAI request: {e}, retrying in {backOff}")
            script = None
    
    ##Stop execution if the script is not generated 
    if script is None:
        logging.error("Failed to generate Edited Script")
        return False    

    logging.info(f"(5/8) -> Script Successfully generated")
        
    
    ##Eleven labs audio generation
    ##------------------------------
    print("generating audio with eleven labs")

    for retry in range(maxRetries + 1):
        backOff = 2**retry
        try:
            audio = elClient.text_to_speech.convert(
                text=script,
                voice_id="bwBMii6YyaA3YprSpbXH",  # Use Ehssans voice
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            break
        except Exception as e:
            logging.warning(f"Error working with Eleven labs: {e}")
            audio = None
            time.sleep(backOff)
    if audio is None:
        logging.error("Unable to get audio file from Eleven labs, details in logging file")
        return False
    
    logging.info("(6/8) -> Successfully created audio file")

    try:
        # Convert generator into raw bytes
        audio_bytes = b"".join(audio)

        os.makedirs(AUDIO_DRAFTS_FOLDER, exist_ok=True)

        audioName = AUDIO_DRAFTS_FOLDER + "/" + theme.capitalize().strip() + ".mp3"
        # Save as MP3 file
        print("saving audio file")
        with open(audioName, "wb") as f:
            f.write(audio_bytes)
    except Exception as e:
        logging.error(f"Unable to save audio to local disk: {e}")
        return False
    
    logging.info(f"(7/8) -> Successfully saved the audio to {audioName}")

    
    ##Upload the audio file and update the google sheet
    print("Uploading to the drive")
    audioLink = driveClient.upload_file(audioName, AUDIO_DEST_FOLDER, "audio/mpeg")
    logging.info("(8/8) -> Audio uploaded to the drive")
    
    ##Update the sheets to generate the next round of countent

    print("updating the theme")
    contentThemes.update_cell(todaysTheme["id"], 4, 0)
    #Check if we are at the end of the list 
    if todaysTheme["id"] >= rowCount + 1:
        contentThemes.update_cell(2, 4, 1)
    else:
        contentThemes.update_cell(todaysTheme["id"] + 1, 4, 1)

    logging.info("Content themes spreadsheet updated")
    
    ##Uploading the script for later use with the date of construction
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") ##Get date time from now
    production.append_row([audioLink, script, today])

    ##Clean up the local files to save space
    os.remove(audioName)
    os.remove("localStorage/downloads/workingChapter.pdf")
    return True

if __name__ == "__main__":
    contentGenerated = main()
    if contentGenerated:
        logging.info("*******************CONTENT SUCCESSFULLY GENERATED**********************\n\n")