import json
import os
import time
from config import MESSAGES_TRACKING_FILE, MAX_RECORD_AGE, CLEANUP_INTERVAL

def load_tracking_data():
    """Load message tracking data from file"""
    if not os.path.exists(MESSAGES_TRACKING_FILE):
        return {"receipt_messages": {}, "last_cleanup": time.time()}
    
    try:
        with open(MESSAGES_TRACKING_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading tracking data: {str(e)}")
        return {"receipt_messages": {}, "last_cleanup": time.time()}

def save_tracking_data(data):
    """Save message tracking data to file"""
    try:
        with open(MESSAGES_TRACKING_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving tracking data: {str(e)}")
        return False

def add_message_tracking(user_id, message_id, sheet_row_id, message_text, record_id=None, group_id=None, spreadsheet_id=None, sheet_id=None):
    """
    Add a new message tracking record
    
    Args:
        user_id (int): Telegram user ID
        message_id (int): Message ID
        sheet_row_id (int): Row ID in Google Sheets
        message_text (str): Message text
        record_id (str, optional): Unique record ID (UUID)
        group_id (int, optional): User group ID
        spreadsheet_id (str, optional): Google Spreadsheet ID
        sheet_id (str, optional): Google Sheet ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    data = load_tracking_data()
    
    # Create key from user_id and message_id
    key = f"{user_id}_{message_id}"
    
    # Add record
    data["receipt_messages"][key] = {
        "sheet_row_id": sheet_row_id,
        "timestamp": time.time(),
        "message_text": message_text,
        "record_id": record_id,
        "group_id": group_id,
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": sheet_id
    }
    
    # Check if cleanup is needed
    if time.time() - data.get("last_cleanup", 0) > CLEANUP_INTERVAL:
        cleanup_old_records(data)
    
    return save_tracking_data(data)

def get_receipt_by_message(user_id, message_id):
    """Get receipt info by message ID"""
    data = load_tracking_data()
    key = f"{user_id}_{message_id}"
    
    receipt_info = data["receipt_messages"].get(key)
    if receipt_info and time.time() - receipt_info["timestamp"] <= MAX_RECORD_AGE:
        return receipt_info
    
    return None

def cleanup_old_records(data=None):
    """Clean up old records"""
    if data is None:
        data = load_tracking_data()
    
    current_time = time.time()
    keys_to_remove = []
    
    for key, info in data["receipt_messages"].items():
        if current_time - info["timestamp"] > MAX_RECORD_AGE:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del data["receipt_messages"][key]
    
    data["last_cleanup"] = current_time
    save_tracking_data(data)
    
    print(f"Cleaned up {len(keys_to_remove)} old receipt records")

def extract_user_id_from_row_id(row_id):
    """Extract user_id from tracking data based on row_id"""
    data = load_tracking_data()
    
    for key, info in data["receipt_messages"].items():
        if info.get("sheet_row_id") == row_id:
            # Extract user_id from the key (format: "user_id_message_id")
            return int(key.split('_')[0])
    
    return None

def get_record_id_by_row_id(row_id):
    """
    Get record_id from tracking data based on row_id
    
    Args:
        row_id (int): Row ID in Google Sheets
        
    Returns:
        str or None: Record ID (UUID) if found, None otherwise
    """
    data = load_tracking_data()
    
    for key, info in data["receipt_messages"].items():
        if info.get("sheet_row_id") == row_id:
            return info.get("record_id")
    
    return None

def get_receipt_info_by_row_id(row_id):
    """
    Get complete receipt info from tracking data based on row_id
    
    Args:
        row_id (int): Row ID in Google Sheets
        
    Returns:
        dict or None: Receipt info if found, None otherwise
    """
    data = load_tracking_data()
    
    for key, info in data["receipt_messages"].items():
        if info.get("sheet_row_id") == row_id:
            return info
    
    return None
