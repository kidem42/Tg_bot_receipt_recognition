import time
import random
import requests
from openai import OpenAI
from config import OPENAI_API_KEY, MODELS, OPENAI_REQUEST_TIMEOUT, OPENAI_MAX_RETRIES, OPENAI_RETRY_DELAY
from config import RECEIPT_SYSTEM_PROMPT, RECEIPT_USER_PROMPT

# Create OpenAI client with timeout settings
client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=OPENAI_REQUEST_TIMEOUT
)

def call_with_retry(func, *args, **kwargs):
    """
    Helper function to call OpenAI API with retry mechanism and exponential backoff.
    
    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        Exception: If all retry attempts fail
    """
    retries = 0
    max_retries = OPENAI_MAX_RETRIES
    delay = OPENAI_RETRY_DELAY
    
    while True:
        try:
            return func(*args, **kwargs)
        except (TimeoutError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
            retries += 1
            if retries > max_retries:
                print(f"Maximum retry attempts ({max_retries}) reached. Giving up.")
                raise
            
            # Add jitter to avoid thundering herd problem
            jitter = random.uniform(0, 0.1 * delay)
            wait_time = delay * (2 ** (retries - 1)) + jitter
            
            print(f"Timeout error: {str(e)}. Retrying in {wait_time:.2f} seconds (attempt {retries}/{max_retries})...")
            time.sleep(wait_time)
        except Exception as e:
            # For non-timeout errors, we don't retry
            print(f"Error during API call: {str(e)}")
            raise

def analyze_images_batch(image_contents_list):
    """
    Analyzes multiple images (pages) as a single receipt by sending them
    in one request to OpenAI Vision.
    
    Args:
        image_contents_list (list): List of image contents in bytes
        
    Returns:
        dict: Structured receipt data
    """
    import base64
    import json
    
    # Check input data
    if not image_contents_list or len(image_contents_list) == 0:
        print("Error: No images provided for analysis")
        return None
    
    # Create request content with multiple images
    content = [{"type": "text", "text": RECEIPT_USER_PROMPT + " This is a multi-page receipt (like an airline ticket)."}]
    
    # Add each image to the request
    for image_content in image_contents_list:
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_base64}"
            }
        })
    
    try:
        # Use the retry mechanism for the API call
        response = call_with_retry(
            client.chat.completions.create,
            model=MODELS['vision'],
            temperature=0.3,
            messages=[
                {"role": "system", "content": RECEIPT_SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ]
        )
        
        receipt_data = response.choices[0].message.content
        
        # Clean the response from markdown formatting
        cleaned_data = receipt_data
        
        # Check if the response starts with a markdown code marker
        if cleaned_data.startswith("```"):
            # Find the first and last line with markers
            lines = cleaned_data.split("\n")
            start_idx = 0
            end_idx = len(lines) - 1
            
            # Look for the starting marker
            for i, line in enumerate(lines):
                if line.startswith("```"):
                    start_idx = i
                    break
            
            # Look for the ending marker
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith("```") and i != start_idx:
                    end_idx = i
                    break
            
            # Extract only the JSON content (without markers)
            cleaned_data = "\n".join(lines[start_idx + 1:end_idx])
        
        # Try to parse JSON
        try:
            receipt_json = json.loads(cleaned_data)
            return receipt_json
        except json.JSONDecodeError as e:
            print("Error parsing JSON from OpenAI response")
            print(f"Parsing error: {str(e)}")
            print(f"Received response from OpenAI: {receipt_data}")
            print(f"Cleaned response: {cleaned_data}")
            return None
            
    except (TimeoutError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
        print(f"Timeout error in analyze_images_batch after all retries: {str(e)}")
        return None
    except Exception as e:
        print(f"Error analyzing receipt batch: {str(e)}")
        return None


def analyze_image(image_content):
    """
    Analyzes a receipt image using OpenAI Vision and extracts structured data.
    
    Args:
        image_content (bytes): Receipt image content
        
    Returns:
        dict: Structured receipt data
    """
    import base64
    import json
    
    # Encode image in base64
    image_base64 = base64.b64encode(image_content).decode('utf-8')
    
    try:
        # Use the retry mechanism for the API call
        response = call_with_retry(
            client.chat.completions.create,
            model=MODELS['vision'],
            temperature=0.3,
            messages=[
                {"role": "system", "content": RECEIPT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": RECEIPT_USER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        )
        
        receipt_data = response.choices[0].message.content
        
        # Clean the response from markdown formatting
        cleaned_data = receipt_data
        
        # Check if the response starts with a markdown code marker
        if cleaned_data.startswith("```"):
            # Find the first and last line with markers
            lines = cleaned_data.split("\n")
            start_idx = 0
            end_idx = len(lines) - 1
            
            # Look for the starting marker
            for i, line in enumerate(lines):
                if line.startswith("```"):
                    start_idx = i
                    break
            
            # Look for the ending marker
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith("```") and i != start_idx:
                    end_idx = i
                    break
            
            # Extract only the JSON content (without markers)
            cleaned_data = "\n".join(lines[start_idx + 1:end_idx])
        
        # Try to parse JSON
        try:
            receipt_json = json.loads(cleaned_data)
            return receipt_json
        except json.JSONDecodeError as e:
            print("Error parsing JSON from OpenAI response")
            print(f"Parsing error: {str(e)}")
            print(f"Received response from OpenAI: {receipt_data}")
            print(f"Cleaned response: {cleaned_data}")
            return None
            
    except (TimeoutError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
        print(f"Timeout error in analyze_image after all retries: {str(e)}")
        return None
    except Exception as e:
        print(f"Error analyzing receipt: {str(e)}")
        return None
