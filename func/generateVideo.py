from config.driveConfig import driveClient
import random
from config.jsonFiles import DriveFiles
from mutagen.mp3 import MP3
import subprocess
import os
import logging

VIDEO_CLIPS = DriveFiles["Automation"]["1.2. VIDEO FILES"]

def generateVideo(voiceFile):
    try:
        videoClips = driveClient.list_files_in_folder(VIDEO_CLIPS)

            ##Prepare videos for the audio file
        try:
            length = MP3(voiceFile).info.length
        except Exception as e:
            logging.error(f"Unable to read MP3 metadata: {e}")
            raise 
        noVids = max(1, int(length//10 + 1)) ##Get the number of required videos
        if noVids > len(videoClips):
            logging.warning(f"Requested {noVids} but only had {len(videoClips)}")
            noVids = len(videoClips)
        listOfNumbers = random.sample(range(len(videoClips)), noVids)
        vidsList = []
        count = 1
        for i in listOfNumbers:
            fileId = videoClips[i]["id"]
            tempName = f"stitch_{count}.mp4"
            driveClient.download_file(fileId, tempName)
            vidsList.append(tempName)
            count += 1
        
        ##Create a text file for all the videos
        videosTxt = "localStorage/downloads/videos.txt"
        with open(videosTxt, "w") as f:
            for vid in vidsList:
                f.write(f"file '{vid}'\n")
                print("This works")

            ##Stitch all videos together with ffmpeg
        command = [
                "ffmpeg", 
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                f"{videosTxt}",
                "-c",
                "copy",
                "localStorage/videos/video.mp4"
            ]

        result = subprocess.run(command)
        
        logging.info("Video successfully created")
        

        ##Remove all of the files
        for vid in vidsList:
            try:
                os.remove("localStorage/downloads/"+ vid)
            except Exception as e:
                logging.error(f"Could not delete {vid}: {e}")
        os.remove(videosTxt)
        return "localStorage/videos/video.mp4"
    except Exception as e:
        logging.info(f"Error generating video: {e}")
        return None

    



