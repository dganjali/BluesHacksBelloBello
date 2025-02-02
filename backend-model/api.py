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
        data = request.json
        user_id = data.get('user_id')
        
        db = FoodBankDatabase(user_id)
        df = db.load_data()
        
        if df.empty:
            return jsonify({
                'success': True,
                'distribution_plan': [],
                'message': 'No inventory data available'
            })
            
        # Get predictions
        try:
            model.train(df)
            distribution_plan = model.get_distribution_plan(df)
            
            response = {
                'success': True,
                'distribution_plan': distribution_plan[['food_item', 'food_type', 
                    'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                    'priority_score', 'rank']].to_dict('records')
            }
            
            return jsonify(response)
        except ValueError as ve:
            return jsonify({
                'success': False,
                'error': str(ve)
            }), 400
            
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
                model.train(df)
                distribution_plan = model.get_distribution_plan(df)
                
                response = {
                    'success': True,
                    'distribution_plan': distribution_plan[['food_item', 'food_type', 
                        'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                        'priority_score', 'rank']].to_dict('records')
                }
                
                print(json.dumps(response))
                sys.exit(0)
            except ValueError as ve:
                print(json.dumps({
                    'success': False,
                    'error': str(ve)
                }))
                sys.exit(1)
    else:
        # Get port from environment variable for Render
        port = int(os.environ.get('PORT', 5002))
        # Allow any host to connect
        app.run(host='0.0.0.0', port=port)