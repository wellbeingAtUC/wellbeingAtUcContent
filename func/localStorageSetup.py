import os

##Create the local storage folder
os.makedirs("localStorage",exist_ok=True)

storageSubs = [
    "audioDrafts",
    "convertedVideos",
    "downloads",
    "uploadVideos",
    "videos"
]

for fileName in storageSubs:
    name = "localStorage/"+fileName
    os.makedirs(name, exist_ok=True)

print("localStorage directories created")