import secrets
import string

def generate_api_key(length=32):
    """
    Generates a cryptographically secure API key of the specified length.
    
    Args:
        length (int): Length of the generated key. Default is 32 characters.
        
    Returns:
        str: Generated API key
    """
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key

# Usage example:
if __name__ == "__main__":
    api_key = generate_api_key()
    print(f"Your API key: {api_key}")
    
    # For a longer key:
    long_api_key = generate_api_key(64)
    print(f"Long API key: {long_api_key}")