from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from modules.receipt_notes import handle_receipt_note, register_receipt_message
from io import BytesIO
import time
import asyncio
import os

from modules.user_validator import is_user_allowed
from modules.file_processor import get_formatted_filename
from modules.google_script import get_user_folder_id, upload_file_to_drive
from modules.openai_client import analyze_image
from config import MAX_FILE_SIZE
from config import MAX_PDF_PAGES

# Cache for user folder IDs
user_folder_cache = {}

# For tracking delayed messages
batch_trackers = {}

# For tracking files with processing errors
failed_files = {}

# For tracking the processing status of files in a batch
batch_files = {}

# Maximum file size in bytes (5 MB)
#MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes

# Wait time before sending a message (in seconds)
BATCH_TIMEOUT = 3.0

# URL for direct access to Google Drive folders
GOOGLE_DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/{folder_id}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    user_id = update.effective_user.id
    
    if is_user_allowed(user_id):
        await update.message.reply_text(
            f"👋 Hello, {update.effective_user.first_name}! I'm your Receipt Bot!\n\n"
            f"📝 I can help you:\n"
            f"• 📸 Upload and organize photos\n"
            f"• 📄 Process PDF documents\n"
            f"• 🧾 Analyze receipts automatically\n"
            f"• 📊 Track expenses in Google Sheets\n"
            f"• 📝 Add notes to receipts by replying to messages\n\n"
            f"📤 All files are stored in Google Drive folder.\n"
            f"⚠️ Maximum file size: 5 MB\n\n"
            f"🔍 Send me a receipt photo or PDF to get started!\n"
            f"❓ Type /help for more information."
        )
    else:
        await update.message.reply_text(
            "⛔ Sorry, you don't have access to this bot. Please contact the administrator if you believe this is an error."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command"""
    user_id = update.effective_user.id
    
    if is_user_allowed(user_id):
        help_text = (
            "🤖 *Bot Features and Commands*\n\n"
            "📋 *File Support:*\n"
            "• 📸 Photos - Send receipts directly from your camera\n"
            "• 📄 Documents - Upload PDFs, images\n"
            "• 🧾 Receipts - Automatically extract amount, date, items\n\n"
            
            "🔄 *Processing Flow:*\n"
            "1. Send me a receipt (photo or PDF)\n"
            "2. I'll upload it to your Google Drive folder\n"
            "3. 🔍 AI will analyze the receipt content\n"
            "4. 📊 Data will be added to your expense spreadsheet\n\n"
            
            "⚠️ *Limitations:*\n"
            "• Maximum file size: 5 MB\n"
            "• PDF limit: Up to 5 pages per document\n"
            "• Currently, video and audio files are not supported\n\n"
            
            "🔔 *Tips:*\n"
            "• For best results, ensure receipts are clearly visible\n"
            "• When uploading multiple files, wait for the confirmation message\n"
            "• You can click on the Google Drive link to view all your uploaded files\n\n"
            
            "📝 *Receipt Notes:*\n"
            "• Reply to any receipt message with text to add notes\n"
            "• Notes are saved directly to your expense spreadsheet\n"
            "• Notes can be added up to 14 days after uploading a receipt\n\n"
            
            "💬 If you need more assistance, please contact the administrator."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "⛔ Sorry, you don't have access to this bot. Please contact the administrator if you believe this is an error."
        )

def get_cached_folder_id(user_id, username):
    """
    Gets the user folder ID from cache or creates a new entry
    
    Args:
        user_id (int): Telegram user ID
        username (str): Username
        
    Returns:
        str: User folder ID
    """
    # Cache key - user ID
    cache_key = str(user_id)
    
    # If folder ID is already in cache, return it
    if cache_key in user_folder_cache:
        print(f"Using cached folder ID for user {user_id}_{username}")
        return user_folder_cache[cache_key]
    
    # Otherwise get folder ID and cache it
    folder_id = get_user_folder_id(user_id, username)
    if folder_id:
        user_folder_cache[cache_key] = folder_id
    
    return folder_id

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for photos"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        await update.message.reply_text("Sorry, you don't have access to this bot.")
        return
    
    # Register the file in the tracking system at the beginning of processing
    folder_id = get_cached_folder_id(user_id, update.effective_user.username or update.effective_user.first_name)
    file_id = await register_file(update, context, user_id, folder_id)
    
    # Get user information
    username = update.effective_user.username or update.effective_user.first_name
    
    # Get the highest quality photo
    photo = update.message.photo[-1]
    
    # Check file size
    if hasattr(photo, 'file_size') and photo.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            "⚠️ Photo is too large! Maximum file size: 5 MB."
        )
        return
    
    # Download the photo
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Additional size check after download
    if len(photo_bytes) > MAX_FILE_SIZE:
        await update.message.reply_text(
            "⚠️ Photo is too large! Maximum file size: 5 MB."
        )
        return
    
    # Original filename for photo
    original_filename = f"photo_{photo.file_id}.jpg"
    formatted_filename = get_formatted_filename(user_id, original_filename)
    mime_type = "image/jpeg"
    
    # Get folder ID from cache or request it
    folder_id = get_cached_folder_id(user_id, username)
    
    # Upload file to Google Drive
    success = upload_file_to_drive(
        photo_bytes, 
        formatted_filename, 
        folder_id, 
        mime_type,
        user_id
    )
    
    if success:
        # Get file URL on Google Drive
        file_url = f"https://drive.google.com/file/d/{success}/view"
        
        # Send message about starting analysis
        processing_message = await update.message.reply_text(
            "🔍 Analyzing receipt image. This may take some time..."
        )
        
        try:
            # Convert image to a format compatible with OpenAI
            # For photos from Telegram, conversion is usually not required,
            # but we check just in case
            from modules.img_converter import convert_image_to_compatible_format
            compatible_image, compatible_mime = convert_image_to_compatible_format(
                photo_bytes, original_filename
            )
            
            if compatible_image:
                # Analyze image with OpenAI
                receipt_data = analyze_image(compatible_image)
                
                if receipt_data:
                    # Create a record in Google Sheets
                    from modules.google_sheets import create_expense_record
                    record_created = create_expense_record(
                        user_id, username, receipt_data, file_url
                    )
                    
                    if record_created:
                        # Delete processing message
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=processing_message.message_id
                        )
                        
                        # Send message about successful analysis
                        items_text = receipt_data.get('items', 'Not recognized')
                        message = await update.message.reply_text(
                            f"✅ Receipt successfully analyzed and saved!\n\n"
                            f"💰 Amount: {receipt_data.get('total_amount')} {receipt_data.get('currency')}\n"
                            f"💸 Taxes: {receipt_data.get('tax_amount')} {receipt_data.get('currency')}\n"
                            f"📅 Date: {receipt_data.get('date')}\n"
                            f"🕓 Time: {receipt_data.get('time')}\n"
                            f"🛒 Items: {items_text}"
                        )
                        
                        # Register message for receipt notes
                        register_receipt_message(user_id, message.message_id, record_created, message.text)
                    else:
                        # Delete processing message
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=processing_message.message_id
                        )
                        
                        await update.message.reply_text(
                            "⚠️ File uploaded, but failed to create a record in the spreadsheet."
                        )
                else:
                    # Delete processing message
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id
                    )
                    
                    await update.message.reply_text(
                        "⚠️ Failed to recognize receipt in the image."
                    )
            else:
                # Delete processing message
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id
                )
                
                await update.message.reply_text(
                    "⚠️ Failed to convert image to a format supported by the analyzer."
                )
        except Exception as e:
            # Delete processing message
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id
            )
            
            print(f"Error analyzing image: {str(e)}")
            
            # Add file to the list of files with errors
            user_key = str(user_id)
            if user_key not in failed_files:
                failed_files[user_key] = []
            
            failed_files[user_key].append(original_filename)
            
            await update.message.reply_text(
                f"⚠️ An error occurred while analyzing the image '{original_filename}'. "
                f"The file was uploaded to the drive but not processed. Please try sending it again."
            )
            
            # Clean up temporary files
            from modules.img_converter import clear_temp_files
            clear_temp_files()
    
    # Mark file as processed
    user_key = str(user_id)
    if user_key in batch_files and file_id in batch_files[user_key]:
        batch_files[user_key][file_id]['status'] = 'completed'
        
    # Start timer for sending batch completion notification
    if user_key in batch_trackers:
        # If previous task is still active, cancel it
        if batch_trackers[user_key]['task'] and not batch_trackers[user_key]['task'].done():
            batch_trackers[user_key]['task'].cancel()
        
        # Create a new task for sending notification
        task = asyncio.create_task(
            send_batch_complete(context, user_key)
        )
        batch_trackers[user_key]['task'] = task

async def register_file(update, context, user_id, folder_id):
    """
    Registers a file in the tracking system without starting the notification timer
    
    Args:
        update: Telegram Update object
        context: Bot context
        user_id: User ID
        folder_id: ID of the folder where files are uploaded
        
    Returns:
        str: File ID for tracking processing status
    """
    user_key = str(user_id)
    current_time = time.time()
    message_id = update.message.message_id
    file_id = f"{user_key}_{message_id}"
    
    # Register file in tracking structure
    if user_key not in batch_files:
        batch_files[user_key] = {}
    
    # Add file to the list of processing files
    batch_files[user_key][file_id] = {
        'status': 'processing',
        'timestamp': current_time
    }
    
    # Create or update tracker for user
    if user_key not in batch_trackers:
        # First user upload - create a new tracker
        batch_trackers[user_key] = {
            'count': 1,
            'last_update': current_time,
            'chat_id': update.effective_chat.id,
            'folder_id': folder_id,  # Save folder ID
            'task': None,
            'pending_files': [file_id]
        }
    else:
        # Tracker already exists - update counter and last update time
        tracker = batch_trackers[user_key]
        
        # Update tracker
        tracker['count'] += 1
        tracker['last_update'] = current_time
        tracker['folder_id'] = folder_id  # Update folder ID (just in case something changed)
        
        # Add file to the list of pending files
        if 'pending_files' not in tracker:
            tracker['pending_files'] = []
        tracker['pending_files'].append(file_id)
    
    # Return file ID for subsequent status updates
    return file_id

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for documents"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        await update.message.reply_text("Sorry, you don't have access to this bot.")
        return
    
    # Register the file in the tracking system at the beginning of processing
    folder_id = get_cached_folder_id(user_id, update.effective_user.username or update.effective_user.first_name)
    file_id = await register_file(update, context, user_id, folder_id)
    
    # Get user information
    username = update.effective_user.username or update.effective_user.first_name
    
    # Get document
    document = update.message.document
    original_filename = document.file_name
    
    # Check file size
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"⚠️ File '{original_filename}' is too large! Maximum file size: 5 MB."
        )
        return
    
    formatted_filename = get_formatted_filename(user_id, original_filename)
    mime_type = document.mime_type or "application/octet-stream"
    
    # Download document
    doc_file = await context.bot.get_file(document.file_id)
    doc_bytes = await doc_file.download_as_bytearray()
    
    # Get folder ID from cache or request it
    folder_id = get_cached_folder_id(user_id, username)
    
    # Upload file
    success = upload_file_to_drive(
        doc_bytes, 
        formatted_filename, 
        folder_id, 
        mime_type,
        user_id
    )
    
    # Check if the document is a PDF file or image
    if success and (mime_type == "application/pdf" or mime_type.startswith("image/")):
        # Get file URL on Google Drive
        file_url = f"https://drive.google.com/file/d/{success}/view"
        
        # Determine file type for message
        file_type_msg = "PDF document" if mime_type == "application/pdf" else "image"
        
        # Send message about starting analysis
        processing_message = await update.message.reply_text(
            f"🔍 Analyzing {file_type_msg}. This may take some time..."
        )
        
        try:
            # Process depending on file type
            if mime_type == "application/pdf":
                # Convert PDF to images
                from modules.pdf_to_image import pdf_to_image, clean_temp_files
                images = pdf_to_image(pdf_content=doc_bytes)
                
                # Check if PDF has multiple pages
                if len(images) > 1:
                    # Update processing message
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text=f"🔍 Multi-page PDF detected ({len(images)} pages). Analyzing up to {min(MAX_PDF_PAGES, len(images))} pages as a single receipt..."
                    )
                    
                    # Limit pages to MAX_PDF_PAGES
                    analysis_images = images[:min(MAX_PDF_PAGES, len(images))]
                    
                    # Convert each page to bytes
                    image_bytes_list = []
                    for img in analysis_images:
                        img_byte_arr = BytesIO()
                        if img.mode == 'RGBA' or img.mode == 'LA':
                            img.save(img_byte_arr, format='PNG')
                        else:
                            img.save(img_byte_arr, format='JPEG')
                        image_bytes_list.append(img_byte_arr.getvalue())
                    
                    # Analyze all pages as a single receipt
                    from modules.openai_client import analyze_images_batch
                    receipt_data = analyze_images_batch(image_bytes_list)
                else:
                    # For single page PDF, use existing logic
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text="🔍 PDF converted to image. Analyzing content..."
                    )
                    
                    first_page = images[0]
                    img_byte_arr = BytesIO()
                    if first_page.mode == 'RGBA' or first_page.mode == 'LA':
                        first_page.save(img_byte_arr, format='PNG')
                    else:
                        first_page.save(img_byte_arr, format='JPEG')
                    img_bytes = img_byte_arr.getvalue()
                    
                    # Analyze image with OpenAI
                    from modules.openai_client import analyze_image
                    receipt_data = analyze_image(img_bytes)
            elif mime_type.startswith("image/"):
                # For images use converter
                from modules.img_converter import convert_image_to_compatible_format
                compatible_image, compatible_mime = convert_image_to_compatible_format(
                    doc_bytes, original_filename
                )
                
                # If conversion is successful, create a list with one image
                if compatible_image:
                    # Create PIL Image from bytes
                    from PIL import Image
                    import io
                    images = [Image.open(io.BytesIO(compatible_image))]
                    
                    # Update processing message
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text="🔍 Analyzing receipt image..."
                    )
                    
                    # Convert PIL Image to bytes
                    img_byte_arr = BytesIO()
                    if images[0].mode == 'RGBA' or images[0].mode == 'LA':
                        images[0].save(img_byte_arr, format='PNG')
                    else:
                        images[0].save(img_byte_arr, format='JPEG')
                    img_bytes = img_byte_arr.getvalue()
                    
                    # Analyze image with OpenAI
                    from modules.openai_client import analyze_image
                    receipt_data = analyze_image(img_bytes)
                else:
                    images = []
                    receipt_data = None
            else:
                # Unsupported file type
                images = []
                receipt_data = None
            
            if receipt_data:
                # Create a record in Google Sheets
                from modules.google_sheets import create_expense_record
                record_created = create_expense_record(
                    user_id, username, receipt_data, file_url
                )
                
                if record_created:
                    # Delete processing message
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id
                    )
                    
                    # Send message about successful analysis
                    items_text = receipt_data.get('items', 'Not recognized')
                    # Determine file type for message
                    file_type = "PDF document" if mime_type == "application/pdf" else "Image"
                    
                    message = await update.message.reply_text(
                        f"✅ {file_type} successfully analyzed and saved!\n\n"
                        f"💰 Amount: {receipt_data.get('total_amount')} {receipt_data.get('currency')}\n"
                        f"💸 Taxes: {receipt_data.get('tax_amount')} {receipt_data.get('currency')}\n"
                        f"📅 Date: {receipt_data.get('date')}\n"
                        f"🕓 Time: {receipt_data.get('time')}\n"
                        f"🛒 Items: {items_text}"
                    )
                    
                    # Register message for receipt notes
                    register_receipt_message(user_id, message.message_id, record_created, message.text)
                else:
                    # Delete processing message
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id
                    )
                    
                    await update.message.reply_text(
                        "⚠️ File uploaded, but failed to create a record in the spreadsheet."
                    )
            else:
                # Delete processing message
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id
                )
                
                # Determine file type for error message
                file_type = "PDF document" if mime_type == "application/pdf" else "image"
                
                await update.message.reply_text(
                    f"⚠️ Failed to recognize receipt in the {file_type}."
                )
        except Exception as e:
            # Delete processing message
            if 'processing_message' in locals():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id
                )
            
            print(f"Error processing PDF: {str(e)}")
            
            # Add file to the list of files with errors
            user_key = str(user_id)
            if user_key not in failed_files:
                failed_files[user_key] = []
            
            failed_files[user_key].append(original_filename)
            
            # Determine file type for error message
            file_type = "PDF document" if mime_type == "application/pdf" else "image"
            
            await update.message.reply_text(
                f"⚠️ An error occurred while processing the {file_type} '{original_filename}'. "
                f"The file was uploaded to the drive but not processed. Please try sending it again."
            )
            
            # Clean up temporary files depending on file type
            if mime_type == "application/pdf":
                from modules.pdf_to_image import clean_temp_files
                clean_temp_files()
            else:
                from modules.img_converter import clear_temp_files
                clear_temp_files()
    
    # Mark file as processed
    user_key = str(user_id)
    if user_key in batch_files and file_id in batch_files[user_key]:
        batch_files[user_key][file_id]['status'] = 'completed'
        
    # Start timer for sending batch completion notification
    if user_key in batch_trackers:
        # If previous task is still active, cancel it
        if batch_trackers[user_key]['task'] and not batch_trackers[user_key]['task'].done():
            batch_trackers[user_key]['task'].cancel()
        
        # Create a new task for sending notification
        task = asyncio.create_task(
            send_batch_complete(context, user_key)
        )
        batch_trackers[user_key]['task'] = task

async def track_upload(update, context, user_id, folder_id):
    """
    Tracks file uploads and groups them into batches
    for sending a single notification
    
    Args:
        update: Telegram Update object
        context: Bot context
        user_id: User ID
        folder_id: ID of the folder where files are uploaded
        
    Returns:
        str: File ID for tracking processing status
    """
    user_key = str(user_id)
    current_time = time.time()
    message_id = update.message.message_id
    file_id = f"{user_key}_{message_id}"
    
    # Register file in tracking structure
    if user_key not in batch_files:
        batch_files[user_key] = {}
    
    # Add file to the list of processing files
    batch_files[user_key][file_id] = {
        'status': 'processing',
        'timestamp': current_time
    }
    
    # Create or update tracker for user
    if user_key not in batch_trackers:
        # First user upload - create a new tracker
        batch_trackers[user_key] = {
            'count': 1,
            'last_update': current_time,
            'chat_id': update.effective_chat.id,
            'folder_id': folder_id,  # Save folder ID
            'task': None,
            'pending_files': [file_id]
        }
    else:
        # Tracker already exists - update counter and last update time
        tracker = batch_trackers[user_key]
        
        # If previous task is still active, cancel it
        if tracker['task'] and not tracker['task'].done():
            tracker['task'].cancel()
        
        # Update tracker
        tracker['count'] += 1
        tracker['last_update'] = current_time
        tracker['folder_id'] = folder_id  # Update folder ID (just in case something changed)
        
        # Add file to the list of pending files
        if 'pending_files' not in tracker:
            tracker['pending_files'] = []
        tracker['pending_files'].append(file_id)
    
    # Create a new task for sending notification
    task = asyncio.create_task(
        send_batch_complete(context, user_key)
    )
    batch_trackers[user_key]['task'] = task
    
    # Return file ID for subsequent status updates
    return file_id

async def send_batch_complete(context, user_key):
    """
    Sends a notification about the completion of a batch file upload
    after the timeout expires and all files are processed
    """
    # Wait the specified time before sending notification
    await asyncio.sleep(BATCH_TIMEOUT)
    
    # Make sure the tracker still exists
    if user_key in batch_trackers:
        tracker = batch_trackers[user_key]
        
        # Check if all files in the batch are processed
        all_files_processed = True
        if 'pending_files' in tracker and tracker['pending_files']:
            for file_id in tracker['pending_files']:
                # Check file status
                if user_key in batch_files and file_id in batch_files[user_key]:
                    if batch_files[user_key][file_id]['status'] != 'completed':
                        all_files_processed = False
                        break
        
        # If not all files are processed, delay sending the message
        if not all_files_processed:
            # Create a new task for rechecking after 1 second
            task = asyncio.create_task(
                send_batch_complete(context, user_key)
            )
            batch_trackers[user_key]['task'] = task
            return
        
        # All files processed, send message
        count = tracker['count']
        chat_id = tracker['chat_id']
        folder_id = tracker['folder_id']
        
        # Form Google Drive folder URL
        folder_url = GOOGLE_DRIVE_FOLDER_URL.format(folder_id=folder_id)
        
        # Create keyboard with button to open folder
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Open folder", url=folder_url)]
        ])
        
        # Form message
        message = (
            f"📤 Upload complete!\n\n"
            f"✅ Successfully uploaded: {count} file(s)"
        )
        
        # Check if there are files with processing errors
        if user_key in failed_files and failed_files[user_key]:
            failed_count = len(failed_files[user_key])
            failed_list = ", ".join(failed_files[user_key])
            
            message += f"\n\n⚠️ {failed_count} file(s) could not be processed: {failed_list}"
            message += "\nFiles were uploaded to the drive but not processed. Please try sending them again."
            
            # Clear the list of error files for this user
            failed_files[user_key] = []
        
        # Send message with keyboard
        await context.bot.send_message(
            chat_id=chat_id, 
            text=message,
            reply_markup=keyboard
        )
        
        # Clear user file data
        if user_key in batch_files:
            del batch_files[user_key]
        
        # Delete tracker
        del batch_trackers[user_key]

async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for unsupported message types"""
    user_id = update.effective_user.id
    
    if is_user_allowed(user_id):
        await update.message.reply_text(
            "I can only accept photos and documents. "
            "Video and audio files are not supported yet."
        )

def setup_handlers(application):
    """Setup command and message handlers"""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # File handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Text message handler for notes (only for replies)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY, handle_receipt_note
    ))
    
    # Handler for unsupported types
    application.add_handler(MessageHandler(
        filters.VIDEO | filters.AUDIO | filters.VOICE, 
        handle_unsupported
    ))
