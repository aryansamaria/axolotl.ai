import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import re
import logging
from urllib.parse import urljoin
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

class WiseHelpScraper:
    def __init__(self, base_url, max_workers=5):
        """
        Initialize the scraper with the base URL.
        
        Args:
            base_url (str): The base URL of the Wise help center
            max_workers (int): Maximum number of concurrent threads for scraping
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        self.results = []
        self.max_workers = max_workers
        self.processed_urls = set()  # To avoid processing the same URL twice
        self.checkpoint_file = "scraper_checkpoint.json"

    def fetch_page(self, url):
        """
        Fetch a page with error handling and retries.
        
        Args:
            url (str): URL to fetch
            
        Returns:
            str or None: The HTML content of the page, or None if failed
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logging.info(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                logging.warning(f"Error fetching {url}: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        logging.error(f"Failed to fetch {url} after {max_retries} attempts")
        return None

    def load_checkpoint(self):
        """
        Load checkpoint data if it exists to resume scraping.
        
        Returns:
            bool: True if checkpoint was loaded, False otherwise
        """
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                    self.results = checkpoint_data.get('results', [])
                    self.processed_urls = set(checkpoint_data.get('processed_urls', []))
                    logging.info(f"Loaded checkpoint with {len(self.results)} results and {len(self.processed_urls)} processed URLs")
                    return True
            except Exception as e:
                logging.error(f"Error loading checkpoint: {e}")
        return False

    def save_checkpoint(self):
        """Save checkpoint data to resume scraping later."""
        try:
            checkpoint_data = {
                'results': self.results,
                'processed_urls': list(self.processed_urls)
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Saved checkpoint with {len(self.results)} results")
        except Exception as e:
            logging.error(f"Error saving checkpoint: {e}")

    def parse_main_page(self, url):
        """
        Parse the main help page to extract categories and questions.
        
        Args:
            url (str): URL of the main help page
        """
        html_content = self.fetch_page(url)
        if not html_content:
            return
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all accordion buttons (categories)
        categories = soup.find_all('button', {'data-testid': re.compile(r'^accordion-button-')})
        
        # Create a list to store all question URLs for parallel processing
        question_data = []
        
        for category in categories:
            category_name = category.find('h2').text.strip()
            logging.info(f"Found category: {category_name}")
            
            # Get the category ID to find its content
            category_id = category.get('data-testid').replace('accordion-button-', '')
            
            # Find the accordion content for this category
            content_div = soup.find('div', {'data-testid': f'accordion-content-{category_id}'})
            
            # If the category is collapsed, the content might be 'inert'
            # We still try to process it
            if content_div:
                # Find all question links in this category
                question_links = content_div.find_all('a', {'class': re.compile(r'np-link')})
                
                for question_link in question_links:
                    question_text = question_link.text.strip()
                    question_url = urljoin(self.base_url, question_link['href'])
                    
                    # Only add if we haven't processed this URL before
                    if question_url not in self.processed_urls:
                        question_data.append({
                            'category': category_name,
                            'question': question_text,
                            'url': question_url
                        })
            else:
                logging.warning(f"Could not find content for category: {category_name}")
        
        logging.info(f"Found {len(question_data)} new questions to process")
        
        # Process questions in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all question processing tasks
            future_to_question = {
                executor.submit(self.process_question_page, item['category'], item['question'], item['url']): item
                for item in question_data
            }
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_question)):
                try:
                    future.result()  # Get the result (or exception)
                except Exception as e:
                    question = future_to_question[future]
                    logging.error(f"Error processing {question['url']}: {e}")
                
                # Save checkpoint periodically (every 10 questions)
                if i > 0 and i % 10 == 0:
                    self.save_checkpoint()
                    logging.info(f"Processed {i}/{len(question_data)} questions")
        
        # Final checkpoint save
        self.save_checkpoint()

    def process_question_page(self, category, question, url):
        """
        Process a question page to extract the answer.
        
        Args:
            category (str): The category name
            question (str): The question text
            url (str): The URL of the question page
        """
        # Skip if already processed
        if url in self.processed_urls:
            return
        
        html_content = self.fetch_page(url)
        if not html_content:
            return
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the answer content
        answer_content = None
        
        # Try different selectors to find the answer content
        # The article content is usually in a div with a class containing 'article-content'
        content_div = soup.find('div', {'class': re.compile(r'article-content')})
        if content_div:
            answer_content = content_div
        else:
            # Try alternative selectors
            content_div = soup.find('div', {'class': re.compile(r'col-lg-8|col-lg-10')})
            if content_div:
                # Try to find the main content excluding headers, navigation, etc.
                main_content = content_div.find('div', {'class': re.compile(r'row')})
                
                if main_content:
                    # Exclude header and other non-content elements
                    for element in main_content.find_all(['h1', 'nav', 'div'], {'class': re.compile(r'breadcrumbs|header')}):
                        element.decompose()
                    answer_content = main_content
                else:
                    answer_content = content_div
        
        if answer_content:
            # Clean up the answer text
            answer_text = self._clean_text(answer_content.get_text())
            
            # Store the result
            result = {
                'category': category,
                'question': question,
                'answer': answer_text,
                'url': url
            }
            
            self.results.append(result)
            self.processed_urls.add(url)
            
            logging.info(f"Processed question: {question}")
        else:
            logging.warning(f"Could not find answer content for question: {question}")
            # Mark as processed even if we couldn't find the answer
            self.processed_urls.add(url)

    def _clean_text(self, text):
        """
        Clean up extracted text by removing extra whitespace.
        
        Args:
            text (str): Raw text to clean
            
        Returns:
            str: Cleaned text
        """
        # Replace multiple whitespace with a single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def save_to_csv(self, filename):
        """
        Save the scraped data to a CSV file.
        
        Args:
            filename (str): Output CSV file name
        """
        logging.info(f"Saving {len(self.results)} results to {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['category', 'question', 'answer', 'url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow(result)
        
        logging.info(f"Data saved to {filename}")

def main():
    """Main function to run the scraper."""
    # Base URL for the Wise help center
    base_url = "https://wise.com"
    help_url = "https://wise.com/help/topics/5bVKT0uQdBrDp6T62keyfz/sending-money"
    
    # Initialize the scraper
    scraper = WiseHelpScraper(base_url)
    
    try:
        # Try to load checkpoint data
        scraper.load_checkpoint()
        
        # Parse the main page to extract categories and questions
        scraper.parse_main_page(help_url)
        
        # Save the results to a CSV file
        scraper.save_to_csv("wise_help_content.csv")
        
        logging.info("Scraping completed successfully")
    except KeyboardInterrupt:
        logging.info("Scraping interrupted by user")
        # Save checkpoint on keyboard interrupt
        scraper.save_checkpoint()
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        # Save checkpoint on error
        scraper.save_checkpoint()

if __name__ == "__main__":
    main()