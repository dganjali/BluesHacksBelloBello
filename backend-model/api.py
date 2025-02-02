#!/usr/bin/env python3
import sys
import json
from datetime import datetime
import pandas as pd
from foodbank_regression import FoodBankDatabase, FoodBankDistributionModel
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)
model = FoodBankDistributionModel()

# Add health check endpoint
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

def handle_add_item(data):
    """Handle adding new item to user's inventory."""
    try:
        user_id = data['user_id']
        item_data = data['item_data']
        
        db = FoodBankDatabase(user_id)
        success = db.add_inventory_item(item_data)
        
        return {'success': success}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/predict', methods=['POST'])
def predict():
    try:
        user_id = request.json.get('user_id')
        db = FoodBankDatabase(user_id)
        df = db.load_data()
        
        # Get predictions
        model.train(df)
        distribution_plan = model.get_distribution_plan(df)
        
        response = {
            'success': True,
            'distribution_plan': distribution_plan[['food_item', 'food_type', 
                'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                'priority_score', 'rank']].to_dict('records')
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'add_item':
            data = json.loads(sys.argv[2])
            result = handle_add_item(data)
            print(json.dumps(result))
            sys.exit(0 if result['success'] else 1)
    else:
        # Get port from environment variable for Render
        port = int(os.environ.get('PORT', 5002))
        # Allow any host to connect and use production mode
        app.run(host='0.0.0.0', port=port)