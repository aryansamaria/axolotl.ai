import os
import json
import requests
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("investment.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class InvestmentModel:
    """Model for handling investment data and NSE API interactions"""
    
    def __init__(self):
        """Initialize the Investment Model"""
        self.cache_dir = './cache/investments'
        self.cache_expiry = 60 * 60  # 1 hour in seconds
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # NSE API configuration
        self.api_base_url = os.getenv('NSE_API_BASE_URL', 'https://www.nseindia.com/api')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_company_data(self, symbol):
        """
        Get company data either from cache or NSE API
        
        Args:
            symbol (str): The company symbol to search for
            
        Returns:
            dict: Company data
        """
        # Check if data exists in cache and is not expired
        cached_data = self._get_from_cache(symbol)
        if cached_data:
            logger.info(f"Returning cached data for {symbol}")
            return cached_data
        
        # If not in cache or expired, fetch from API
        logger.info(f"Fetching fresh data for {symbol}")
        company_data = self._fetch_from_api(symbol)
        
        # Save to cache if data was fetched successfully
        if company_data:
            self._save_to_cache(symbol, company_data)
        
        return company_data
    
    def _get_from_cache(self, symbol):
        """
        Get data from cache if available and not expired
        
        Args:
            symbol (str): Company symbol
            
        Returns:
            dict or None: Cached data if valid, None otherwise
        """
        cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is expired
            timestamp = cached.get('cached_at', 0)
            current_time = datetime.now().timestamp()
            
            if current_time - timestamp > self.cache_expiry:
                logger.info(f"Cache expired for {symbol}")
                return None
            
            return cached.get('data')
        except Exception as e:
            logger.error(f"Error reading cache for {symbol}: {e}")
            return None
    
    def _save_to_cache(self, symbol, data):
        """
        Save data to cache
        
        Args:
            symbol (str): Company symbol
            data (dict): Data to cache
        """
        cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}.json")
        
        try:
            cached_data = {
                'data': data,
                'cached_at': datetime.now().timestamp()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f, indent=2)
                
            logger.info(f"Data cached for {symbol}")
        except Exception as e:
            logger.error(f"Error caching data for {symbol}: {e}")
    
    def _fetch_from_api(self, symbol):
        """
        Fetch company data from NSE API
        
        Args:
            symbol (str): Company symbol
            
        Returns:
            dict: Company data or None if failed
        """
        try:
            # First visit NSE homepage to get cookies
            self.session.get('https://www.nseindia.com/get-quotes/equity?symbol=' + symbol, 
                            timeout=10)
            
            # Get quote data
            quote_url = f"{self.api_base_url}/quote-equity?symbol={symbol}"
            quote_resp = self.session.get(quote_url, timeout=10)
            
            if quote_resp.status_code != 200:
                logger.error(f"Failed to fetch quote data: {quote_resp.status_code}")
                return None
            
            quote_data = quote_resp.json()
            
            # Get trade info
            trade_url = f"{self.api_base_url}/quote-equity?symbol={symbol}&section=trade_info"
            trade_resp = self.session.get(trade_url, timeout=10)
            if trade_resp.status_code == 200:
                trade_data = trade_resp.json()
                quote_data['tradeInfo'] = trade_data.get('marketDeptOrderBook', {})
            
            # Get company info
            info_url = f"{self.api_base_url}/quote-equity?symbol={symbol}&section=company_info"
            info_resp = self.session.get(info_url, timeout=10)
            if info_resp.status_code == 200:
                info_data = info_resp.json()
                quote_data['companyInfo'] = info_data
            
            # Get historical data for charts (1 year)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            historical_url = (f"{self.api_base_url}/historical/securityArchives?"
                             f"symbol={symbol}&from={start_date.strftime('%d-%m-%Y')}"
                             f"&to={end_date.strftime('%d-%m-%Y')}&series=EQ")
            
            hist_resp = self.session.get(historical_url, timeout=10)
            if hist_resp.status_code == 200:
                hist_data = hist_resp.json()
                quote_data['historicalData'] = hist_data.get('data', [])
            
            return quote_data
            
        except requests.RequestException as e:
            logger.error(f"Request error fetching data for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def get_market_movers(self, category='gainers', count=5):
        """
        Get market movers (gainers, losers, most active)
        
        Args:
            category (str): Category of market movers ('gainers', 'losers', 'active')
            count (int): Number of stocks to return
            
        Returns:
            list: List of market movers
        """
        try:
            url_map = {
                'gainers': f"{self.api_base_url}/market-data-pre-open?key=NIFTY&cat=gainers",
                'losers': f"{self.api_base_url}/market-data-pre-open?key=NIFTY&cat=losers",
                'active': f"{self.api_base_url}/market-data-pre-open?key=NIFTY&cat=active"
            }
            
            if category not in url_map:
                logger.error(f"Invalid market mover category: {category}")
                return []
            
            url = url_map[category]
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch market movers: {response.status_code}")
                return []
            
            data = response.json()
            return data.get('data', [])[:count]
            
        except Exception as e:
            logger.error(f"Error fetching market movers: {e}")
            return []
    
    def search_companies(self, query):
        """
        Search for companies by name or symbol
        
        Args:
            query (str): Search query
            
        Returns:
            list: List of matching companies
        """
        try:
            url = f"{self.api_base_url}/search/autocomplete?q={query}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to search companies: {response.status_code}")
                return []
            
            data = response.json()
            return data.get('symbols', [])
            
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []

# Create singleton instance
investment_model = InvestmentModel()