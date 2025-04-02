import io
from PIL import Image
import pillow_heif
import tempfile
import os

def convert_image_to_compatible_format(image_content, source_filename):
    """
    Converts an image to a format compatible with the OpenAI API.
    
    Supported OpenAI formats:
    - PNG (.png)
    - JPEG (.jpeg, .jpg)
    - WEBP (.webp)
    - Non-animated GIF (.gif)
    
    Args:
        image_content (bytes): Image file content
        source_filename (str): Original filename to determine the extension
        
    Returns:
        tuple: (bytes, mime_type) - converted image content and its MIME type
              or None if conversion failed
    """
    # Get file extension in lowercase
    _, ext = os.path.splitext(source_filename)
    ext = ext.lower()
    
    # Check if conversion is needed
    compatible_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
    
    if ext in compatible_extensions:
        # Check that GIF is not animated
        if ext == '.gif':
            try:
                with Image.open(io.BytesIO(image_content)) as img:
                    # If n_frames > 1, then GIF is animated
                    if getattr(img, "n_frames", 1) > 1:
                        # Convert animated GIF to PNG (take the first frame)
                        img.seek(0)  # go to the first frame
                        output_buffer = io.BytesIO()
                        img.convert("RGBA").save(output_buffer, format="PNG")
                        return output_buffer.getvalue(), "image/png"
                    else:
                        # Non-animated GIF - no conversion required
                        return image_content, "image/gif"
            except Exception as e:
                print(f"Error checking GIF: {str(e)}")
                return None, None
        else:
            # Format is compatible, no conversion required
            mime_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp'
            }
            return image_content, mime_map.get(ext)
    
    # Conversion is necessary
    try:
        # Special handling for HEIC/HEIF
        if ext in ['.heic', '.heif']:
            # Register HEIF in Pillow
            pillow_heif.register_heif_opener()
            
            # Create a temporary file for HEIC
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
                temp_file.write(image_content)
                temp_path = temp_file.name
            
            try:
                # Open and convert HEIC to JPEG
                with Image.open(temp_path) as img:
                    output_buffer = io.BytesIO()
                    img.convert("RGB").save(output_buffer, format="JPEG", quality=95)
                    return output_buffer.getvalue(), "image/jpeg"
            finally:
                # Delete temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            # Processing other image formats
            try:
                with Image.open(io.BytesIO(image_content)) as img:
                    output_buffer = io.BytesIO()
                    
                    # Save as JPEG or PNG depending on the presence of alpha channel
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        img.save(output_buffer, format="PNG")
                        return output_buffer.getvalue(), "image/png"
                    else:
                        img.convert("RGB").save(output_buffer, format="JPEG", quality=95)
                        return output_buffer.getvalue(), "image/jpeg"
            except Exception as e:
                print(f"Error converting image: {str(e)}")
                return None, None
    except Exception as e:
        print(f"Error converting image: {str(e)}")
        return None, None
def clear_temp_files():
    """
    Cleans up temporary files created during image conversion.
    """
    temp_dir = tempfile.gettempdir()
    try:
        for file in os.listdir(temp_dir):
            if file.startswith('tmp') and (file.endswith('.heic') or file.endswith('.heif')):
                try:
                    os.remove(os.path.join(temp_dir, file))
                    print(f"Temporary file deleted: {file}")
                except Exception as e:
                    print(f"Failed to delete temporary file {file}: {str(e)}")
    except Exception as e:
        print(f"Error cleaning temporary files: {str(e)}")
