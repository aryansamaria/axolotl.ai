import os
import logging
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.schema import Document
from llama_index.core.node_parser import SimpleFileNodeParser
from llama_index.llms.openai import OpenAI
import pandas as pd
from config import Config

# Configure logging
logger = logging.getLogger(__name__)

class RAGSystem:
    """
    Retrieval Augmented Generation (RAG) system for answering queries
    using a vector store index.
    """
    def __init__(self):
        """Initialize the RAG system."""
        self.query_engine = None
        
    def setup(self):
        """Set up the RAG system by loading or creating the vector index."""
        try:
            # Configure the global settings
            Settings.llm = OpenAI(api_key=Config.OPENAI_API_KEY)
            Settings.node_parser = SimpleFileNodeParser()
            
            # Create a fresh index from CSV data
            logger.info("Creating index from CSV data...")
            
            # Check if CSV file exists
            if not os.path.exists(Config.CSV_PATH):
                logger.error(f"CSV file not found at {Config.CSV_PATH}")
                raise FileNotFoundError(f"CSV file not found at {Config.CSV_PATH}")
            
            # Load CSV data into a DataFrame
            df = pd.read_csv(Config.CSV_PATH)
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Create documents from DataFrame rows
            documents = []
            for index, row in df.iterrows():
                try:
                    doc = Document(
                        text=row['answer'],
                        metadata={
                            'question': row['question'], 
                            'category': row.get('category', ''), 
                            'url': row.get('url', '')
                        }
                    )
                    documents.append(doc)
                except Exception as e:
                    logger.warning(f"Error creating document for row {index}: {e}")
            
            logger.info(f"Created {len(documents)} documents")
            
            # Create a new index from documents
            index = VectorStoreIndex.from_documents(documents)
            
            # Save the index
            if not os.path.exists(Config.STORAGE_DIR):
                os.makedirs(Config.STORAGE_DIR)
            
            index.storage_context.persist(persist_dir=Config.STORAGE_DIR)
            logger.info(f"Saved index to {Config.STORAGE_DIR}")
            
            # Initialize the query engine
            self.query_engine = index.as_query_engine()
            
            return True
        
        except Exception as e:
            logger.error(f"Error setting up RAG system: {e}")
            raise
    
    def query(self, user_query):
        """
        Send a query to the RAG system and get a response.
        
        Args:
            user_query (str): The user's query text
            
        Returns:
            str: The response from the RAG system
        """
        try:
            if not self.query_engine:
                logger.warning("Query engine not initialized. Setting up RAG system...")
                self.setup()
                
            # Get response from RAG system
            response = self.query_engine.query(user_query)
            return response.response
        except Exception as e:
            logger.error(f"Error querying RAG system: {e}")
            return None
            
# Create a singleton instance
rag_system = RAGSystem()