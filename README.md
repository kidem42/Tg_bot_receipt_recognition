# Telegram Receipt Recognition Bot

## Overview
The Telegram Receipt Bot is a Telegram bot that allows users to upload receipts (images' formats and PDF are supported). The bot automatically processes these documents using OpenAI's computer vision capabilities to extract structured information and stores both the original files and the processed data in Google Drive and Google Sheets.

## Features
- Upload photos and document files (PDFs, images) via Telegram
- Automatic receipt information extraction:
  - Total amount and taxes
  - Currency
  - Date and time
  - List of purchased items (symply listed with no strong focus on that part)
- Multi-page PDF document support
- Image conversion from various formats to ones compatible with OpenAI's API
- Document storage in Google Drive with user-specific folders based on telegram user ID in the name 
- Structured data storage in Google Sheets
- User permission system with group-based access control
- Secure API communication with Google Apps Script

## Architecture

### Components
1. **Telegram Bot Interface**: Handles user interactions via the Telegram API
2. **File Processing Pipeline**: Converts, uploads and processes various file formats
3. **OpenAI Integration**: Extracts structured data from receipt images
4. **Google Drive Integration**: Stores files in user-specific folders
5. **Google Sheets Integration**: Records extracted receipt data for analysis
6. **User Authentication System**: Controls access via configurable user groups

### Key Modules
- `account_router.py`: Manages user permissions and routes to appropriate Google resources
- `google_script.py`: Handles communication with Google Apps Script
- `openai_client.py`: Processes images using OpenAI's vision capabilities
- `pdf_to_image.py`: Converts PDF documents to images for processing
- `img_converter.py`: Converts various image formats to ones compatible with OpenAI
- `telegram_handler.py`: Handles Telegram bot interactions and commands
- `google_sheets.py`: Manages the creation of records in Google Sheets
- `file_processor.py`: Coordinates the file processing workflow

### Google Apps Script Component
- `pyHandler.gs`: Google Apps Script web app that handles Drive/Sheets operations

## Setup Instructions

### Prerequisites
- Python 3.8+
- A Telegram Bot Token (create one via BotFather)
- An OpenAI API key
- A Google account with access to Google Drive and Google Sheets

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/telegram-receipt-bot.git
cd telegram-receipt-bot
```

2. Install required dependencies
```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on the provided `.env.example`
```bash
cp .env.example .env
```

4. Edit the `.env` file with your API keys and configuration:
```
TELEGRAM_TOKEN=your_telegram_token_here
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_SCRIPT_API_KEY=your_random_api_key_here  # Should match value in pyHandler.gs

# Google Script URLs for different user groups
GOOGLE_SCRIPT_URL_0=your_google_script_url_for_group_0

# User groups for routing (comma-separated list of user IDs)
ALLOWED_USERS_0=user_id_1,user_id_2,user_id_3

# Main settings - Root folder IDs on Google Drive
MAIN_FOLDER_ID_0=your_folder_id_for_group_0
```

### Google Apps Script Setup

1. Create a new Google Sheet where you want to store the receipt data
2. Open the Script Editor (Extensions → Apps Script)
3. Copy the content of `pyHandler.gs` into the editor
4. Replace the placeholder `'GOOGLE_SCRIPT_API_KEY'` with the same key you specified in your `.env` file
5. Deploy the script as a web app:
   - Click Deploy → New Deployment
   - Select "Web app" as the type
   - Set "Execute as" to "Me"
   - Set "Who has access" to "Anyone"
   - Click "Deploy"
6. Copy the provided web app URL and paste it as `GOOGLE_SCRIPT_URL_0` in your `.env` file

### Google Drive Setup

1. Create a folder in Google Drive where you want to store receipt files
2. Right-click the folder and select "Get link"
3. From the sharing link, extract the folder ID (the part after `/folders/` in the URL)
4. Add this folder ID as `MAIN_FOLDER_ID_0` in your `.env` file

### Testing the Setup

1. Run the test script to verify Google API connection:
```bash
python test_google_api.py <your_telegram_user_id> <your_telegram_username>
```

2. If everything is working correctly, you should see "All tests completed successfully!"

### Running the Bot

1. Start the bot:
```bash
python main.py
```

2. Send a message to your bot on Telegram, it should respond with a welcome message if you're in the allowed users list

## Usage

- Send a photo of a receipt directly to the bot
- Send a document (PDF or image) containing receipt information
- The bot will process the image, extract receipt data, and respond with the extracted information
- All files are stored in your Google Drive, and receipt data is recorded in Google Sheets

## Security

- The API key for Google Apps Script is secured with SHA-256 signatures
- Request timestamp validation prevents replay attacks
- User permission control limits access to authorized users only
- File size limits prevent abuse (5MB maximum file size)

## Limitations

- Maximum file size: 5MB
- Maximum PDF pages processed at once: 5 (configurable in `config.py`)
- Video and audio files are not supported

## Dependencies

This project uses the following open-source libraries:

- python-telegram-bot (>=13.0) - LGPL-3.0
- openai (>=1.0.0) - MIT
- google-auth (>=2.0.0) - Apache-2.0
- google-api-python-client (>=2.0.0) - Apache-2.0
- python-dotenv (>=0.19.0) - BSD-3-Clause
- requests (>=2.25.0) - Apache-2.0
- Pillow (>=9.0.0) - HPND
- pillow-heif (>=0.10.0) - BSD-3-Clause
- pdf2image (>=1.16.0) - MIT

Full license texts for these dependencies can be found in the `licenses` directory.

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3) - see the [LICENSE](LICENSE) file for details.
