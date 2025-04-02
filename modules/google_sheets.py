import requests
import json
import time
import hashlib
import logging
from modules.account_router import get_script_url
from config import GOOGLE_SCRIPT_API_KEY

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
        bool: True if the record was created successfully, False otherwise
    """
    # Get script URL for this user
    script_url = get_script_url(user_id)
    
    if not script_url:
        print(f"Failed to get script URL for user {user_id}")
        return False
    # Prepare data for recording
    row_data = {
        "telegram_user_id": user_id,
        "telegram_username": username,
        "total_amount": receipt_data.get("total_amount"),
        "tax_amount": receipt_data.get("tax_amount"),
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
        # Generate timestamp and signature for security
        timestamp = int(time.time())
        signature = hashlib.sha256(f"{GOOGLE_SCRIPT_API_KEY}{timestamp}".encode()).hexdigest()
        
        # Add security headers
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": GOOGLE_SCRIPT_API_KEY,
            "X-Timestamp": str(timestamp),
            "X-Signature": signature
        }
        
        # Log request details
        logger.info(f"Making request to: {script_url}")
        logger.info(f"Headers: X-API-Key: {headers['X-API-Key'][:5]}..., X-Timestamp: {headers['X-Timestamp']}, X-Signature: {headers['X-Signature'][:10]}...")
        logger.info(f"Payload: {payload}")
        
        # Add headers to URL as query parameters
        url_with_params = f"{script_url}?X-API-Key={headers['X-API-Key']}&X-Timestamp={headers['X-Timestamp']}&X-Signature={headers['X-Signature']}"
        logger.info(f"URL with params: {url_with_params[:50]}...")
        
        response = requests.post(
            url_with_params,
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
                    return True
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
