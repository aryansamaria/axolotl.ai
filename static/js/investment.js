// Investment Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const companySearchInput = document.getElementById('company-search');
    const searchForm = document.getElementById('search-form');
    const searchResults = document.getElementById('search-results');
    const moversBody = document.getElementById('movers-body');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const recentCompanies = document.getElementById('recent-companies');
    
    // Market data elements
    const niftyValue = document.getElementById('nifty-value');
    const niftyChange = document.getElementById('nifty-change');
    const sensexValue = document.getElementById('sensex-value');
    const sensexChange = document.getElementById('sensex-change');
    const marketCap = document.getElementById('market-cap');
    
    // Variables
    let currentCategory = 'gainers';
    let searchTimeout = null;
    
    // Initialize
    init();
    
    // ------ Functions ------
    
    /**
     * Initialize the page
     */
    function init() {
        // Load market movers for default category
        loadMarketMovers(currentCategory);
        
        // Load market data
        loadMarketData();
        
        // Load recent searches
        loadRecentSearches();
        
        // Set up event listeners
        setupEventListeners();
    }
    
    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Search input
        companySearchInput.addEventListener('input', handleSearchInput);
        
        // Search form submission
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (companySearchInput.value.trim()) {
                const firstResult = searchResults.querySelector('.search-result-item');
                if (firstResult) {
                    firstResult.click();
                }
            }
        });
        
        // Tab buttons for market movers
        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                const category = this.dataset.category;
                
                // Update active tab
                tabButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Load market movers for the selected category
                currentCategory = category;
                loadMarketMovers(category);
            });
        });
        
        // Close search results when clicking elsewhere
        document.addEventListener('click', function(e) {
            if (!searchResults.contains(e.target) && e.target !== companySearchInput) {
                searchResults.classList.remove('active');
            }
        });
    }
    
    /**
     * Handle search input
     */
    function handleSearchInput() {
        const query = companySearchInput.value.trim();
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        if (query.length < 2) {
            searchResults.classList.remove('active');
            return;
        }
        
        // Set timeout to avoid making too many requests
        searchTimeout = setTimeout(() => {
            searchCompanies(query);
        }, 300);
    }
    
    /**
     * Search for companies
     * @param {string} query - Search query
     */
    function searchCompanies(query) {
        fetch(`/invest/api/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.results.length > 0) {
                    displaySearchResults(data.results);
                } else {
                    searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
                    searchResults.classList.add('active');
                }
            })
            .catch(error => {
                console.error('Error searching companies:', error);
                searchResults.innerHTML = '<div class="search-result-item">Error searching companies</div>';
                searchResults.classList.add('active');
            });
    }
    
    /**
     * Display search results
     * @param {Array} results - Search results
     */
    function displaySearchResults(results) {
        searchResults.innerHTML = '';
        
        results.forEach(result => {
            const resultItem = document.createElement('div');
            resultItem.className = 'search-result-item';
            resultItem.innerHTML = `
                <div class="symbol">${result.symbol}</div>
                <div class="company-name">${result.name}</div>
            `;
            
            // Add click event
            resultItem.addEventListener('click', function() {
                // Navigate to company details page
                window.location.href = `/invest/company/${result.symbol}`;
                
                // Add to recent searches
                addToRecentSearches({
                    symbol: result.symbol,
                    name: result.name
                });
            });
            
            searchResults.appendChild(resultItem);
        });
        
        searchResults.classList.add('active');
    }
    
    /**
     * Load market movers
     * @param {string} category - Category of market movers
     */
    function loadMarketMovers(category) {
        moversBody.innerHTML = '<tr><td colspan="5" class="text-center">Loading data...</td></tr>';
        
        fetch(`/invest/api/market-movers?category=${category}&count=10`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data.length > 0) {
                    displayMarketMovers(data.data);
                } else {
                    moversBody.innerHTML = '<tr><td colspan="5" class="text-center">No data available</td></tr>';
                }
            })
            .catch(error => {
                console.error('Error loading market movers:', error);
                moversBody.innerHTML = '<tr><td colspan="5" class="text-center">Error loading data</td></tr>';
            });
    }
    
    /**
     * Display market movers
     * @param {Array} movers - Market movers data
     */
    function displayMarketMovers(movers) {
        moversBody.innerHTML = '';
        
        movers.forEach(mover => {
            const row = document.createElement('tr');
            const changeClass = mover.change >= 0 ? 'positive-change' : 'negative-change';
            const changePrefix = mover.change >= 0 ? '+' : '';
            
            row.innerHTML = `
                <td>${mover.symbol}</td>
                <td>${mover.name}</td>
                <td>₹${formatNumber(mover.lastPrice)}</td>
                <td class="${changeClass}">${changePrefix}${mover.change.toFixed(2)}%</td>
                <td><a href="/invest/company/${mover.symbol}" class="view-btn">View</a></td>
            `;
            
            moversBody.appendChild(row);
        });
    }
    
    /**
     * Load market data
     */
    function loadMarketData() {
        // In a real implementation, this would fetch from an API
        // For demo purposes, using static data
        
        // Fetch Nifty data
        niftyValue.textContent = '20,138.15';
        niftyChange.textContent = '+0.24% ↑';
        niftyChange.classList.add('positive');
        
        // Fetch Sensex data
        sensexValue.textContent = '65,982.48';
        sensexChange.textContent = '-0.12% ↓';
        sensexChange.classList.add('negative');
        
        // Fetch Market Cap data
        marketCap.textContent = '₹349.2 Lakh Cr';
    }
    
    /**
     * Add company to recent searches
     * @param {Object} company - Company data
     */
    function addToRecentSearches(company) {
        let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        
        // Check if company already exists in recent searches
        const existingIndex = recentSearches.findIndex(item => item.symbol === company.symbol);
        
        if (existingIndex !== -1) {
            // Remove existing entry
            recentSearches.splice(existingIndex, 1);
        }
        
        // Add to the beginning of the array
        recentSearches.unshift({
            symbol: company.symbol,
            name: company.name,
            timestamp: Date.now()
        });
        
        // Limit to 10 recent searches
        recentSearches = recentSearches.slice(0, 10);
        
        // Save to localStorage
        localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
        
        // Reload recent searches
        loadRecentSearches();
    }
    
    /**
     * Load recent searches
     */
    function loadRecentSearches() {
        const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        
        if (recentSearches.length === 0) {
            recentCompanies.innerHTML = '<div class="empty-state">No recent searches</div>';
            return;
        }
        
        recentCompanies.innerHTML = '';
        
        recentSearches.forEach(company => {
            const companyTile = document.createElement('div');
            companyTile.className = 'company-tile';
            companyTile.innerHTML = `
                <div class="symbol">${company.symbol}</div>
                <div class="company-name">${company.name}</div>
            `;
            
            // Add click event
            companyTile.addEventListener('click', function() {
                window.location.href = `/invest/company/${company.symbol}`;
            });
            
            recentCompanies.appendChild(companyTile);
        });
    }
    
    /**
     * Format number with commas
     * @param {number} num - Number to format
     * @returns {string} Formatted number
     */
    function formatNumber(num) {
        return new Intl.NumberFormat('en-IN').format(num);
    }
});