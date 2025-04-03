// Company Details Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const loadingOverlay = document.getElementById('loading-overlay');
    const companyNameBreadcrumb = document.getElementById('company-name-breadcrumb');
    const companyName = document.getElementById('company-name');
    const companyCode = document.getElementById('company-code');
    const currentPrice = document.getElementById('current-price');
    const priceChange = document.getElementById('price-change');
    const priceChart = document.getElementById('price-chart');
    const chartPeriodBtns = document.querySelectorAll('.chart-period-btn');
    const orderBookTabs = document.querySelectorAll('.order-book-tab');
    const orderBookBody = document.getElementById('order-book-body');
    const announcementsList = document.getElementById('announcements-list');
    
    // Trading info elements
    const openPrice = document.getElementById('open-price');
    const highPrice = document.getElementById('high-price');
    const lowPrice = document.getElementById('low-price');
    const closePrice = document.getElementById('close-price');
    const volume = document.getElementById('volume');
    const weekHigh = document.getElementById('52w-high');
    const weekLow = document.getElementById('52w-low');
    const marketCapElem = document.getElementById('market-cap');
    
    // Company info elements
    const industry = document.getElementById('industry');
    const indexElem = document.getElementById('index');
    const faceValue = document.getElementById('face-value');
    const listingDate = document.getElementById('listing-date');
    const peRatio = document.getElementById('pe-ratio');
    const eps = document.getElementById('eps');
    const dividendYield = document.getElementById('dividend-yield');
    const bookValue = document.getElementById('book-value');
    
    // Variables
    let companyData = null;
    let chart = null;
    let currentPeriod = '1Y';
    let currentOrderBookTab = 'buy';
    
    // Initialize
    loadCompanyData();
    
    // ------ Functions ------
    
    /**
     * Load company data
     */
    function loadCompanyData() {
        fetch(`/invest/api/company/${COMPANY_SYMBOL}`)
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    companyData = result.data;
                    renderCompanyData();
                    initializeChartData();
                    loadOrderBook('buy');
                    loadAnnouncements();
                    loadingOverlay.style.display = 'none';
                } else {
                    alert('Error loading company data: ' + result.message);
                }
            })
            .catch(error => {
                console.error('Error loading company data:', error);
                alert('Error loading company data. Please try again later.');
            });
    }
    
    /**
     * Render company data
     */
    function renderCompanyData() {
        // Basic company info
        const info = companyData.info || {};
        const metadata = companyData.metadata || {};
        const priceInfo = companyData.priceInfo || {};
        
        companyNameBreadcrumb.textContent = info.companyName || COMPANY_SYMBOL;
        companyName.textContent = info.companyName || COMPANY_SYMBOL;
        companyCode.textContent = COMPANY_SYMBOL;
        
        // Price information
        const lastPrice = priceInfo.lastPrice || 0;
        const change = priceInfo.change || 0;
        const changePercent = priceInfo.pChange || 0;
        
        currentPrice.textContent = `₹${formatNumber(lastPrice)}`;
        
        if (change >= 0) {
            priceChange.textContent = `+${change.toFixed(2)} (${changePercent.toFixed(2)}%)`;
            priceChange.classList.add('positive');
        } else {
            priceChange.textContent = `${change.toFixed(2)} (${changePercent.toFixed(2)}%)`;
            priceChange.classList.add('negative');
        }
        
        // Trading information
        openPrice.textContent = `₹${formatNumber(priceInfo.open || 0)}`;
        highPrice.textContent = `₹${formatNumber(priceInfo.dayHigh || 0)}`;
        lowPrice.textContent = `₹${formatNumber(priceInfo.dayLow || 0)}`;
        closePrice.textContent = `₹${formatNumber(priceInfo.previousClose || 0)}`;
        volume.textContent = formatNumber(priceInfo.totalTradedVolume || 0);
        weekHigh.textContent = `₹${formatNumber(priceInfo.weekHigh || 0)}`;
        weekLow.textContent = `₹${formatNumber(priceInfo.weekLow || 0)}`;
        marketCapElem.textContent = `₹${formatCrores(priceInfo.marketCap || 0)}`;
        
        // Company information
        industry.textContent = metadata.industry || 'N/A';
        indexElem.textContent = metadata.indices || 'N/A';
        faceValue.textContent = `₹${metadata.faceValue || 0}`;
        listingDate.textContent = formatDate(metadata.listingDate) || 'N/A';
        peRatio.textContent = (priceInfo.pe || 0).toFixed(2);
        eps.textContent = `₹${(priceInfo.eps || 0).toFixed(2)}`;
        dividendYield.textContent = `${(priceInfo.dividendYield || 0).toFixed(2)}%`;
        bookValue.textContent = `₹${(metadata.bookValue || 0).toFixed(2)}`;
    }
    
    /**
     * Initialize chart data and create chart
     */
    function initializeChartData() {
        setupEventListeners();
        updateChart(currentPeriod);
    }
    
    /**
     * Update chart based on selected period
     * @param {string} period - Time period for chart
     */
    function updateChart(period) {
        const historicalData = companyData.historicalData || [];
        
        if (historicalData.length === 0) {
            return;
        }
        
        // Filter data based on period
        let filteredData = [];
        const now = new Date();
        
        switch (period) {
            case '1M':
                // Last 30 days
                const oneMonthAgo = new Date();
                oneMonthAgo.setDate(now.getDate() - 30);
                filteredData = historicalData.filter(item => new Date(item.date) >= oneMonthAgo);
                break;
            case '3M':
                // Last 90 days
                const threeMonthsAgo = new Date();
                threeMonthsAgo.setDate(now.getDate() - 90);
                filteredData = historicalData.filter(item => new Date(item.date) >= threeMonthsAgo);
                break;
            case '6M':
                // Last 180 days
                const sixMonthsAgo = new Date();
                sixMonthsAgo.setDate(now.getDate() - 180);
                filteredData = historicalData.filter(item => new Date(item.date) >= sixMonthsAgo);
                break;
            case '1Y':
                // Last 365 days
                const oneYearAgo = new Date();
                oneYearAgo.setDate(now.getDate() - 365);
                filteredData = historicalData.filter(item => new Date(item.date) >= oneYearAgo);
                break;
            case 'ALL':
                // All data
                filteredData = historicalData;
                break;
            default:
                // Default to 1 year
                const defaultOneYearAgo = new Date();
                defaultOneYearAgo.setDate(now.getDate() - 365);
                filteredData = historicalData.filter(item => new Date(item.date) >= defaultOneYearAgo);
        }
        
        // Sort data by date
        filteredData.sort((a, b) => new Date(a.date) - new Date(b.date));
        
        // Extract data for chart
        const labels = filteredData.map(item => item.date);
        const prices = filteredData.map(item => item.close);
        
        // Create/update chart
        if (chart) {
            chart.destroy();
        }
        
        const ctx = priceChart.getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Close Price (₹)',
                    data: prices,
                    borderColor: '#00b9ff',
                    backgroundColor: 'rgba(0, 185, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '#00b9ff',
                    pointHoverBorderColor: '#ffffff',
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                return `₹${context.raw.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxTicksLimit: 10,
                            callback: function(value, index, values) {
                                // Show fewer x-axis labels for clarity
                                if (period === '1M' || period === '3M') {
                                    return labels[index];
                                } else {
                                    // For longer periods, show month and year
                                    const date = new Date(labels[index]);
                                    return `${date.toLocaleString('default', { month: 'short' })} ${date.getFullYear()}`;
                                }
                            }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return `₹${value}`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Load order book data
     * @param {string} type - Type of orders ('buy' or 'sell')
     */
    function loadOrderBook(type) {
        const tradeInfo = companyData.tradeInfo || {};
        const buyOrders = tradeInfo.buyOrders || [];
        const sellOrders = tradeInfo.sellOrders || [];
        
        // Get orders based on type
        const orders = type === 'buy' ? buyOrders : sellOrders;
        
        if (orders.length === 0) {
            orderBookBody.innerHTML = '<tr><td colspan="3" class="text-center">No data available</td></tr>';
            return;
        }
        
        orderBookBody.innerHTML = '';
        
        orders.forEach(order => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>₹${formatNumber(order.price)}</td>
                <td>${formatNumber(order.quantity)}</td>
                <td>${order.orders}</td>
            `;
            orderBookBody.appendChild(row);
        });
    }
    
    /**
     * Load company announcements
     */
    function loadAnnouncements() {
        const announcements = companyData.announcements || [];
        
        if (announcements.length === 0) {
            announcementsList.innerHTML = '<div class="empty-state">No announcements available</div>';
            return;
        }
        
        announcementsList.innerHTML = '';
        
        // Sort announcements by date (most recent first)
        announcements.sort((a, b) => new Date(b.date) - new Date(a.date));
        
        // Show up to 5 most recent announcements
        const recentAnnouncements = announcements.slice(0, 5);
        
        recentAnnouncements.forEach(announcement => {
            const announcementItem = document.createElement('div');
            announcementItem.className = 'announcement-item';
            announcementItem.innerHTML = `
                <div class="announcement-date">${formatDate(announcement.date)}</div>
                <div class="announcement-title">${announcement.title}</div>
                <a href="${announcement.url}" class="announcement-link" target="_blank">View Details</a>
            `;
            announcementsList.appendChild(announcementItem);
        });
    }
    
    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Chart period buttons
        chartPeriodBtns.forEach(button => {
            button.addEventListener('click', function() {
                const period = this.dataset.period;
                
                // Update active button
                chartPeriodBtns.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Update chart
                currentPeriod = period;
                updateChart(period);
            });
        });
        
        // Order book tabs
        orderBookTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const tabType = this.dataset.tab;
                
                // Update active tab
                orderBookTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Update order book
                currentOrderBookTab = tabType;
                loadOrderBook(tabType);
            });
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
    
    /**
     * Format value in crores
     * @param {number} num - Number to format
     * @returns {string} Formatted value
     */
    function formatCrores(num) {
        if (num >= 10000000) {
            return `${(num / 10000000).toFixed(2)} Cr`;
        } else {
            return formatNumber(num);
        }
    }
    
    /**
     * Format date
     * @param {string} dateString - Date string
     * @returns {string} Formatted date
     */
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        const date = new Date(dateString);
        return date.toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    }
});