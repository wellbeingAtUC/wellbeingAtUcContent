import json


##Drive files information
with open("config/jsonFiles/driveFiles.json", "r") as file:
    DriveFiles = json.load(file)

##List of admin emails
with open("config/jsonFiles/adminEmails.json") as file:
    AdminEmails = json.load(file)