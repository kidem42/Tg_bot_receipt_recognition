import requests
import json
import time
import hashlib
import logging
from modules.account_router import get_script_url, get_main_folder_id
from config import GOOGLE_SCRIPT_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('google_script')

def create_user_folder(user_id, username):
    """
    Creates a user folder on Google Drive through Google Apps Script.
    
    Args:
        user_id (int): Telegram user ID
        username (str): Username
        
    Returns:
        str: ID of the created folder or None in case of error
    """
    folder_name = f"{user_id}_{username}"
    
    # Get URL and root folder ID for this user
    script_url = get_script_url(user_id)
    parent_folder_id = get_main_folder_id(user_id)
    
    if not script_url or not parent_folder_id:
        print(f"Failed to get script URL or root folder ID for user {user_id}")
        return None
    
    payload = {
        "action": "createFolder",
        "parentFolderId": parent_folder_id,
        "folderName": folder_name
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
                    return None
                
                logger.info(f"Folder created: {folder_name}, ID: {result.get('folderId')}")
                return result.get('folderId')
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response.text}")
                return None
        else:
            logger.error(f"Error creating folder: {response.status_code}, {response.text}")
            try:
                error_json = response.json()
                if 'error' in error_json:
                    logger.error(f"Error details: {error_json['error']}")
            except:
                pass
            return None
    except Exception as e:
        logger.error(f"Exception when creating folder: {str(e)}")
        return None

def upload_file_to_drive(file_content, file_name, folder_id, mime_type, user_id=None):
    """
    Uploads a file to Google Drive through Google Apps Script.
    
    Args:
        file_content (bytes): File content in binary format
        file_name (str): File name
        folder_id (str): ID of the folder to upload the file to
        mime_type (str): File MIME type
        user_id (int, optional): Telegram user ID to determine the script URL
        
    Returns:
        str: ID of the uploaded file or None in case of error
    """
    # Encode file in base64 for transmission
    import base64
    encoded_content = base64.b64encode(file_content).decode('utf-8')
    
    # Get script URL for this user
    script_url = get_script_url(user_id) if user_id else None
    
    # If we couldn't get the URL for the user, display an error and return None
    if not script_url:
        print(f"Failed to get script URL for user {user_id}")
        return None
    
    payload = {
        "action": "uploadFile",
        "folderId": folder_id,
        "fileName": file_name,
        "fileContent": encoded_content,
        "mimeType": mime_type
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
        logger.info(f"Payload action: {payload['action']}, fileName: {payload['fileName']}")
        
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
                    return None
                
                logger.info(f"File uploaded: {file_name}, ID: {result.get('fileId')}")
                return result.get('fileId')  # Return the file ID
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response.text}")
                return None
        else:
            logger.error(f"Error uploading file: {response.status_code}, {response.text}")
            try:
                error_json = response.json()
                if 'error' in error_json:
                    logger.error(f"Error details: {error_json['error']}")
            except:
                pass
            return None
    except Exception as e:
        logger.error(f"Exception when uploading file: {str(e)}")
        return None

def get_user_folder_id(user_id, username):
    """
    Gets the user folder ID or creates it if it doesn't exist.
    
    Args:
        user_id (int): Telegram user ID
        username (str): Username
        
    Returns:
        str: User folder ID
    """
    folder_name = f"{user_id}_{username}"
    
    # Get URL and root folder ID for this user
    script_url = get_script_url(user_id)
    parent_folder_id = get_main_folder_id(user_id)
    
    if not script_url or not parent_folder_id:
        print(f"Failed to get script URL or root folder ID for user {user_id}")
        return None
    
    payload = {
        "action": "getFolderByName",
        "parentFolderId": parent_folder_id,
        "folderName": folder_name
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
                    return create_user_folder(user_id, username)
                
                if result.get('found'):
                    logger.info(f"User folder found: {folder_name}, ID: {result.get('folderId')}")
                    return result.get('folderId')
                else:
                    logger.info(f"User folder not found, creating a new one: {folder_name}")
                    return create_user_folder(user_id, username)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response.text}")
                return create_user_folder(user_id, username)
        else:
            logger.error(f"Error searching for folder: {response.status_code}, {response.text}")
            try:
                error_json = response.json()
                if 'error' in error_json:
                    logger.error(f"Error details: {error_json['error']}")
            except:
                pass
            return create_user_folder(user_id, username)
    except Exception as e:
        logger.error(f"Exception when searching for folder: {str(e)}")
        return create_user_folder(user_id, username)

def test_api_connection(user_id):
    """
    Tests the connection to the Google Apps Script API.
    
    Args:
        user_id (int): Telegram user ID
        
    Returns:
        bool: True if connection is successful, False otherwise
    """
    # Get script URL for this user
    script_url = get_script_url(user_id)
    
    if not script_url:
        logger.error(f"Failed to get script URL for user {user_id}")
        return False
    
    # Simple test payload
    payload = {
        "action": "test"
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
        logger.info(f"Testing API connection to: {script_url}")
        logger.info(f"Headers: X-API-Key: {headers['X-API-Key'][:5]}..., X-Timestamp: {headers['X-Timestamp']}, X-Signature: {headers['X-Signature'][:10]}...")
        
        # Add headers to URL as query parameters
        url_with_params = f"{script_url}?X-API-Key={headers['X-API-Key']}&X-Timestamp={headers['X-Timestamp']}&X-Signature={headers['X-Signature']}"
        logger.info(f"URL with params: {url_with_params[:50]}...")
        
        response = requests.post(
            url_with_params,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        # Log response details
        logger.info(f"Test response status code: {response.status_code}")
        logger.info(f"Test response content: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'error' in result:
                    logger.error(f"API test returned error: {result['error']}")
                    return False
                
                logger.info(f"API connection test successful")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response in test: {e}")
                logger.error(f"Raw response: {response.text}")
                return False
        else:
            logger.error(f"Error testing API connection: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception when testing API connection: {str(e)}")
        return False
