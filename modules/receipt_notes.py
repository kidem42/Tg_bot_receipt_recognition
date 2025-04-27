import logging
from telegram import Update
from telegram.ext import ContextTypes
from modules.account_router import is_user_allowed
from modules.message_tracker import get_receipt_by_message
from modules.google_sheets import update_receipt_note_by_record_id

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
            success = False
            
            # Update receipt note in Google Sheets
            # Extract necessary data from receipt_info
            record_id = receipt_info.get("record_id")
            spreadsheet_id = receipt_info.get("spreadsheet_id")
            sheet_id = receipt_info.get("sheet_id")
            
            # If we don't have record_id, we can't update the note
            if not record_id:
                logger.error(f"Missing record_id for receipt, cannot update note")
                await update.message.reply_text("❌ Failed to add note. Receipt data is incomplete.")
                return
            
            # Update receipt note in Google Sheets using record_id
            success = update_receipt_note_by_record_id(
                record_id, 
                note_text, 
                user_id,
                spreadsheet_id,
                sheet_id
            )
            logger.info(f"Attempting to update note using record_id: {record_id}")
            
            if success:
                await update.message.reply_text("✅ Note added successfully to the receipt!", reply_to_message_id=update.message.message_id)
                logger.info(f"Note added to receipt for user {user_id}")
            else:
                await update.message.reply_text("❌ Failed to add note. Please try again.")
                logger.error(f"Failed to add note for user {user_id}")
        else:
            await update.message.reply_text("❌ Could not find the associated receipt or note is too old (max 14 days).")
            logger.warning(f"Receipt not found for message_id {original_message.message_id} from user {user_id}")

def register_receipt_message(user_id, message_id, sheet_row_id, message_text, record_id=None, group_id=None, spreadsheet_id=None, sheet_id=None):
    """
    Register a receipt message for tracking
    
    Args:
        user_id: Telegram user ID
        message_id: Message ID
        sheet_row_id: Row ID in Google Sheets
        message_text: Message text
        record_id: Unique record ID (UUID)
        group_id: User group ID
        spreadsheet_id: Google Spreadsheet ID
        sheet_id: Google Sheet ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    from modules.message_tracker import add_message_tracking
    return add_message_tracking(user_id, message_id, sheet_row_id, message_text, record_id, group_id, spreadsheet_id, sheet_id)
