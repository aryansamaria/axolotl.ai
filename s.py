import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import logging
import argparse
import os
from urllib.parse import urljoin, urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("faq_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GeneralFaqScraper:
    """A flexible scraper to extract FAQ content from arbitrary websites."""
    
    def __init__(self, base_url, output_file="faqs.csv"):
        """
        Initialize the scraper.
        
        Args:
            base_url (str): The base URL of the page containing FAQs
            output_file (str): Path to save the output CSV file
        """
        self.base_url = base_url
        self.output_file = output_file
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        self.results = []
        self.domain = urlparse(base_url).netloc
        
    def fetch_page(self, url=None):
        """
        Fetch the page content with error handling and retries.
        
        Args:
            url (str, optional): URL to fetch, defaults to base_url if not provided
            
        Returns:
            BeautifulSoup object or None if failed
        """
        if url is None:
            url = self.base_url
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Fetching URL: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Create BeautifulSoup object
                return BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.RequestException as e:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"Error fetching {url}: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
        logger.error(f"Failed to fetch {url} after {max_retries} attempts")
        return None
        
    def extract_faqs(self):
        """
        Extract FAQ content using multiple strategies.
        
        Returns:
            int: Number of FAQs extracted
        """
        soup = self.fetch_page()
        if not soup:
            return 0
        
        logger.info("Analyzing page structure to find FAQs...")
        
        # Apply multiple extraction strategies in order of specificity
        extracted = self._extract_structured_faqs(soup)
        
        if not extracted:
            extracted = self._extract_faq_from_accordion(soup)
            
        if not extracted:
            extracted = self._extract_definition_list_faqs(soup)
            
        if not extracted:
            extracted = self._extract_heading_paragraph_faqs(soup)
            
        if not extracted:
            extracted = self._extract_question_like_content(soup)
        
        logger.info(f"Extracted {len(self.results)} FAQs in total")
        return len(self.results)
    
    def _extract_structured_faqs(self, soup):
        """Extract FAQs from structured FAQ sections."""
        # Look for common FAQ section identifiers
        faq_containers = []
        
        # Method 1: Look for elements with FAQ-related classes or IDs
        for container in soup.find_all(['div', 'section', 'article']):
            container_id = container.get('id', '').lower()
            container_class = ' '.join(container.get('class', [])).lower()
            
            if any(term in container_id or term in container_class 
                  for term in ['faq', 'faqs', 'frequently-asked', 'questions-answers', 'q-and-a']):
                faq_containers.append(container)
                
        # Method 2: Look for FAQ headings
        if not faq_containers:
            for heading in soup.find_all(['h1', 'h2', 'h3']):
                text = heading.get_text().lower()
                if any(term in text for term in ['faq', 'frequently asked questions', 'questions & answers']):
                    # Find the parent container
                    parent = heading.find_parent(['div', 'section', 'article'])
                    if parent:
                        faq_containers.append(parent)
        
        if not faq_containers:
            return False
            
        extracted = False
        
        for container in faq_containers:
            # Strategy 1: Look for question/answer pairs with distinct classes
            q_elements = container.find_all(class_=re.compile(r'question|faq-q|accordion-header|toggle-header'))
            a_elements = container.find_all(class_=re.compile(r'answer|faq-a|accordion-content|toggle-content'))
            
            if len(q_elements) > 0 and len(q_elements) == len(a_elements):
                # Matching pairs found
                for q, a in zip(q_elements, a_elements):
                    self._add_faq(q.get_text(), a.get_text(), 'structured-class-pairs')
                extracted = True
                
            # Strategy 2: Look for question/answer elements that follow each other
            if not extracted:
                q_tags = container.find_all(['h3', 'h4', 'strong', 'p', 'div', 'button'], 
                                            class_=re.compile(r'question|faq-q|q-text'))
                
                for q_tag in q_tags:
                    # Find the next sibling or cousin that could be an answer
                    a_tag = q_tag.find_next(['p', 'div'])
                    if a_tag and not self._is_question(a_tag.get_text()):
                        self._add_faq(q_tag.get_text(), a_tag.get_text(), 'structured-siblings')
                        extracted = True
        
        return extracted
    
    def _extract_faq_from_accordion(self, soup):
        """Extract FAQs from accordion-style elements."""
        # Common accordion patterns
        accordion_patterns = [
            # Bootstrap accordions
            {'items': soup.find_all('div', class_=re.compile(r'accordion-item'))},
            # jQuery UI accordions
            {'headers': soup.find_all('h3', class_=re.compile(r'ui-accordion-header')),
             'contents': soup.find_all('div', class_=re.compile(r'ui-accordion-content'))},
            # Generic accordions
            {'buttons': soup.find_all('button', {'aria-expanded': re.compile(r'true|false')})}
        ]
        
        extracted = False
        
        # Process Bootstrap-like accordions
        for pattern in accordion_patterns:
            if 'items' in pattern and pattern['items']:
                for item in pattern['items']:
                    header = item.find(['button', 'h2', 'h3', 'h4', 'div'], 
                                      class_=re.compile(r'accordion-header|accordion-button'))
                    content = item.find(['div'], class_=re.compile(r'accordion-body|accordion-content|collapse'))
                    
                    if header and content:
                        self._add_faq(header.get_text(), content.get_text(), 'accordion-item')
                        extracted = True
            
            # Process header/content pairs
            elif 'headers' in pattern and 'contents' in pattern and len(pattern['headers']) == len(pattern['contents']):
                for header, content in zip(pattern['headers'], pattern['contents']):
                    self._add_faq(header.get_text(), content.get_text(), 'accordion-pair')
                    extracted = True
            
            # Process buttons that control expandable content
            elif 'buttons' in pattern and pattern['buttons']:
                for button in pattern['buttons']:
                    # Find controlled element
                    control_id = button.get('aria-controls')
                    if control_id:
                        content = soup.find(id=control_id)
                        if content:
                            self._add_faq(button.get_text(), content.get_text(), 'accordion-control')
                            extracted = True
        
        # Look for details/summary elements (HTML5 native accordions)
        details_elements = soup.find_all('details')
        if details_elements:
            for details in details_elements:
                summary = details.find('summary')
                if summary:
                    # Get the summary text
                    question = summary.get_text()
                    
                    # Copy the details element and remove the summary to get just the content
                    details_copy = details
                    summary_copy = details_copy.find('summary')
                    if summary_copy:
                        summary_copy.extract()
                    
                    answer = details_copy.get_text()
                    self._add_faq(question, answer, 'details-summary')
                    extracted = True
        
        return extracted
    
    def _extract_definition_list_faqs(self, soup):
        """Extract FAQs from definition lists (dt/dd)."""
        dl_elements = soup.find_all('dl')
        if not dl_elements:
            return False
            
        extracted = False
        
        for dl in dl_elements:
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            if len(dt_elements) > 0 and len(dt_elements) == len(dd_elements):
                for dt, dd in zip(dt_elements, dd_elements):
                    self._add_faq(dt.get_text(), dd.get_text(), 'definition-list')
                    extracted = True
        
        return extracted
    
    def _extract_heading_paragraph_faqs(self, soup):
        """Extract FAQs from heading followed by paragraph pattern."""
        # Find all headings h2-h5 that might be questions
        headings = soup.find_all(['h2', 'h3', 'h4', 'h5'])
        
        if not headings:
            return False
            
        extracted = False
        
        for heading in headings:
            heading_text = heading.get_text().strip()
            
            # Check if heading looks like a question
            if self._is_question(heading_text):
                # Find the next paragraph or div
                answer_elem = heading.find_next(['p', 'div'])
                
                if answer_elem and not self._is_heading(answer_elem.name):
                    answer_text = answer_elem.get_text().strip()
                    
                    # Make sure the answer doesn't look like another question
                    if not self._is_question(answer_text) and len(answer_text) > 10:
                        self._add_faq(heading_text, answer_text, 'heading-paragraph')
                        extracted = True
        
        return extracted
    
    def _extract_question_like_content(self, soup):
        """Extract content that looks like questions and answers based on text patterns."""
        # Find elements with text ending in question marks
        potential_questions = []
        
        for elem in soup.find_all(['p', 'div', 'span', 'strong', 'b']):
            text = elem.get_text().strip()
            if text.endswith('?') or self._is_question(text):
                potential_questions.append(elem)
        
        if not potential_questions:
            return False
            
        extracted = False
        
        for q_elem in potential_questions:
            q_text = q_elem.get_text().strip()
            
            # Find the next element as a potential answer
            a_elem = q_elem.find_next(['p', 'div', 'span'])
            
            if a_elem and not self._is_question(a_elem.get_text()):
                a_text = a_elem.get_text().strip()
                
                if len(a_text) > 15:  # Ensure answer has meaningful content
                    self._add_faq(q_text, a_text, 'text-pattern')
                    extracted = True
        
        return extracted
    
    def _is_question(self, text):
        """
        Check if text looks like a question.
        
        Args:
            text (str): Text to check
            
        Returns:
            bool: True if the text looks like a question
        """
        text = text.strip().lower()
        
        # Obvious signs: ends with question mark or starts with question words
        if text.endswith('?'):
            return True
            
        question_starters = ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'can', 'do', 'does', 'will', 'is', 'are']
        words = text.split()
        
        if words and words[0] in question_starters:
            return True
            
        # Check for phrases like "How to..." or "Learn about..."
        question_phrases = ['how to', 'ways to', 'tips for', 'guide to']
        return any(phrase in text for phrase in question_phrases)
    
    def _is_heading(self, tag_name):
        """Check if tag is a heading."""
        return tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    def _add_faq(self, question, answer, source_type):
        """
        Add a FAQ to results after cleaning.
        
        Args:
            question (str): The question text
            answer (str): The answer text
            source_type (str): Type of source this FAQ was extracted from
        """
        # Clean and normalize text
        question = self._clean_text(question)
        answer = self._clean_text(answer)
        
        # Validate FAQ content
        if len(question) < 5 or len(answer) < 10:
            return
            
        # Add to results
        self.results.append({
            'question': question,
            'answer': answer,
            'url': self.base_url,
            'source_type': source_type
        })
        
        logger.debug(f"Added FAQ: {question[:30]}... [{source_type}]")
    
    def _clean_text(self, text):
        """
        Clean up the extracted text.
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text
        """
        # Replace multiple whitespace with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might appear in HTML
        text = re.sub(r'[\r\n\t]+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def save_to_csv(self):
        """Save the extracted FAQs to a CSV file."""
        if not self.results:
            logger.warning("No results to save")
            return False
            
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['question', 'answer', 'url', 'source_type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in self.results:
                    writer.writerow(result)
                    
            logger.info(f"Saved {len(self.results)} FAQs to {self.output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            return False
    
    def scrape(self):
        """
        Perform the complete scraping process.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract FAQs
            count = self.extract_faqs()
            
            if count == 0:
                logger.warning(f"No FAQs found on {self.base_url}")
                return False
                
            # Save to CSV
            return self.save_to_csv()
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return False

def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(description='General FAQ Scraper')
    parser.add_argument('url', help='The URL of the page containing FAQs')
    parser.add_argument('--output', '-o', default='faqs.csv', help='Output CSV file (default: faqs.csv)')
    
    args = parser.parse_args()
    
    scraper = GeneralFaqScraper(args.url, args.output)
    success = scraper.scrape()
    
    if success:
        print(f"Successfully extracted {len(scraper.results)} FAQs from {args.url}")
        print(f"Results saved to {args.output}")
    else:
        print(f"Failed to extract FAQs from {args.url}")

if __name__ == "__main__":
    main()