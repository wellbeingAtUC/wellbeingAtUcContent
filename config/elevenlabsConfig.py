from elevenlabs.client import ElevenLabs
import logging
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    filename="Logging/configLogs/elevenlabs_config.log",       # log file name
    filemode="a",                       # "w" to overwrite, "a" to append
    format="%(asctime)s - %(levelname)s - %(message)s"
)
try:
    elClient = ElevenLabs(api_key=os.getenv("ELEVENLABS_KEY"))
    logging.info("Successful Elevenlabs implementation")
except Exception as e:
    logging.error(f"Unable to establish Elevenlabs client: {e}")
    elClient = None
