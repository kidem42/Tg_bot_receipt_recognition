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

def add_message_tracking(user_id, message_id, sheet_row_id, message_text):
    """Add a new message tracking record"""
    data = load_tracking_data()
    
    # Create key from user_id and message_id
    key = f"{user_id}_{message_id}"
    
    # Add record
    data["receipt_messages"][key] = {
        "sheet_row_id": sheet_row_id,
        "timestamp": time.time(),
        "message_text": message_text
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
