from openai import OpenAI, RateLimitError, APIError, APIConnectionError, Timeout
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    filename="Logging/configLogs/openai_client.log",       # log file name
    filemode="a",                       # "w" to overwrite, "a" to append
    format="%(asctime)s - %(levelname)s - %(message)s"
)

##Attempt to connect to the openai API
try:
    openaiClient = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))
    logging.info("Openai client successfully created")
except EnvironmentError as e:
    logging.error(f"AI Key is not present: {e}")
    openaiClient = None
except Exception as e:
    logging.error(f"Unexpected exception: {e}")
    openaiClient = None


