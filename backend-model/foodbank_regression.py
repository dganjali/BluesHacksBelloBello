import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore') ## ignore privacy wrnings for unidentified excel files, for instance
from flask import Flask, request, jsonify

app = Flask(__name__)

class FoodBankDatabase:
    def __init__(self, user_id):
        # start the database
        self.user_id = user_id
        self.excel_path = f'backend-model/user_data/inventory_{user_id}.xlsx'
        self.ensure_user_directory()
        
    def ensure_user_directory(self):
        directory = 'backend-model/user_data'
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        if not os.path.exists(self.excel_path):
            # excel columns (case-sensitive!!)
            df = pd.DataFrame(columns=[
                'food_item',
                'food_type',
                'current_quantity',
                'expiration_date',
                'days_until_expiry',
                'calories',
                'sugars',
                'nutritional_ratio',
                'weekly_customers'
            ])
            # save empty data frane
            df.to_excel(self.excel_path, index=False)
            print(f"Created new inventory file for user {self.user_id}")
    
    def add_inventory_item(self, item_data):
        """Add new inventory item to user's Excel file."""
        try:
            self.ensure_user_directory()
            
            try:
                df = pd.read_excel(self.excel_path)
            except:
                df = pd.DataFrame(columns=[
                    'food_item',
                    'food_type',
                    'current_quantity',
                    'expiration_date',
                    'days_until_expiry',
                    'calories',
                    'sugars',
                    'nutritional_ratio',
                    'weekly_customers'
                ])
            
            new_row = {
                'food_item': item_data['type'],
                'food_type': item_data['category'],
                'current_quantity': item_data['quantity'],
                'expiration_date': item_data['expiration_date'],
                'days_until_expiry': (pd.to_datetime(item_data['expiration_date']) - pd.Timestamp.now()).days,
                'calories': item_data['nutritional_value']['calories'],
                'sugars': item_data['nutritional_value']['sugars'],
                'nutritional_ratio': item_data['nutritional_value']['calories'] / (item_data['nutritional_value']['sugars'] + 1),
                'weekly_customers': 100
            }
            
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(self.excel_path, index=False)
            print(f"Successfully added item to inventory for user {self.user_id}")
            return True
        except Exception as e:
            print(f"Error adding inventory item: {str(e)}")
            return False

    def load_data(self):
        
        try:
            # read the excel rows
            df = pd.read_excel(self.excel_path)
            
            # change columns names so they are more formal 
            column_mapping = {
                'food item': 'food_item',
                'expiration': 'expiration_date',
                'days until expiration': 'days_until_expiry',
                'type of food': 'food_type',
                'quantity available': 'current_quantity',
                'calories per serving': 'calories',
                'sugars per serving': 'sugars',
                'customers that week': 'weekly_customers',
                'nutritional ratio (calories:sugars)': 'nutritional_ratio'
            }
            
            df = df.rename(columns=column_mapping)
            
            # handle an error if column number isnt precise
            required_columns = set(column_mapping.values())
            missing_columns = required_columns - set(df.columns)
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            return df
            
        except Exception as e:
            raise Exception(f"Error loading Excel file: {str(e)}")

