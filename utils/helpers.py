import os
import uuid
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_unique_id():
    """
    Generate a unique ID.
    
    Returns:
        str: A unique ID
    """
    return str(uuid.uuid4())

def get_timestamp():
    """
    Get current timestamp in ISO format.
    
    Returns:
        str: Current timestamp
    """
    return datetime.now().isoformat()

def save_conversation(user_query, assistant_response):
    """
    Save a conversation exchange to the conversation history.
    
    Args:
        user_query (str): The user's query
        assistant_response (str): The assistant's response
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        log_dir = 'conversation_logs'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.jsonl")
        
        # Create conversation entry
        entry = {
            'id': generate_unique_id(),
            'timestamp': get_timestamp(),
            'user_query': user_query,
            'assistant_response': assistant_response
        }
        
        # Append to log file
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
            
        return True
    
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        return False

def format_error_response(error_message):
    """
    Format an error response.
    
    Args:
        error_message (str): The error message
        
    Returns:
        dict: Formatted error response
    """
    return {
        'error': True,
        'message': error_message,
        'timestamp': get_timestamp()
    }

def sanitize_input(text):
    """
    Sanitize user input.
    
    Args:
        text (str): Text to sanitize
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove any potentially harmful characters or sequences
    sanitized = text.strip()
    return sanitized