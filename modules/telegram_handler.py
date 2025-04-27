from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from modules.receipt_notes import handle_receipt_note, register_receipt_message
from io import BytesIO
import os

from modules.account_router import is_user_allowed, get_user_group
from modules.file_processor import get_formatted_filename
from modules.google_script import get_user_folder_id, upload_file_to_drive
from modules.openai_client import analyze_image
from config import MAX_FILE_SIZE
from config import MAX_PDF_PAGES
from config import GROUP_MESSAGE_TEMPLATES
from config import GOOGLE_DRIVE_FOLDER_URL
from config import MAX_ITEMS_TEXT_LENGTH

# Cache for user folder IDs
user_folder_cache = {}

# For tracking files with processing errors during the current session
failed_files = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    user_id = update.effective_user.id
    print(f"Start command received from user_id: {user_id}, type: {type(user_id)}")
    
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
                    result = create_expense_record(
                        user_id, username, receipt_data, file_url
                    )
                    
                    if result:
                        # Delete processing message
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=processing_message.message_id
                        )
                        
                        # Send message about successful analysis
                        items_text = receipt_data.get('items', 'Not recognized')
                        
                        # Truncate items text for display in message if it's too long
                        display_items_text = items_text
                        if items_text is not None and len(items_text) > MAX_ITEMS_TEXT_LENGTH:
                            display_items_text = items_text[:MAX_ITEMS_TEXT_LENGTH] + "..."
                        
                        # Get user group and check for template
                        user_group = get_user_group(user_id)
                        template = None
                        if user_group is not None and user_group in GROUP_MESSAGE_TEMPLATES:
                            template = GROUP_MESSAGE_TEMPLATES[user_group]
                        
                        # Construct the message
                        message_text = (
                            f"✅ Receipt successfully analyzed and saved!\n\n"
                            f"💰 Amount: {receipt_data.get('total_amount')} {receipt_data.get('currency')}\n"
                            #f"💸 Taxes: {receipt_data.get('tax_amount')} {receipt_data.get('currency')}\n"
                            f"📅 Date: {receipt_data.get('date')}\n"
                            #f"🕓 Time: {receipt_data.get('time')}\n"
                            f"🛒 Items: {display_items_text}"
                        )
                        
                        # Add template if it exists
                        if template:
                            # Create folder URL for template
                            folder_url = GOOGLE_DRIVE_FOLDER_URL.format(folder_id=folder_id)
                            
                            # Replace placeholders in template
                            formatted_template = template.format(folder_url=folder_url)
                            
                            message_text += f"\n\n{formatted_template}"
                        
                        # Send the message with Markdown formatting if template exists
                        if template:
                            message = await update.message.reply_text(message_text, parse_mode="Markdown")
                        else:
                            message = await update.message.reply_text(message_text)
                        
                        # Register message for receipt notes with all data
                        register_receipt_message(
                            user_id, 
                            message.message_id, 
                            result["row_id"], 
                            message.text,
                            result["record_id"],
                            result["group_id"],
                            result["spreadsheet_id"],
                            result["sheet_id"]
                        )
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
            
            await update.message.reply_text(
                f"⚠️ An error occurred while analyzing the image '{original_filename}'. "
                f"The file was uploaded to the drive but not processed. Please try sending it again."
            )
            
            # Clean up temporary files
            from modules.img_converter import clear_temp_files
            clear_temp_files()

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for documents"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        await update.message.reply_text("Sorry, you don't have access to this bot.")
        return
    
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
                result = create_expense_record(
                    user_id, username, receipt_data, file_url
                )
                
                if result:
                    # Delete processing message
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id
                    )
                    
                    # Send message about successful analysis
                    items_text = receipt_data.get('items', 'Not recognized')
                    
                    # Truncate items text for display in message if it's too long
                    display_items_text = items_text
                    if items_text is not None and len(items_text) > MAX_ITEMS_TEXT_LENGTH:
                        display_items_text = items_text[:MAX_ITEMS_TEXT_LENGTH] + "..."
                    # Determine file type for message
                    file_type = "PDF document" if mime_type == "application/pdf" else "Image"
                    
                    # Get user group and check for template
                    user_group = get_user_group(user_id)
                    template = None
                    if user_group is not None and user_group in GROUP_MESSAGE_TEMPLATES:
                        template = GROUP_MESSAGE_TEMPLATES[user_group]
                    
                    # Construct the message
                    message_text = (
                        f"✅ {file_type} successfully analyzed and saved!\n\n"
                        f"💰 Amount: {receipt_data.get('total_amount')} {receipt_data.get('currency')}\n"
                        #f"💸 Taxes: {receipt_data.get('tax_amount')} {receipt_data.get('currency')}\n"
                        f"📅 Date: {receipt_data.get('date')}\n"
                        #f"🕓 Time: {receipt_data.get('time')}\n"
                        f"🛒 Items: {display_items_text}"
                    )
                    
                    # Add template if it exists
                    if template:
                        # Create folder URL for template
                        folder_url = GOOGLE_DRIVE_FOLDER_URL.format(folder_id=folder_id)
                        
                        # Replace placeholders in template
                        formatted_template = template.format(folder_url=folder_url)
                        
                        message_text += f"\n\n{formatted_template}"
                    
                    # Send the message with Markdown formatting if template exists
                    if template:
                        message = await update.message.reply_text(message_text, parse_mode="Markdown")
                    else:
                        message = await update.message.reply_text(message_text)
                    
                    # Register message for receipt notes with all data
                    register_receipt_message(
                        user_id, 
                        message.message_id, 
                        result["row_id"], 
                        message.text,
                        result["record_id"],
                        result["group_id"],
                        result["spreadsheet_id"],
                        result["sheet_id"]
                    )
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

def setup_handlers(application):
    """Sets up all the handlers for the Telegram bot"""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Message handlers for different types of content
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Handler for unsupported message types
    unsupported_filter = ~filters.PHOTO & ~filters.Document.ALL & ~filters.COMMAND & ~filters.TEXT
    application.add_handler(MessageHandler(unsupported_filter, handle_unsupported))
    
    # Handler for replies to receipt messages
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_receipt_note))
    
    return application

async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for unsupported message types"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        await update.message.reply_text("Sorry, you don't have access to this bot.")
        return
    
    # Get message type
    message_type = "unknown"
    if update.message.video:
        message_type = "video"
    elif update.message.audio:
        message_type = "audio"
    elif update.message.voice:
        message_type = "voice message"
    elif update.message.sticker:
        message_type = "sticker"
    elif update.message.animation:
        message_type = "animation/GIF"
    elif update.message.location:
        message_type = "location"
    elif update.message.contact:
        message_type = "contact"
    
    # Send message about unsupported type
    await update.message.reply_text(
        f"⚠️ Sorry, {message_type} files are not supported.\n\n"
        f"Please send receipts as photos or PDF documents."
    )
