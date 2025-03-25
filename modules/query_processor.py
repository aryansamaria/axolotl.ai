import logging
import openai
from config import Config
from modules.rag_system import rag_system

# Configure logging
logger = logging.getLogger(__name__)

class QueryProcessor:
    """
    Processes user queries by querying the RAG system and falling back to 
    OpenAI if needed.
    """
    def __init__(self):
        """Initialize the query processor."""
        # Set OpenAI API key
        openai.api_key = Config.OPENAI_API_KEY
    
    def process_query(self, query_text):
        """
        Process a user query and generate a response.
        
        Args:
            query_text (str): The user's query text
            
        Returns:
            str: The response to the query
        """
        try:
            logger.info(f"Processing query: {query_text}")
            
            # Query the RAG system
            rag_response = rag_system.query(query_text)
            
            # Check if the RAG system provided a meaningful response
            if not rag_response or rag_response.strip() == "" or "I don't know" in rag_response.lower():
                logger.info("No specific information found in knowledge base. Using OpenAI...")
                response = self.fallback_to_openai(query_text)
            else:
                response = rag_response
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "I'm sorry, I encountered an error while processing your question."
    
    def fallback_to_openai(self, query_text):
        """
        Fallback to OpenAI if RAG doesn't have an answer.
        
        Args:
            query_text (str): The user's query text
            
        Returns:
            str: The response from OpenAI
        """
        try:
            logger.info(f"Falling back to OpenAI for query: {query_text}")
            
            # Try newer OpenAI client format (v1.0.0+)
            try:
                client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=Config.FALLBACK_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions about Wise money transfers."},
                        {"role": "user", "content": query_text}
                    ]
                )
                return response.choices[0].message.content
            except AttributeError:
                # Fall back to older format (pre-v1.0.0)
                response = openai.ChatCompletion.create(
                    model=Config.FALLBACK_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions about Wise money transfers."},
                        {"role": "user", "content": query_text}
                    ]
                )
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return "I'm sorry, I'm having trouble connecting to my knowledge base."

# Create a singleton instance
query_processor = QueryProcessor()