class FoodBankDistributionModel:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )
        
    def preprocess_data(self, df):
        
        processed_df = df.copy()

        
        # label the variables
        categorical_columns = ['food_type', 'food_item']
        for col in categorical_columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                processed_df[col] = self.label_encoders[col].fit_transform(processed_df[col])
            else:
                processed_df[col] = self.label_encoders[col].transform(processed_df[col])
        
        # set up the features that we need
        feature_columns = [
            'days_until_expiry',
            'food_type',
            'current_quantity',
            'nutritional_ratio',
            'weekly_customers',
            'calories',
            'sugars'
        ]
        
        X = processed_df[feature_columns]
        
        if hasattr(self, 'scaler_fit'):
            X = pd.DataFrame(self.scaler.transform(X), columns=X.columns)
        else:
            X = pd.DataFrame(self.scaler.fit_transform(X), columns=X.columns)
            self.scaler_fit = True
            
        return X
        
    def calculate_priority_scores(self, df):
        """Calculation Note!* Based off industry customs and convention:
        
        The weightage percentage distribuition for variable types:

        Current weights:

        Expiration (40%): Items closer to expiration get higher priority
        Nutritional ratio (25%): Better nutrition gets higher priority
        Quantity vs customers (35%): Balance between stock and demand
        """
        scores = np.zeros(len(df))
        
        # higher priority for items closer to expiration
        scores += 1 / (df['days_until_expiry'] + 1) * 40
        
        # priority based on nutritional ratio
        scores += df['nutritional_ratio'] * 25
        
        # priority based on current quantity vs weekly customers
        scores += (df['current_quantity'] / df['weekly_customers']) * 35
        
        return scores
        
    def calculate_recommended_quantities(self, df):
        """ As mentioned, calculate recommended quantities based on relevant customs and rules."""
        # ratio between current quantity and weekly customers
        base_quantity = df['current_quantity'] / df['weekly_customers']
        
        # using the expiry weight to adjust
        expiry_factor = 1 + (1 / (df['days_until_expiry'] + 1))
        
        # using the nutritional weight to adjust 
        nutrition_factor = 1 + (df['nutritional_ratio'] / df['nutritional_ratio'].max())
        
        # multiply all the ratios for final quantity
        quantities = base_quantity * expiry_factor * nutrition_factor
        
        # also, each person should get at least 1 unit
        quantities = np.maximum(quantities, 1)  
        
        return quantities
        
    def train(self, df):
       
        X = self.preprocess_data(df)
        
        # need to target priority_score and recommended_quantity, its a two-dimensional output to the regressional model
        y_priority = self.calculate_priority_scores(df)
        y_quantity = self.calculate_recommended_quantities(df)
        
        # fit and train
        self.model.fit(X, np.column_stack((y_priority, y_quantity)))
    
    def predict(self, df):
        
        X = self.preprocess_data(df)
        predictions = self.model.predict(X)
        
        return {
            'priority_scores': predictions[:, 0],
            'recommended_quantities': predictions[:, 1]
        }
        
    def get_distribution_plan(self, df):
        # generating a distriubiton plan to be loaded to another excel here
        predictions = self.predict(df)
        
        # create a new dataframe, but for results
        results = df.copy()
        results['priority_score'] = predictions['priority_scores']
        results['recommended_quantity'] = predictions['recommended_quantities']
        
        # sort via priority score
        results = results.sort_values('priority_score', ascending=False)
        
        # append the ranks
        results['rank'] = range(1, len(results) + 1)
        
        return results

@app.route('/predict', methods=['POST'])

def predict():
    try:
        data = request.json
        user_id = data.get('user_id')
        
        # initialize db
        db = FoodBankDatabase(user_id)
        
        # load any inventory data
        df = db.load_data()
        
        if df.empty:
            return jsonify({
                'success': True,
                'distribution_plan': []
            })
        
        #  now predict
        model = FoodBankDistributionModel()
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

# sample usage for the 1000 row foodbank_dataset.xlsx training file (simulate inventory data)

def main():
    
    user_id = input("Enter user ID: ")
    db = FoodBankDatabase(user_id)
               
    try:
        # load again
        data = db.load_data()
        
        # gauge the size of the spreadsheet
        num_rows = data.shape[0]
        
        print()
        print(f"There are {num_rows} entries in the food inventory spreadsheet.")
        print()
        try:
            num_ranks = int(input("Enter the number of entries that you want to be ranked for optimized distribution: "))
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
            return
        
        # run the training model
        model = FoodBankDistributionModel()
        model.train(data)
        
        # output a new excel, disribution_plan.xlsx
        distribution_plan = model.get_distribution_plan(data)
        
        # display
        print(f"\nTop {num_ranks} Priority Items:")
        print(distribution_plan[['food_item', 'food_type', 'days_until_expiry', 
                               'current_quantity', 'recommended_quantity', 
                               'priority_score', 'rank']].head(num_ranks))
        
        # save!
        distribution_plan.to_excel("distribution_plan.xlsx", index=False)
        print("\nFull distribution plan saved to 'distribution_plan.xlsx'")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
    
if __name__ == "__main__":
    app.run(debug=True)
