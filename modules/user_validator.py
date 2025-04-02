from modules.account_router import is_user_allowed as router_is_user_allowed

def is_user_allowed(user_id):
    """
    Checks if the user is in the list of allowed users.
    
    Args:
        user_id (int): Telegram user ID
        
    Returns:
        bool: True if the user is allowed, False otherwise
    """
    return router_is_user_allowed(user_id)
