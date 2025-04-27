"""
Module for routing users between different Google Script URLs and folders.
"""
import config
import logging

# Configure logging
logger = logging.getLogger('account_router')

def get_user_group(user_id):
    """
    Determines which group the user belongs to.
    
    Args:
        user_id (int): Telegram user ID
        
    Returns:
        int: User group number (0, 1, 2, ...) or None if user is not found
    """
    # Check if user_id is in ALLOWED_USERS_0
    if user_id in config.ALLOWED_USERS_0:
        logger.debug(f"User {user_id} belongs to group 0")
        return 0
    elif hasattr(config, 'ALLOWED_USERS_1') and user_id in config.ALLOWED_USERS_1:
        logger.debug(f"User {user_id} belongs to group 1")
        return 1
    elif hasattr(config, 'ALLOWED_USERS_2') and user_id in config.ALLOWED_USERS_2:
        logger.debug(f"User {user_id} belongs to group 2")
        return 2
    # More groups can be added if needed
    
    logger.debug(f"User {user_id} does not belong to any group")
    return None

def is_user_allowed(user_id):
    """
    Checks if the user is in any of the allowed groups.
    
    Args:
        user_id (int): Telegram user ID
        
    Returns:
        bool: True if the user is allowed, False otherwise
    """
    result = get_user_group(user_id) is not None
    logger.debug(f"Access check for user {user_id}: {result}")
    return result

def get_script_url(user_id):
    """
    Returns the Google Script URL for the specified user.
    
    Args:
        user_id (int): Telegram user ID
        
    Returns:
        str: Google Script URL or None if the user is not found or URL is not configured
    """
    group = get_user_group(user_id)
    
    if group is None:
        logger.debug(f"User {user_id} does not belong to any group")
        return None
    
    # Get the corresponding URL from the configuration
    url_var_name = f'GOOGLE_SCRIPT_URL_{group}'
    if hasattr(config, url_var_name):
        return getattr(config, url_var_name)
    
    # If URL is not found, return None
    logger.debug(f"URL for group {group} is not configured")
    return None

def get_main_folder_id(user_id):
    """
    Returns the Google Drive root folder ID for the specified user.
    
    Args:
        user_id (int): Telegram user ID
        
    Returns:
        str: Root folder ID or None if the user is not found or ID is not configured
    """
    group = get_user_group(user_id)
    
    if group is None:
        logger.debug(f"User {user_id} does not belong to any group")
        return None
    
    # Get the corresponding folder ID from the configuration
    folder_var_name = f'MAIN_FOLDER_ID_{group}'
    if hasattr(config, folder_var_name):
        return getattr(config, folder_var_name)
    
    # If folder ID is not found, return None
    logger.debug(f"Folder ID for group {group} is not configured")
    return None
