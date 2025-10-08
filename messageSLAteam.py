from config.gmailConfig import GmailClient
from config.sheetsConfig import slaList, scripts
from config.driveConfig import driveClient
import datetime
from config.jsonFiles import DriveFiles

UPLOAD_FILES_ID = DriveFiles["Automation"]["2. Content to Send Off"]
AWAITING_ASSESSMENT_ID = DriveFiles["Automation"]["3. Awaiting Assessment"]
emails = slaList.col_values(1)[1:]
gmailClient = GmailClient()

##Get the script files
currentScripts = scripts.get_all_records()
scriptIds = []
for s in currentScripts: ##Only check the scripts with TBA checked
    if s["Published"] == "TBA":
        scriptIds.append(s["Id"])

print("requesting")
files = driveClient.list_files_in_folder(UPLOAD_FILES_ID)
for file in files:
    ##Check the script files
    fileId = file["id"]
    for s in scriptIds: ##Continue to the next iteration only if the spreadsheet has been uploaded
        ##This implies that the team are already aware of the upload.
        alreadySent = False
        if s == fileId:
            alreadySent = True
    if alreadySent:
        continue
    fileName = file["name"]
    driveLink = driveClient.makePublicLink(fileId)
    ##Send email to notify the SLA team that the file has been uploaded
    emailName = "Harley"
    emailText = "Hello everyone, \nNew content has been uploaded to the google drive"
    emailText += " please review and provide feedback by replying to this email.\n"
    emailText += f"The content can be found at: {driveLink}\nkind regards \n- wellbeing@UC content team "
    ##Create the email chain from the list for emails
    emailChain = ", ".join(emails)
    ##Upload Link to the drive
    ##UPDATE THE SCRIPTS DATABASE
    todaysDate = datetime.date.today().strftime("%Y-%m-%d")
    scripts.append_row([todaysDate, "TBA",  driveLink, fileId, ""])

    gmailClient.send_message(emailChain, "New Content Generated for SLA", emailText)

    ##Move the file to await assessment
    driveClient.move_file(fileId, AWAITING_ASSESSMENT_ID)



    

    




