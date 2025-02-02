#!/usr/bin/env python3
import sys
import json
from datetime import datetime
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from flask import Flask, request, jsonify
from flask_cors import CORS

class FoodBankDistributionModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
    def train(self, df):
        features = ['days_until_expiry', 'current_quantity', 
                   'calories', 'sugars', 'nutritional_ratio']
        X = self.scaler.fit_transform(df[features])
        y = df['current_quantity']
        self.model.fit(X, y)
        
    def get_distribution_plan(self, df):
        features = ['days_until_expiry', 'current_quantity', 
                   'calories', 'sugars', 'nutritional_ratio']
        X = self.scaler.transform(df[features])
        df['recommended_quantity'] = self.model.predict(X)
        df['priority_score'] = (
            df['days_until_expiry'] * 0.3 +
            df['nutritional_ratio'] * 0.4 +
            (df['current_quantity'] / df['recommended_quantity']) * 0.3
        )
        df['rank'] = df['priority_score'].rank(ascending=False)
        return df

app = Flask(__name__)
CORS(app)
model = FoodBankDistributionModel()

@app.route('/predict', methods=['POST'])
def predict():
    try:
        inventory_data = request.json
        df = pd.DataFrame(inventory_data)
        
        # Prepare data
        df['food_item'] = df['type']
        df['food_type'] = df['type']
        df['days_until_expiry'] = (pd.to_datetime(df['expiration_date']) - pd.Timestamp.now()).dt.days
        df['current_quantity'] = df['quantity']
        df['calories'] = df.apply(lambda x: x['nutritional_value']['calories'], axis=1)
        df['sugars'] = df.apply(lambda x: x['nutritional_value']['sugars'], axis=1)
        df['nutritional_ratio'] = df['calories'] / (df['sugars'] + 1)
        df['weekly_customers'] = 100
        
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

if len(sys.argv) > 1:
    # Command line mode
    try:
        inventory_data = json.loads(sys.argv[1])
        df = pd.DataFrame(inventory_data)
        model.train(df)
        distribution_plan = model.get_distribution_plan(df)
        print(json.dumps({
            'success': True,
            'distribution_plan': distribution_plan.to_dict('records')
        }))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))
        sys.exit(1)
else:
    # Server mode
    app.run(port=5002)