#!/usr/bin/env python3
import sys
import json
from datetime import datetime
import pandas as pd
from foodbank_regression import FoodBankDatabase, FoodBankDistributionModel
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import os.path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'backend-model', 'user_data')

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5001", "https://blueshacksByteBite.onrender.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Create the data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Handle OPTIONS requests for all routes
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response

# Add health check endpoint
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

def handle_add_item(data):
    """Handle adding new item to user's inventory."""
    try:
        user_id = data['user_id']
        item_data = data['item_data']
        
        inventory_path = os.path.join(DATA_DIR, f'inventory_{user_id}.xlsx')
        
        try:
            df = pd.read_excel(inventory_path)
        except FileNotFoundError:
            df = pd.DataFrame(columns=[
                'food_item', 'food_type', 'current_quantity', 'expiration_date',
                'days_until_expiry', 'calories', 'sugars', 'nutritional_ratio',
                'weekly_customers'
            ])
        
        # Add new item
        new_row = {
            'food_item': item_data['type'],
            'food_type': item_data['category'],
            'current_quantity': item_data['quantity'],
            'expiration_date': item_data['expiration_date'],
            'days_until_expiry': (pd.to_datetime(item_data['expiration_date']) - pd.Timestamp.now()).days,
            'calories': item_data['nutritional_value']['calories'],
            'sugars': item_data['nutritional_value']['sugars'],
            'nutritional_ratio': item_data['nutritional_value']['calories'] / (item_data['nutritional_value']['sugars'] + 1),
            'weekly_customers': 100  # Default value
        }
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(inventory_path, index=False)
        
        return {'success': True}
    except Exception as e:
        print(f"Error adding inventory item: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.route('/api/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == "OPTIONS":
        return make_response()
        
    try:
        data = request.json
        user_id = data.get('user_id')
        inventory_data = data.get('inventory_data', [])
        
        # Use absolute paths
        os.makedirs(DATA_DIR, exist_ok=True)
        inventory_path = os.path.join(DATA_DIR, f'inventory_{user_id}.xlsx')
        distribution_path = os.path.join(DATA_DIR, f'distribution_plan_{user_id}.xlsx')
        
        if inventory_data:
            inventory_df = pd.DataFrame(inventory_data)
            inventory_df.to_excel(inventory_path, index=False)
        
        db = FoodBankDatabase(user_id)
        df = db.load_data()
        
        if df.empty:
            empty_plan = pd.DataFrame(columns=[
                'food_item', 'food_type', 'days_until_expiry', 'current_quantity',
                'recommended_quantity', 'priority_score', 'rank'
            ])
            empty_plan.to_excel(distribution_path, index=False)
            return jsonify({
                'success': True,
                'distribution_plan': []
            })
            
        # Get predictions
        model = FoodBankDistributionModel()
        model.train(df)
        distribution_plan = model.get_distribution_plan(df)
        
        # Save full distribution plan to Excel
        distribution_plan.to_excel(distribution_path, index=False)
        
        # Return top 10 for display
        top_10_plan = distribution_plan.nlargest(10, 'priority_score')
        
        response = {
            'success': True,
            'distribution_plan': top_10_plan[['food_item', 'food_type', 
                'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                'priority_score', 'rank']].to_dict('records')
        }
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in prediction: {str(e)}", file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'add_item':
            data = json.loads(sys.argv[2])
            result = handle_add_item(data)
            print(json.dumps(result))
            sys.exit(0 if result['success'] else 1)
        elif command == 'predict':
            data = json.loads(sys.argv[2])
            user_id = data['user_id']
            db = FoodBankDatabase(user_id)
            df = db.load_data()
            
            if df.empty:
                print(json.dumps({
                    'success': True,
                    'distribution_plan': [],
                    'message': 'No inventory data available'
                }))
                sys.exit(0)
            
            # Get predictions
            try:
                # Create model instance first
                model = FoodBankDistributionModel()
                model.train(df)
                distribution_plan = model.get_distribution_plan(df)
                
                # Get top 10 items by priority score
                top_10_plan = distribution_plan.nlargest(10, 'priority_score')
                
                # Save distribution plan to Excel
                distribution_path = os.path.join(DATA_DIR, f'distribution_plan_{user_id}.xlsx')
                distribution_plan.to_excel(distribution_path, index=False)
                
                response = {
                    'success': True,
                    'distribution_plan': top_10_plan[['food_item', 'food_type', 
                        'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                        'priority_score', 'rank']].to_dict('records')
                }
                
                print(json.dumps(response))
                sys.exit(0)
            except Exception as e:
                print(json.dumps({
                    'success': False,
                    'error': str(e)
                }))
                sys.exit(1)
    else:
        # Get port from environment variable for Render
        port = int(os.environ.get('PORT', 5002))
        # Allow any host to connect
        app.run(host='0.0.0.0', port=port, debug=True)