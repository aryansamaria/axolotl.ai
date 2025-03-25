import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Paths
    STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage')
    CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wise_help_content.csv')
    AUDIO_INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'input')
    AUDIO_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'output')
    
    # Speech settings
    TTS_LANGUAGE = 'en'
    STT_MODEL = 'whisper-1'
    
    # RAG settings
    FALLBACK_MODEL = 'gpt-3.5-turbo'
    
    # Flask settings
    DEBUG = True
    PORT = 5000
    HOST = '0.0.0.0'
    
    # Create necessary directories
    @staticmethod
    def setup_directories():
        os.makedirs(Config.STORAGE_DIR, exist_ok=True)
        os.makedirs(Config.AUDIO_INPUT_DIR, exist_ok=True)
        os.makedirs(Config.AUDIO_OUTPUT_DIR, exist_ok=True)