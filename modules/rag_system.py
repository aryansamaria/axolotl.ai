import os
import logging
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.schema import Document
from llama_index.core.node_parser import SimpleFileNodeParser
from llama_index.llms.openai import OpenAI
import pandas as pd
from config import Config
import time
import random
from llama_index.core import load_index_from_storage, StorageContext

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
        
        # Check if the index already exists
            index_path = os.path.join(Config.STORAGE_DIR, "index")
            if os.path.exists(index_path) and os.listdir(index_path):
                logger.info(f"Loading existing index from {index_path}")
            
            # Load the existing index
                storage_context = StorageContext.from_defaults(
                    persist_dir=index_path
                )
            
                index = load_index_from_storage(
                    storage_context=storage_context
                )
                logger.info("Successfully loaded existing index")
            else:
            # Create a fresh index from CSV data
                logger.info("Creating new index from CSV data...")
            
            # Check if CSV file exists
                if not os.path.exists(Config.CSV_PATH):
                    logger.error(f"CSV file not found at {Config.CSV_PATH}")
                    raise FileNotFoundError(f"CSV file not found at {Config.CSV_PATH}")
            
            # Load CSV data into a DataFrame
                df = pd.read_csv(Config.CSV_PATH)
                logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Create documents from DataFrame rows in batches
                batch_size = 10  # Process 10 documents at a time
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
                
                # Process in batches with rate limiting
                    if len(documents) % batch_size == 0:
                        logger.info(f"Processed {len(documents)} documents so far")
                    # Add a short delay to respect rate limits
                        time.sleep(2)  # 2 second pause between batches
            
                logger.info(f"Created {len(documents)} documents")
            
            # Use exponential backoff for creating the index
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                    # Create a new index from documents
                        index = VectorStoreIndex.from_documents(documents)
                    
                    # Save the index
                        if not os.path.exists(Config.STORAGE_DIR):
                            os.makedirs(Config.STORAGE_DIR)
                    
                        index.storage_context.persist(persist_dir=index_path)
                        logger.info(f"Saved index to {index_path}")
                        break  # Success, exit the retry loop
                    except Exception as e:
                        if "429" in str(e) and attempt < max_retries - 1:
                        # Calculate wait time with exponential backoff
                            wait_time = (2 ** attempt) + (random.random() * 2)
                            logger.warning(f"Rate limited, waiting {wait_time:.2f} seconds (attempt {attempt+1}/{max_retries})...")
                            time.sleep(wait_time)
                        else:
                        # Re-raise on final attempt
                            logger.error(f"Failed to create index after {max_retries} attempts")
                            raise
        
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
