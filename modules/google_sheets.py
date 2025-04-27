import requests
import json
import logging
from modules.account_router import get_script_url, get_user_group

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('google_sheets')

def create_expense_record(user_id, username, receipt_data, file_url):
    """
    Creates an expense record in Google Sheets.
    
    Args:
        user_id (int): Telegram user ID
        username (str): Telegram username
        receipt_data (dict): Receipt data obtained after OpenAI analysis
        file_url (str): Link to the original image in Google Drive
        
    Returns:
        dict or bool: Dictionary with row_id, record_id, group_id, spreadsheet_id, sheet_id if successful, False otherwise
    """
    # Get script URL and group ID for this user
    script_url = get_script_url(user_id)
    group_id = get_user_group(user_id)
    
    if not script_url:
        print(f"Failed to get script URL for user {user_id}")
        return False
    
    # Prepare data for recording
    row_data = {
        "telegram_user_id": user_id,
        "telegram_username": username,
        "total_amount": receipt_data.get("total_amount"),
        "currency": receipt_data.get("currency"),
        "date": receipt_data.get("date"),
        "time": receipt_data.get("time"),
        "items": receipt_data.get("items"),
        "image_url": file_url
    }
    
    payload = {
        "action": "createExpenseRecord",
        "data": row_data
    }
    
    try:
        # Log request details
        logger.info(f"Making request to: {script_url}")
        logger.info(f"Payload: {payload}")
        
        # Make the request without security headers
        response = requests.post(
            script_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        # Log response details
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'error' in result:
                    logger.error(f"API returned error: {result['error']}")
                    return False
                
                if result.get('success'):
                    logger.info(f"Expense record created for user {user_id}_{username}")
                    
                    # Return dictionary with row_id, record_id, group_id, spreadsheet_id, sheet_id
                    return {
                        "row_id": result.get('rowId'),
                        "record_id": result.get('recordId'),
                        "group_id": group_id,
                        "spreadsheet_id": result.get('spreadsheetId'),
                        "sheet_id": result.get('sheetId')
                    }
                else:
                    logger.error(f"Error creating record: {result.get('error')}")
                    return False
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response.text}")
                return False
        else:
            logger.error(f"HTTP error when creating record: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception when creating expense record: {str(e)}")
        return False

# update_receipt_note function removed - using only update_receipt_note_by_record_id now

def update_receipt_note_by_record_id(record_id, note_text, user_id, spreadsheet_id=None, sheet_id=None):
    """
    Updates a note for an existing receipt record in Google Sheets using record ID.
    
    Args:
        record_id (str): Unique record ID
        note_text (str): Note text to add
        user_id (int): User ID to determine the script URL
        spreadsheet_id (str, optional): ID of the spreadsheet
        sheet_id (str, optional): ID of the sheet
        
    Returns:
        bool: True if the update was successful, False otherwise
    """
    # Get script URL for this user
    script_url = get_script_url(user_id)
    
    if not script_url:
        logger.error(f"Failed to get script URL for user {user_id}")
        return False
    
    payload = {
        "action": "updateReceiptNoteByRecordId",
        "recordId": record_id,
        "note": note_text
    }
    
    # Add spreadsheet_id and sheet_id if provided
    if spreadsheet_id:
        payload["spreadsheetId"] = spreadsheet_id
    
    if sheet_id:
        payload["sheetId"] = sheet_id
    
    try:
        # Log request details
        logger.info(f"Making request to: {script_url}")
        logger.info(f"Payload: {payload}")
        
        # Make the request without security headers
        response = requests.post(
            script_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        # Log response details
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'error' in result:
                    logger.error(f"API returned error: {result['error']}")
                    return False
                
                if result.get('success'):
                    logger.info(f"Note added to receipt for user {user_id} using record_id")
                    return True
                else:
                    logger.error(f"Error adding note: {result.get('error')}")
                    return False
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return False
        else:
            logger.error(f"HTTP error when adding note: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception when adding note: {str(e)}")
        return False
