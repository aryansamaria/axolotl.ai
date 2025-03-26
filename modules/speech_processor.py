import os
import base64
import io
import logging
import openai
import sounddevice as sd
from scipy.io.wavfile import write
import pygame
from gtts import gTTS
from config import Config
import threading
import uuid

# Configure logging
logger = logging.getLogger(__name__)

class SpeechProcessor:
    """
    Handles speech-to-text and text-to-speech operations.
    """
    def __init__(self):
        """Initialize the speech processor."""
        # Set OpenAI API key
        openai.api_key = Config.OPENAI_API_KEY
        
        # Add this dictionary to track active speech tasks
        self.active_speech_tasks = {}
        self.speech_lock = threading.Lock()
        
    def transcribe_audio_file(self, audio_file_path):
        """
        Transcribe an audio file to text using OpenAI's Whisper API.
        
        Args:
            audio_file_path (str): Path to the audio file
            
        Returns:
            str: Transcribed text
        """
        try:
            # Try newer OpenAI client format (v1.0.0+)
            try:
                client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
                with open(audio_file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model=Config.STT_MODEL,
                        file=audio_file
                    )
                transcription_text = transcription.text
            except AttributeError:
                # Fall back to older format (pre-v1.0.0)
                with open(audio_file_path, "rb") as audio_file:
                    transcription = openai.Audio.transcribe(
                        Config.STT_MODEL,
                        audio_file
                    )
                transcription_text = transcription.text
                
            logger.info(f"Transcribed: {transcription_text}")
            return transcription_text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    def transcribe_audio_data(self, audio_data):
        """
        Transcribe audio data to text.
        
        Args:
            audio_data (str): Base64-encoded audio data
            
        Returns:
            str: Transcribed text
        """
        try:
            # Generate a unique filename
            import uuid
            filename = os.path.join(Config.AUDIO_INPUT_DIR, f"{uuid.uuid4()}.wav")
            
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
            
            # Save audio file temporarily
            with open(filename, 'wb') as f:
                f.write(audio_bytes)
            
            # Transcribe the audio file
            transcription_text = self.transcribe_audio_file(filename)
            
            # Clean up temporary file
            os.remove(filename)
            
            return transcription_text
            
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            return None
    
    def text_to_speech_file(self, text, output_path):
        """
        Convert text to speech and save as an audio file.
        
        Args:
            text (str): Text to convert to speech
            output_path (str): Path to save the audio file
            
        Returns:
            str: Path to the saved audio file
        """
        try:
            tts = gTTS(text=text, lang=Config.TTS_LANGUAGE)
            tts.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return None
    
    def text_to_speech_data(self, text, session_id=None):
        """
        Convert text to speech and return as base64-encoded data.
        This version supports cancellation of in-progress speech synthesis.
        
        Args:
            text (str): Text to convert to speech
            session_id (str, optional): Session ID for tracking
            
        Returns:
            str: Base64-encoded audio data
        """
        try:
            # Generate a unique ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                
            # Track this task
            with self.speech_lock:
                self.active_speech_tasks[session_id] = {
                    'cancelled': False,
                    'text': text[:30] + '...' if len(text) > 30 else text
                }
            
            # Generate audio in memory
            audio_io = io.BytesIO()
            tts = gTTS(text=text, lang=Config.TTS_LANGUAGE)
            
            # Check if cancelled before writing to file
            if self._is_task_cancelled(session_id):
                logger.info(f"Speech synthesis cancelled for session {session_id}")
                return None
                
            tts.write_to_fp(audio_io)
            audio_io.seek(0)
            
            # Check if cancelled before encoding
            if self._is_task_cancelled(session_id):
                logger.info(f"Speech synthesis cancelled for session {session_id}")
                return None
            
            # Convert to base64
            audio_base64 = base64.b64encode(audio_io.read()).decode('utf-8')
            
            # Remove task from tracking
            with self.speech_lock:
                if session_id in self.active_speech_tasks:
                    del self.active_speech_tasks[session_id]
                    
            return f"data:audio/mp3;base64,{audio_base64}"
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            
            # Clean up tracking
            with self.speech_lock:
                if session_id in self.active_speech_tasks:
                    del self.active_speech_tasks[session_id]
                    
            return None
    
    def play_audio(self, audio_path):
        """
        Play an audio file.
        
        Args:
            audio_path (str): Path to the audio file
        """
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
    
    def record_audio(self, seconds=5, sample_rate=44100):
        """
        Record audio from the microphone.
        
        Args:
            seconds (int): Duration of recording in seconds
            sample_rate (int): Sample rate for the recording
            
        Returns:
            str: Path to the saved audio file
        """
        try:
            logger.info("Recording audio...")
            import uuid
            filename = os.path.join(Config.AUDIO_INPUT_DIR, f"{uuid.uuid4()}.wav")
            
            # Record audio
            recording = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=2)
            sd.wait()  # Wait until recording is finished
            
            # Save as WAV file
            write(filename, sample_rate, recording)
            logger.info(f"Audio saved to {filename}")
            
            return filename
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return None

    def _is_task_cancelled(self, session_id):
        """
        Check if a task has been cancelled.
        
        Args:
            session_id (str): The session ID to check
            
        Returns:
            bool: True if cancelled, False otherwise
        """
        with self.speech_lock:
            if session_id in self.active_speech_tasks:
                return self.active_speech_tasks[session_id]['cancelled']
        return False
    
    def cancel_active_speech(self, session_id):
        """
        Cancel an active speech synthesis task.
        
        Args:
            session_id (str): Session ID of the speech to cancel
            
        Returns:
            bool: True if a task was found and marked for cancellation
        """
        with self.speech_lock:
            if session_id in self.active_speech_tasks:
                self.active_speech_tasks[session_id]['cancelled'] = True
                logger.info(f"Speech task for session {session_id} marked for cancellation")
                return True
        return False
        
    def cleanup_tasks(self):
        """
        Remove completed or old tasks from tracking.
        """
        with self.speech_lock:
            # Implementation would depend on how you track task completion
            # This is a simple placeholder
            self.active_speech_tasks = {}
            logger.info("Cleaned up speech tasks")        

# Create a singleton instance
speech_processor = SpeechProcessor()