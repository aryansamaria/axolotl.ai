import os
import logging
from flask import Flask, render_template, request, jsonify
from config import Config
from modules import initialize_modules
from modules.speech_processor import speech_processor
from modules.query_processor import query_processor
from modules.data_manager import data_manager
from utils.helpers import save_conversation, format_error_response, sanitize_input, get_timestamp
import uuid
from flask import session


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

Config.setup_directories()

with app.app_context():
    initialize_modules()

app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assistant')
def assistant():
    return render_template('assistant.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Transcribe audio to text using speech recognition.
    Expects a base64-encoded audio file.
    """
    try:
        # Get audio data from request
        audio_data = request.json.get('audio')
        if not audio_data:
            return jsonify(format_error_response("No audio data received")), 400
        
        # Transcribe audio
        transcription_text = speech_processor.transcribe_audio_data(audio_data)
        
        if not transcription_text:
            return jsonify(format_error_response("Failed to transcribe audio")), 500
        
        return jsonify({
            "success": True,
            "text": transcription_text
        })
    
    except Exception as e:
        logger.error(f"Error in transcription: {str(e)}")
        return jsonify(format_error_response(str(e))), 500

@app.route('/cancel_response', methods=['POST'])
def cancel_response():
    """
    Cancel any ongoing response generation or speech synthesis.
    """
    try:
        logger.info("Response cancelled by user")
        
        # Get session ID for the current user
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Cancel any active query
        speech_processor.cancel_active_speech(session_id)
        
        return jsonify({
            "success": True,
            "message": "Response cancellation processed"
        })
    
    except Exception as e:
        logger.error(f"Error canceling response: {str(e)}")
        return jsonify(format_error_response(str(e))), 500     


@app.route('/process_query', methods=['POST'])
def process_query():
    """
    Process a text query and generate a response with audio.
    Updated to support interruption and session tracking.
    """
    try:
        # Get query text from request
        query = request.json.get('query')
        if not query:
            return jsonify(format_error_response("No query received")), 400
        
        # Get or create a session ID
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        sanitized_query = sanitize_input(query)
        
        # Process the query
        response = query_processor.process_query(sanitized_query)
        
        # Generate speech with session ID for tracking
        audio_data = speech_processor.text_to_speech_data(response, session_id)
        
        # Save conversation
        save_conversation(sanitized_query, response)
        
        return jsonify({
            "success": True,
            "text": response,
            "audio_data": audio_data,
            "session_id": session_id
        })
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify(format_error_response(str(e))), 500


@app.route('/categories', methods=['GET'])
def get_categories():
    """Get all available categories."""
    try:
        categories = data_manager.get_categories()
        return jsonify({
            "success": True,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify(format_error_response(str(e))), 500

@app.route('/questions/<category>', methods=['GET'])
def get_questions(category):
    """Get questions for a specific category."""
    try:
        questions = data_manager.get_questions_by_category(category)
        return jsonify({
            "success": True,
            "category": category,
            "questions": questions
        })
    except Exception as e:
        logger.error(f"Error getting questions: {str(e)}")
        return jsonify(format_error_response(str(e))), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": get_timestamp()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify(format_error_response("Resource not found")), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify(format_error_response("Internal server error")), 500

# Enable CORS if needed
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to enable cross-origin requests."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

if __name__ == '__main__':
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )