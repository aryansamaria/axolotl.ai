from flask import Blueprint, render_template, request, jsonify
import logging
from models.investment_model import investment_model

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
investment_bp = Blueprint('investment', __name__, url_prefix='/invest')

@investment_bp.route('/')
def index():
    """Investment landing page"""
    return render_template('investment/index.html')

@investment_bp.route('/company/<symbol>')
def company_details(symbol):
    """Company details page"""
    return render_template('investment/company_details.html', symbol=symbol)

@investment_bp.route('/api/company/<symbol>')
def get_company_data(symbol):
    """API endpoint to get company data"""
    try:
        data = investment_model.get_company_data(symbol.upper())
        
        if not data:
            return jsonify({
                'success': False,
                'message': f"Could not find data for {symbol}"
            }), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
    
    except Exception as e:
        logger.error(f"Error getting company data: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@investment_bp.route('/api/search')
def search_companies():
    """API endpoint to search for companies"""
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify({
            'success': True,
            'results': []
        })
    
    try:
        results = investment_model.search_companies(query)
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@investment_bp.route('/api/market-movers')
def get_market_movers():
    """API endpoint to get market movers"""
    category = request.args.get('category', 'gainers')
    count = int(request.args.get('count', 5))
    
    try:
        data = investment_model.get_market_movers(category, count)
        
        return jsonify({
            'success': True,
            'category': category,
            'data': data
        })
    
    except Exception as e:
        logger.error(f"Error getting market movers: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500