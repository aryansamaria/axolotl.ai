import os
import pandas as pd
import logging
from config import Config

# Configure logging
logger = logging.getLogger(__name__)

class DataManager:
    """
    Manages data loading, preprocessing, and storage.
    """
    def __init__(self):
        """Initialize the data manager."""
        pass
    
    def load_csv_data(self, csv_path=None):
        """
        Load data from a CSV file.
        
        Args:
            csv_path (str, optional): Path to the CSV file. Defaults to Config.CSV_PATH.
            
        Returns:
            pandas.DataFrame: The loaded data
        """
        try:
            if csv_path is None:
                csv_path = Config.CSV_PATH
                
            if not os.path.exists(csv_path):
                logger.error(f"CSV file not found at {csv_path}")
                return None
            
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} rows from CSV: {csv_path}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            return None
    
    def get_categories(self):
        """
        Get all unique categories from the CSV data.
        
        Returns:
            list: List of unique categories
        """
        try:
            df = self.load_csv_data()
            if df is None:
                return []
            
            if 'category' in df.columns:
                categories = df['category'].unique().tolist()
                return categories
            else:
                logger.warning("No 'category' column found in CSV data")
                return []
                
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    def get_questions_by_category(self, category):
        """
        Get all questions for a specific category.
        
        Args:
            category (str): The category to filter by
            
        Returns:
            list: List of questions in the category
        """
        try:
            df = self.load_csv_data()
            if df is None:
                return []
            
            if 'category' in df.columns and 'question' in df.columns:
                filtered_df = df[df['category'] == category]
                questions = filtered_df['question'].tolist()
                return questions
            else:
                logger.warning("Required columns not found in CSV data")
                return []
                
        except Exception as e:
            logger.error(f"Error getting questions by category: {e}")
            return []
    
    def export_data(self, data, output_path, format='csv'):
        """
        Export data to a file.
        
        Args:
            data (pandas.DataFrame): The data to export
            output_path (str): Path to save the exported file
            format (str, optional): Export format ('csv' or 'json'). Defaults to 'csv'.
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if isinstance(data, pd.DataFrame):
                if format.lower() == 'csv':
                    data.to_csv(output_path, index=False)
                elif format.lower() == 'json':
                    data.to_json(output_path, orient='records')
                else:
                    logger.error(f"Unsupported export format: {format}")
                    return False
                
                logger.info(f"Data exported to {output_path}")
                return True
            else:
                logger.error("Export data must be a pandas DataFrame")
                return False
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False

# Create a singleton instance
data_manager = DataManager()