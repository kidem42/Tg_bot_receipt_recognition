import os
import datetime
from modules.google_script import get_user_folder_id, upload_file_to_drive

import os
import datetime

def get_formatted_filename(user_id, original_filename):
    """
    Forms a filename according to the template: user_id_hour_minute_month_day_year.extension
    
    Args:
        user_id (int): Telegram user ID
        original_filename (str): Original filename
        
    Returns:
        str: Formatted filename
    """
    now = datetime.datetime.now()
    
    # Get file extension
    _, file_extension = os.path.splitext(original_filename)
    
    # Format filename
    formatted_name = f"{user_id}_{now.hour}_{now.minute}_{now.month}_{now.day}_{now.year}{file_extension}"
    
    return formatted_name

def process_and_upload_file(file_content, original_filename, user_id, username, mime_type):
    """
    Processes and uploads a file to Google Drive.
    
    Args:
        file_content (bytes): File content
        original_filename (str): Original filename
        user_id (int): Telegram user ID
        username (str): Username
        mime_type (str): File MIME type
        
    Returns:
        bool: True if upload is successful, False otherwise
    """
    # Get or create user folder
    folder_id = get_user_folder_id(user_id, username)
    
    if not folder_id:
        print(f"Failed to get folder ID for user {user_id}_{username}")
        return False
    
    # Form a new filename
    new_filename = get_formatted_filename(user_id, original_filename)
    
    # Upload the file
    return upload_file_to_drive(file_content, new_filename, folder_id, mime_type)
