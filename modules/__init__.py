from modules.rag_system import rag_system
from modules.speech_processor import speech_processor
from modules.query_processor import query_processor
from modules.data_manager import data_manager

# Initialize modules
def initialize_modules():
    """
    Initialize all modules.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize RAG system
        rag_system.setup()
        return True
    except Exception as e:
        import logging
        logging.error(f"Error initializing modules: {e}")
        return False