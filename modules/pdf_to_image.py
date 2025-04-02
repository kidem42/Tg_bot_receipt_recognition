import tempfile
import os
import glob
import shutil
from pdf2image import convert_from_bytes, convert_from_path

# Prefix for temporary files so they can be easily identified
PDF_TEMP_PREFIX = "pdf2img_temp_"

def pdf_to_image(pdf_content=None, pdf_path=None, dpi=200, output_format='JPEG', 
                 first_page=None, last_page=None, single_page=None):
    """
    Converts PDF to a list of images.
    
    Args:
        pdf_content (bytes, optional): PDF file content as bytes
        pdf_path (str, optional): Path to PDF file
        dpi (int, optional): Image resolution. Default is 200.
        output_format (str, optional): Output image format ('JPEG', 'PNG'). Default is 'JPEG'.
        first_page (int, optional): First page number to convert (starting from 1)
        last_page (int, optional): Last page number to convert
        single_page (int, optional): Specific page number to convert (starting from 1)
        
    Returns:
        list: List of PIL.Image objects
    """
    if pdf_content is None and pdf_path is None:
        raise ValueError("You must provide either PDF content or a path to the file")
    
    # Create a temporary directory for files
    temp_dir = tempfile.mkdtemp(prefix=PDF_TEMP_PREFIX)
    
    # Parameters for conversion
    convert_params = {
        'dpi': dpi,
        'fmt': output_format,
        'output_folder': temp_dir,  # Use our temporary directory
        'paths_only': False,        # Return image objects
        'use_pdftocairo': True,     # Faster conversion method
        'thread_count': 4           # Use multithreading for acceleration
    }
    
    # Add page parameters if specified
    if first_page is not None:
        convert_params['first_page'] = first_page
    if last_page is not None:
        convert_params['last_page'] = last_page
    if single_page is not None:
        convert_params['first_page'] = single_page
        convert_params['last_page'] = single_page
    
    try:
        # Convert PDF to images
        if pdf_content is not None:
            # If PDF content is provided as bytes
            images = convert_from_bytes(pdf_content, **convert_params)
        else:
            # If file path is provided
            images = convert_from_path(pdf_path, **convert_params)
        
        return images
    
    finally:
        # Delete the temporary directory and all files in it
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"PDF temporary directory deleted: {temp_dir}")
        except Exception as e:
            print(f"Error deleting temporary directory {temp_dir}: {str(e)}")
        
        # Additionally clean up other temporary files
        clean_temp_files()

def clean_temp_files():
    """
    Cleans up temporary files and directories created when converting PDF to images.
    
    This function removes all temporary files and directories with the PDF_TEMP_PREFIX
    prefix from the temporary files directory.
    """
    temp_dir = tempfile.gettempdir()
    try:
        # Find all temporary files and directories with our prefix
        pattern = os.path.join(temp_dir, f"{PDF_TEMP_PREFIX}*")
        temp_paths = glob.glob(pattern)
        
        count = 0
        # Delete found files and directories
        for path in temp_paths:
            try:
                if os.path.isdir(path):
                    # If it's a directory, delete recursively
                    shutil.rmtree(path, ignore_errors=True)
                    print(f"PDF temporary directory deleted: {path}")
                else:
                    # If it's a file, delete normally
                    os.remove(path)
                    print(f"PDF temporary file deleted: {path}")
                count += 1
            except Exception as e:
                print(f"Failed to delete {path}: {str(e)}")
                
        return count  # Return the number of deleted files and directories
    except Exception as e:
        print(f"Error cleaning PDF temporary files: {str(e)}")
        return 0

# Automatically clean temporary files when importing the module
# This will ensure cleanup when starting the bot
print("Cleaning PDF temporary files...")
num_files = clean_temp_files()
print(f"Deleted {num_files} PDF temporary files")
