import logging
from telegram import Update
from telegram.ext import ContextTypes
from modules.user_validator import is_user_allowed
from modules.message_tracker import get_receipt_by_message
from modules.google_sheets import update_receipt_note

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('receipt_notes')

async def handle_receipt_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for receipt notes (text messages that are replies to bot messages)
    
    Args:
        update: Telegram Update object
        context: Bot context
    """
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        await update.message.reply_text("Sorry, you don't have access to this bot.")
        return
    
    # Check if message is a reply
    if not update.message.reply_to_message:
        return
    
    original_message = update.message.reply_to_message
    
    # Check if original message is from the bot and contains receipt info
    if original_message.from_user.id == context.bot.id and "successfully analyzed and saved" in original_message.text:
        # Get note text
        note_text = update.message.text
        
        # Find associated receipt record
        receipt_info = get_receipt_by_message(user_id, original_message.message_id)
        
        if receipt_info:
            # Update receipt note in Google Sheets
            success = update_receipt_note(receipt_info["sheet_row_id"], note_text)
            
            if success:
                await update.message.reply_text("✅ Note added successfully to the receipt!", reply_to_message_id=update.message.message_id)
                logger.info(f"Note added to receipt for user {user_id}")
            else:
                await update.message.reply_text("❌ Failed to add note. Please try again.")
                logger.error(f"Failed to add note for user {user_id}")
        else:
            await update.message.reply_text("❌ Could not find the associated receipt or note is too old (max 14 days).")
            logger.warning(f"Receipt not found for message_id {original_message.message_id} from user {user_id}")

def register_receipt_message(user_id, message_id, sheet_row_id, message_text):
    """
    Register a receipt message for tracking
    
    Args:
        user_id: Telegram user ID
        message_id: Message ID
        sheet_row_id: Row ID in Google Sheets
        message_text: Message text
        
    Returns:
        bool: True if successful, False otherwise
    """
    from modules.message_tracker import add_message_tracking
    return add_message_tracking(user_id, message_id, sheet_row_id, message_text)
