from telegram import Bot
import time
from threading import Lock
from telegram.utils.request import Request
# Replace with your bot's API token
BOT_TOKEN = '6625435370:AAG2rib8Oplf02kzYp0eGNR-rlleoo338uE'

from telegram import Bot
from telegram.ext import Updater
from telegram.error import TimedOut, NetworkError
import logging

def check_pending_updates(bot_token: str, timeout: int = 30):
    """
    Check pending update requests in the Telegram bot update queue.
    
    Args:
        bot_token (str): Your Telegram bot token
        timeout (int): Request timeout in seconds (default: 30)
        
    Returns:
        list: List of pending updates
    """
    try:
        # Initialize bot and logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                          level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Create bot instance with custom timeout
        bot = Bot(token=bot_token, request=Request(
            connect_timeout=timeout,
            read_timeout=timeout
        ))
        
        # Get pending updates with timeout
        updates = bot.get_updates(timeout=timeout)
        
        if not updates:
            logger.info("No pending updates found")
            return []
            
        # Process and display pending updates
        pending_updates = []
        for update in updates:
            update_info = {
                'update_id': update.update_id,
                'message_id': update.message.message_id if update.message else None,
                'chat_id': update.message.chat_id if update.message else None,
                'timestamp': update.message.date if update.message else None,
                'text': update.message.text if update.message else None
            }
            pending_updates.append(update_info)
            logger.info(f"Found pending update: {update_info}")
            
        return pending_updates
        
    except TimedOut:
        logger.error("Request timed out. Consider increasing the timeout value or checking your internet connection.")
        return []
    except NetworkError as e:
        logger.error(f"Network error occurred: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error checking pending updates: {str(e)}")
        raise

def clear_update_queue(bot_token: str, timeout: int = 30, max_retries: int = 3):
    """
    Clear all pending updates from the queue.
    
    Args:
        bot_token (str): Your Telegram bot token
        timeout (int): Request timeout in seconds (default: 30)
        max_retries (int): Maximum number of retry attempts (default: 3)
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            bot = Bot(token=bot_token, request=dict(
                connect_timeout=timeout,
                read_timeout=timeout
            ))
            # Get the last update_id and offset by 1 to mark all as read
            updates = bot.get_updates(timeout=timeout)
            if updates:
                last_update_id = updates[-1].update_id
                bot.get_updates(offset=last_update_id + 1, timeout=timeout)
                logger.info("Update queue cleared successfully")
            return
            
        except TimedOut:
            logger.warning(f"Timeout on attempt {attempt + 1} of {max_retries}")
            if attempt == max_retries - 1:
                logger.error("Failed to clear update queue after maximum retries")
                raise
        except NetworkError as e:
            logger.error(f"Network error occurred: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error clearing update queue: {str(e)}")
            raise


# Check updates with a longer timeout
pending = check_pending_updates(BOT_TOKEN, timeout=60)  # 60 second timeout

# Clear queue with custom timeout and retries
clear_update_queue(BOT_TOKEN, timeout=60, max_retries=5)