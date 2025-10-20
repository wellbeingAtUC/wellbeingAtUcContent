from config.driveConfig import driveClient
import os
import random
import subprocess
from faster_whisper import WhisperModel
import logging
from Logging.ErrorReporting import ErrorNotify
from config.jsonFiles import DriveFiles
from func.generateVideo import generateVideo
from config.sheetsConfig import production

LOCAL_AUDIO_DIR = "localStorage/audioDrafts"
AUDIO_SOURCE_DIR = DriveFiles["Automation"]["1. Add Audio"]
MUSIC_DIR = DriveFiles["Automation"]["1.1. MUSIC FILES"]
DEST_DIR = DriveFiles["Automation"]["2. Content to Send Off"]
ARCHIVE_FOLDER = DriveFiles["Automation"]["X. ARCHIVE CONTENT"]
VIDEO_UPLOADS_DIR = "localStorage/uploadVideos"
DOWNLOADS_FOLDER = "localStorage/downloads"
VIDEOS_FOLDER = "localStorage/videos"

logging.basicConfig(
    level=logging.INFO,
    filename="Logging/automationLogs/edit_content.log",       # log file name
    filemode="a",                       # "w" to overwrite, "a" to append
    format="%(asctime)s - %(levelname)s - %(message)s",
    force = True
)
##Set up the handler/ Logger
handler = ErrorNotify()
logging.getLogger().addHandler(handler)

logging.info("\n\n*********************EDITING CONTENT************************")
##Safe run subprocess
def safe_subprocess(command, description="command"):
    """Run a subprocess command safely with error handling"""
    try:
        subprocess.run(command, check=True)
        logging.info(f"{description} completed successfully")
    except subprocess.CalledProcessError as e:
        logging.error(f"{description} failed: {e}")
        return False
    return True

def format_time(seconds):
    millis = int((seconds - int(seconds))*1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02}.{millis:03}"
        
def validate_format(fileName : str, allowedExts : list):
    """Check that the file is in the correct format"""
    ext = os.path.splitext(fileName)[1].lower()
    return ext in allowedExts

def addVideo(video_path, audio_path, output_path):
        """
        Replace the audio of a video with a new audio track.
        The output will stop at the audio length.
        
        :param video_path: Path to the input video file
        :param audio_path: Path to the input audio file
        :param output_path: Path to the output file (default: output.mp4)
        """

        if not (validate_format(video_path, [".mp4"]) and validate_format(audio_path, [".mp3"])):
            return False ##Return false for incorrect format
        
        command = [
            "ffmpeg",
            "-i", video_path,        # input video
            "-i", audio_path,        # input audio
            "-map", "0:v",           # use video from first input
            "-map", "1:a",           # use audio from second input
            "-shortest",             # cut video to match audio length
            "-c:v", "copy",          # don't re-encode video
            "-c:a", "aac",           # encode audio to AAC
            "-b:a", "192k",          # audio bitrate
            output_path
        ]

        return safe_subprocess(command, "add video to content")

def main():
    ##Get all of the files in the edit Add audio file
    files = driveClient.list_files_in_folder(AUDIO_SOURCE_DIR)
    musicFiles = driveClient.list_files_in_folder(MUSIC_DIR)

    ##Check the music files, because it needs at lease one!
    if not musicFiles:
        logging.error("No music files in the drive")
        return False ##Stop the execution of the function
    

    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        
        #1. Download Content
        ##Check for the correct format of the audio file
        if not validate_format(file_name, [".mp3"]):
            logging.info(f"skipping {file_name} as it is not mp3")
            continue

        print(f"processing {file_name}...")
        try:
            driveClient.download_file(file_id, file_name)
            choice = random.randint(0, len(musicFiles) - 1)
            musicChoice = musicFiles[choice] ##Choose one of the music files
            driveClient.download_file(musicChoice["id"], musicChoice["name"])
            
            ##Get Subtitles with whisper
            subsFile = DOWNLOADS_FOLDER + "/subs.srt"

            ##Establish the files for use
            base_name, _ = os.path.splitext(file_name)
            output_file = os.path.join(LOCAL_AUDIO_DIR, f"mixed_{base_name}.mp3")
            local_file = os.path.join(DOWNLOADS_FOLDER, file_name)
            localMusic = os.path.join(DOWNLOADS_FOLDER, musicChoice["name"])

            try:
                model = WhisperModel("small", device="cpu", compute_type="int8")
                logging.info(f"Successfully loaded whisper Model: {model}")
                segments, info = model.transcribe(local_file, beam_size=5)
                with open(subsFile, "w", encoding="utf-8") as srtFile:
                    ##Convert seconds to srt timestamp format
                    for i, segment in enumerate(segments, start=1):
                        
                        start = segment.start
                        end = segment.end
                        text = segment.text.strip()

                        srtFile.write(f"{i}\n{format_time(start)} --> {format_time(end)}\n{text}\n\n")
                logging.info(f"Successfully transcribed subtitles for {local_file}")
            except Exception as e:
                logging.error(f"Whisper transcription failed for {file_name}: {e}")
                return False ##Stop excecution
            

            ##Put together with music
            command = [
                    "ffmpeg",
                    "-y",  # overwrite if exists
                    "-i", local_file,         # voice input
                    "-i", localMusic,         # music input
                    "-filter_complex",
                    "[0:a]volume=1.1[a0];"    # keep voice as-is
                    "[1:a]volume=0.2[a1];"    # lower music volume (20%)
                    "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[a]",  
                    "-map", "[a]",
                    "-c:a", "mp3",            # output as mp3
                    output_file
                ]
            
            if not safe_subprocess(command, "adding music to content"):
                continue
            

            audioMaster = output_file
            final = os.path.join(VIDEO_UPLOADS_DIR, "nosub.mp4")
            inputVideo = generateVideo(output_file) ###Generate video
            if not addVideo(inputVideo, audioMaster, final):
                continue

            finalWithSubs = os.path.join(VIDEO_UPLOADS_DIR, f"{base_name}.mp4")
            ##Add subtitles to the video
            subtitlesCommand = [
                "ffmpeg",
                "-i",
                final,
                "-vf",
                f"subtitles={subsFile}",
                "-c:a",
                "copy",
                finalWithSubs
            ]

            if not safe_subprocess(subtitlesCommand, "Adding subtitles"):
                continue ##Continue if unable to add subtitles

            
            ##Upload the audio with music
            videoId = driveClient.upload_file(finalWithSubs, DEST_DIR, "video/mp4")
            logging.info(f"Successfully uploaded {finalWithSubs} to the drive")
            # Move originals to archive
            driveClient.move_file(file_id, ARCHIVE_FOLDER)
            logging.info(f"Successfully moved the audio file to the Archive")

            ##Update the progress spreadsheet with the script
            productionCell = production.find(file_id, in_column=1)

            ##This allows the script to be associated with the video created
            if productionCell is not None:
                production.update_cell(productionCell.row, 4,videoId)

        except Exception as e:
            logging.error(f"Unexpected error processing {file_name}: {e}")
        finally: ##Remove all temp files from local storage
            for f in [local_file, localMusic, output_file, final, finalWithSubs, subsFile, inputVideo]:
                if f and os.path.exists(f):
                    os.remove(f)
    return True

if __name__ == "__main__":
    if main():
        logging.info("*************************CONTENT SUCCESSFULLY EDITED*****************************\n\n")