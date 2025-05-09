import os
from dotenv import load_dotenv

# Loading variables from .env file
load_dotenv()

# Debug output for environment variables
print(f"ALLOWED_USERS_0 from env: {os.getenv('ALLOWED_USERS_0')}")

# User groups for routing
ALLOWED_USERS_0 = [int(id.strip()) for id in os.getenv("ALLOWED_USERS_0", "").split(",") if id.strip()]  # First user group
print(f"Parsed ALLOWED_USERS_0: {ALLOWED_USERS_0}")
ALLOWED_USERS_1 = [int(id.strip()) for id in os.getenv("ALLOWED_USERS_1", "").split(",") if id.strip()]  # Second user group
#ALLOWED_USERS_2 = [int(id.strip()) for id in os.getenv("ALLOWED_USERS_2", "").split(",") if id.strip()]  # Third user group

# Main settings - Root folder IDs on Google Drive
MAIN_FOLDER_ID_0 = os.getenv("MAIN_FOLDER_ID_0")  # Root folder ID for group 0
MAIN_FOLDER_ID_1 = os.getenv("MAIN_FOLDER_ID_1")  # Root folder ID for group 1
#MAIN_FOLDER_ID_2 = os.getenv("MAIN_FOLDER_ID_2")  # Root folder ID for group 2

# API keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# GOOGLE_SCRIPT_API_KEY removed - API security disabled

# Google Script URLs for different groups
GOOGLE_SCRIPT_URL_0 = os.getenv("GOOGLE_SCRIPT_URL_0")  # URL for group 0
GOOGLE_SCRIPT_URL_1 = os.getenv("GOOGLE_SCRIPT_URL_1")  # URL for group 1
#GOOGLE_SCRIPT_URL_2 = os.getenv("GOOGLE_SCRIPT_URL_2")  # URL for group 2

MAX_PDF_PAGES = 5  # Maximum number of PDF pages to analyze in one request

# OpenAI Models
MODELS = {
    'main': "gpt-4.1-mini",       # for text translation
    'short': "gpt-4.1",           # for short phrases
    'voice': "gpt-4o-mini-transcribe",  # for speech recognition
    'vision': "gpt-4.1",          # for images
    'tts': "tts-1"               # for voice generation
}

# OpenAI API timeout settings (in seconds)
OPENAI_REQUEST_TIMEOUT = 60  # Overall request timeout
OPENAI_MAX_RETRIES = 3       # Maximum number of retry attempts
OPENAI_RETRY_DELAY = 2       # Initial delay between retries (seconds)

# Allowed file types
ALLOWED_FILE_TYPES = ['photo', 'document']

# Maximum file size in bytes (5 MB)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes

# Prompt for receipt analysis (in English)
RECEIPT_SYSTEM_PROMPT = """You are a professional expert in receipt recognition and analysis.
Your task is to extract the following information from a receipt:
1. Total amount including taxes
2. Currency in Iso format
3. Date and time of the receipt
4. Simple list of purchased items (just names, no details)

Return the information strictly in the following JSON format:
{
  "total_amount": number,
  "currency": "string",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "items": "comma separated list of item names"
}

If any information is missing, set the value to null.
Return only the raw JSON without any additional explanations, markdown formatting, or code block markers (like ```json or ```).
Be precise and accurate in extracting the information."""

# User prompt for receipt analysis
RECEIPT_USER_PROMPT = """Analyze this receipt and extract all required information in the structured format."""

# Receipt message tracking settings
MESSAGES_TRACKING_FILE = "receipt_messages.json"  # Path to temporary file
MAX_RECORD_AGE = 14 * 24 * 60 * 60  # Maximum time to keep records (14 days in seconds)
CLEANUP_INTERVAL = 3 * 24 * 60 * 60  # Cleanup check interval (3 days in seconds)

# Google Drive folder URL format
GOOGLE_DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/{folder_id}"

# Maximum length of items text in Telegram messages
MAX_ITEMS_TEXT_LENGTH = 30

# Message templates for specific user groups
# Available placeholders:
# {folder_url} - URL to the folder in Google Drive
GROUP_MESSAGE_TEMPLATES = {
    # Group 0 template
    0: """
*❗IMPORTANT*
Reply to THIS message to add Notes.\n

Add "*MY*" at the beginning for reimbursement, or "*REP*" for company spent reporting.\n
[Folder]({folder_url})
""",
    # Group 1 template - can be None or different message
    #1: None,
    # Add more group templates as needed
}
