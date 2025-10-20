import os
import subprocess
from config.jsonFiles import DriveFiles
from config.driveConfig import driveClient
import datetime
import shutil

DRIVE_SOURCE = DriveFiles["User Content"]["Content Video"]
DRIVE_DEST = DriveFiles["Automation"]["1.2. VIDEO FILES"]

def mp4converter(input_path):
    try:
        uniqueId = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        output_path = "localStorage/convertedVideos/" + uniqueId + ".mp4"
        if input_path.lower().endswith((
                ".mkv", ".avi", ".mov", ".flv", ".webm", ".wmv", ".m4v"
            )):

            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                output_path
            ]

            subprocess.run(cmd, check=True)
            print(f"Converted: {input_path} -> {output_path}")
        elif input_path.lower().endswith(".mp4"):
            shutil.copy(input_path, output_path)
            print(f"No conversion nessesary: {input_path}, moved to {output_path}")
        return output_path

    except subprocess.CalledProcessError:
        print(f"Failed to convert: {input_path}")
        return None



def batch_convert(videosToConvert):
    for video in videosToConvert:
        videoId = video["id"]
        videoName = video["name"]
        localPath = driveClient.download_file(videoId, videoName)
        # Determines conversion target (full path to the video file to be converted)
        if localPath.lower().endswith(( ##Only deal with video files and ignore all others
                ".mkv", ".avi", ".mov", ".flv", ".webm", ".wmv", ".m4v", ".mp4"
            )):
            outputFile = mp4converter(localPath)
            ##Upload the mp4 file to the drive
            driveClient.upload_file(outputFile, DRIVE_DEST, "video/mp4")
            os.remove(outputFile)

        ##Remove the original file in the drive 
        driveClient.delete_file(videoId)
        ##Remove the local files
        os.remove(localPath)
        
videosToConvert = driveClient.list_files_in_folder(DRIVE_SOURCE) ##Get files from the videos that we want to upload
batch_convert(videosToConvert)
        
