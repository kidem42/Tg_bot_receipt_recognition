#!/usr/bin/env python3
"""
Test script for Google Drive API integration.
This script tests the connection to the Google Apps Script API.
"""
import sys
import logging
from modules.google_script import test_api_connection, get_user_folder_id
from modules.account_router import get_script_url, get_main_folder_id

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_google_api')

def main():
    """Main function to test Google Drive API integration."""
    if len(sys.argv) < 2:
        print("Usage: python test_google_api.py <user_id> [<username>]")
        print("Example: python test_google_api.py 146430279 Kidem42")
        return 1
    
    user_id = int(sys.argv[1])
    username = sys.argv[2] if len(sys.argv) > 2 else "TestUser"
    
    # Test script URL and folder ID
    script_url = get_script_url(user_id)
    folder_id = get_main_folder_id(user_id)
    
    logger.info(f"Testing with user_id: {user_id}, username: {username}")
    logger.info(f"Script URL: {script_url}")
    logger.info(f"Main folder ID: {folder_id}")
    
    if not script_url or not folder_id:
        logger.error("Failed to get script URL or main folder ID")
        return 1
    
    # Test API connection
    logger.info("Testing API connection...")
    connection_result = test_api_connection(user_id)
    
    if connection_result:
        logger.info("API connection test successful!")
    else:
        logger.error("API connection test failed!")
        return 1
    
    # Test folder creation/retrieval
    logger.info("Testing folder creation/retrieval...")
    folder_id = get_user_folder_id(user_id, username)
    
    if folder_id:
        logger.info(f"Folder test successful! Folder ID: {folder_id}")
    else:
        logger.error("Folder test failed!")
        return 1
    
    logger.info("All tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
