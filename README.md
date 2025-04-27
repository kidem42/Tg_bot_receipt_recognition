# Telegram Receipt Recognition Bot

## Overview
The Telegram Receipt Bot is a Telegram bot that allows users to upload receipts (images' formats and PDF are supported). The bot automatically processes these documents using OpenAI's computer vision capabilities to extract structured information and stores both the original files and the processed data in Google Drive and Google Sheets.

## Features
- Upload photos and document files (PDFs, images) via Telegram
- Automatic receipt information extraction:
  - Total amount
  - Currency
  - Date and time
  - List of purchased items (simply listed with no strong focus on that part)
- Add notes to receipts by replying to the bot's messages
- Notes are stored in Google Sheets alongside receipt data
- Group-specific template messages with Markdown formatting and folder links
- Automatic cleanup of old message tracking records (after 14 days)
- Multi-page PDF document support with batch analysis
- Image conversion from various formats to ones compatible with OpenAI's API
- Document storage in Google Drive with user-specific folders based on telegram user ID in the name 
- Structured data storage in Google Sheets with configurable columns
- User permission system with group-based access control
- UUID-based record tracking to ensure notes are added to the correct receipts regardless of row position

## Recent Updates
- Added robust retry mechanism with exponential backoff for API calls
- Enhanced multi-page PDF support with batch analysis for better handling of multi-page receipts
- Improved group-specific template messages:
  - Added Google Drive folder URL in template messages
  - Support for Markdown formatting (bold text) in templates
  - Templates can include instructions for users (e.g., how to add notes)
  - Only shown to users in specified groups
- Implemented truncation of long item lists in Telegram messages
- Removed time display from Telegram messages
- Removed "Tax Amount" field from the OpenAI prompt and data processing
- Enhanced Google Sheets configuration in pyHandler.js:
  - Added option to enable/disable specific columns
  - Added option to hide specific columns
  - Added explicit column order definition
  - Added logging configuration (enableLogging)
- Simplified API security by removing API key requirement
- Implemented UUID-based record tracking system to solve row shifting issues
  - Each receipt now has a unique identifier that doesn't change when rows shift
  - Notes are now linked to receipts by UUID instead of row number
  - Added tracking of spreadsheet and sheet IDs for better cross-group support
- Added option to insert new records at the top of the spreadsheet (insertAtTop configuration)
- Added date and time formatting options (use12HourFormat configuration)
- Added receipt notes functionality allowing users to add context to receipts by replying to bot messages
- Implemented message tracking system for associating notes with receipts
- Added "Notes" column to the spreadsheet
- Added automatic cleanup of old message tracking records (after 14 days)
- Added "Amount in USD" column for manual entry
- Renamed columns for better clarity:
  - "Telegram User ID" → "User ID"
  - "Telegram Username" → "User Name"
  - "Total Amount" → "Amount"
  - "Image URL" → "Recipt"
- Reordered columns to a specific sequence
- Improved column handling to work by header name instead of column index


## Architecture

### Components
1. **Telegram Bot Interface**: Handles user interactions via the Telegram API
2. **File Processing Pipeline**: Converts, uploads and processes various file formats
3. **OpenAI Integration**: Extracts structured data from receipt images using GPT-4o models
4. **Google Drive Integration**: Stores files in user-specific folders
5. **Google Sheets Integration**: Records extracted receipt data for analysis
6. **User Authentication System**: Controls access via configurable user groups
7. **UUID Tracking System**: Ensures data integrity when rows shift in spreadsheets

### Key Modules
- `account_router.py`: Manages user permissions and routes to appropriate Google resources
- `google_script.py`: Handles communication with Google Apps Script
- `openai_client.py`: Processes images using OpenAI's vision capabilities with retry mechanism
- `pdf_to_image.py`: Converts PDF documents to images for processing
- `img_converter.py`: Converts various image formats to ones compatible with OpenAI
- `telegram_handler.py`: Handles Telegram bot interactions and commands
- `google_sheets.py`: Manages the creation of records in Google Sheets
- `file_processor.py`: Coordinates the file processing workflow
- `message_tracker.py`: Tracks message IDs and their associated receipt records with UUIDs
- `receipt_notes.py`: Handles receipt notes functionality and message registration

### Google Apps Script Component
- `pyHandler.gs`: Google Apps Script web app that handles Drive/Sheets operations
  - Generates UUIDs for each record
  - Provides methods to find records by UUID instead of row number
  - Manages hidden RecordId column for UUID storage
  - Configurable column visibility and order
  - Supports 12-hour or 24-hour time format
  - Optional logging to a dedicated Logs sheet

## Setup Instructions

### Prerequisites
- Python 3.8+
- A Telegram Bot Token (create one via BotFather)
- An OpenAI API key
- A Google account with access to Google Drive and Google Sheets

### Installation

1. Clone the repository
```bash
git clone https://github.com/kidem42/Tg_bot_receipt_recognition.git
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
4. Configure the Google Apps Script settings in the GENERAL_CONFIG object:
   - `insertAtTop`: Set to `true` to insert new records at the top of the spreadsheet, or `false` to append at the bottom
   - `use12HourFormat`: Set to `true` for AM/PM time format, or `false` for 24-hour format
   - `enableLogging`: Set to `true` to enable logging to a Logs sheet, or `false` to disable

5. Configure column settings in the COLUMN_CONFIG object:
   - Enable or disable specific columns by setting their values to `true` or `false`
   - Hide columns by adding their names to the HIDDEN_COLUMNS array
   - Set column order by arranging names in the COLUMN_ORDER array

6. Configure group-specific template messages in `config.py`:
   ```python
   # Message templates for specific user groups
   GROUP_MESSAGE_TEMPLATES = {
       # Group 0 template with Markdown formatting
       0: """
   *IMPORTANT!*
   Reply to this message to add Notes. 
   Use "*REP*" for company spent reporting, and "*MY*" for reimbursement
   [Folder]({folder_url})
   """,
       # Group 1 template - set to None for no template
       #1: None,
       # Add more group templates as needed
   }
   ```
7. Deploy the script as a web app:
   - Click Deploy → New Deployment
   - Select "Web app" as the type
   - Set "Execute as" to "Me"
   - Set "Who has access" to "Anyone"
   - Click "Deploy"
8. Copy the provided web app URL and paste it as `GOOGLE_SCRIPT_URL_0` in your `.env` file

### Google Drive Setup

1. Create a folder in Google Drive where you want to store receipt files
2. Right-click the folder and select "Get link"
3. From the sharing link, extract the folder ID (the part after `/folders/` in the URL)
4. Add this folder ID as `MAIN_FOLDER_ID_0` in your `.env` file

## Usage

- Send a photo of a receipt directly to the bot
- Send a document (PDF or image) containing receipt information
- The bot will process the image, extract receipt data, and respond with the extracted information
- To add notes to a receipt, simply reply to the bot's message containing the receipt details
- The bot will confirm that your note has been added with a "✅ Note added successfully to the receipt!" message
- All files are stored in your Google Drive, and receipt data is recorded in Google Sheets
- Notes can be added up to 14 days after uploading a receipt

## Technical Details

### Group-specific Template Messages

The system supports customized template messages for different user groups:

1. **Configuration**:
   - Templates are defined in `config.py` using the `GROUP_MESSAGE_TEMPLATES` dictionary
   - Each user group can have a unique template or no template (set to `None`)
   - Templates support Markdown formatting for text styling (e.g., *bold text*)
   - Templates can include the Google Drive folder URL using the `{folder_url}` placeholder

2. **Implementation**:
   - When a receipt is processed, the system checks the user's group
   - If a template exists for that group, it's appended to the success message
   - Messages with templates are sent with Markdown parsing enabled

3. **Use Cases**:
   - Providing group-specific instructions for receipt handling
   - Highlighting important information with bold formatting
   - Customizing workflow guidance for different departments or teams
   - Providing direct links to user-specific Google Drive folders

### UUID-based Record Tracking

The system uses universally unique identifiers (UUIDs) to track receipt records:

1. **Record Creation**:
   - When a new receipt is processed, a UUID is generated and stored in a hidden "RecordId" column
   - The UUID, along with spreadsheet and sheet IDs, is returned to the bot
   - This information is stored in the receipt_messages.json tracking file

2. **Note Addition**:
   - When a user replies to add a note, the system retrieves the UUID from tracking data
   - The note is added to the correct record by searching for its UUID
   - This ensures notes are added to the right receipt even if rows have shifted

3. **Benefits**:
   - Solves the problem of row shifting when new records are added at the top
   - Ensures data integrity across multiple user groups
   - Provides backward compatibility with existing records

## Security

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
This project is licensed under the Apache License, Version 2.0 - see the LICENSE file for details.

What this means for you:

- You can freely use, modify, and distribute this software
- You can use the software for commercial purposes
- You must include the original copyright notice and license
- You must state significant changes made to the software
- The full license text is available at http://www.apache.org/licenses/LICENSE-2.0
