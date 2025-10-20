from config.youtubeConfig import youtubeUploader
from config.driveConfig import driveClient
from config.jsonFiles import DriveFiles
from config.sheetsConfig import published
import os
import datetime

##Upload files from the drive in the 'Publish to youtube' folder
SOURCE_FILE = DriveFiles["Automation"]["4. Publish to Youtube"]
ARCHIVE_FOLDER = DriveFiles["Automation"]["X. ARCHIVE CONTENT"]

filesToPublish = driveClient.list_files_in_folder(SOURCE_FILE)

##Columns in the 'published' spreadsheet
idColumn = 1
ytUploadColumn = 2
ytLinkColumn = 3
statusColumn = 6
titleColumn = 8
descColumn = 10
##Get todays date
today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") ##Get date time from now

for file in filesToPublish:
    id = file["id"]
    name = file["name"]
    ytTitle = os.path.splitext(name)[0]
    
    ##Download the file to upload to yt
    localName = driveClient.download_file(id, ytTitle)
    
    sheetCell = published.find(id, in_column=idColumn) ##Find the cell in the 'published' spreadsheet
    description = published.row_values(sheetCell.row)[descColumn - 1]
    ytLink = youtubeUploader.upload_video(localName, ytTitle, description=description) ##Upload to youtube
    print(f"{name} Uploaded to youtube as {ytLink}")
    
    published.update_cell(sheetCell.row, ytUploadColumn, today) ##Update the upload date
    published.update_cell(sheetCell.row, ytLinkColumn, ytLink) ##Add the YT link
    published.update_cell(sheetCell.row, statusColumn, "Uploaded") ##Set the status to Uploaded
    published.update_cell(sheetCell.row, titleColumn,  ytTitle)
    print("Spreadsheet updated")

    ##Move the file into the ARCHIVE folder in the drive
    driveClient.move_file(id, ARCHIVE_FOLDER)
    

    os.remove(localName) ##Remove the file in local storage
