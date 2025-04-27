import requests
import json
import logging
from modules.account_router import get_script_url, get_main_folder_id

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
    
    try:
        payload = {
            "action": "createFolder",
            "parentFolderId": parent_folder_id,
            "folderName": folder_name
        }
        
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
    
    try:
        payload = {
            "action": "uploadFile",
            "folderId": folder_id,
            "fileName": file_name,
            "fileContent": encoded_content,
            "mimeType": mime_type
        }
        
        # Log request details
        logger.info(f"Making request to: {script_url}")
        logger.info(f"Payload action: {payload['action']}, fileName: {payload['fileName']}")
        
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
    
    try:
        payload = {
            "action": "getFolderByName",
            "parentFolderId": parent_folder_id,
            "folderName": folder_name
        }
        
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

# test_api_connection function removed - no longer needed after API security removal
