import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class FoodBankDatabase:
    def __init__(self, excel_path):
        """Initialize database connection with Excel file."""
        self.excel_path = excel_path
        
    def load_data(self):
        """Load and preprocess data from Excel file."""
        try:
            # Read Excel file
            df = pd.read_excel(self.excel_path)
            
            # Rename columns to match expected format (if needed)
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
            
            # Validate required columns
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
        """Preprocess the input data."""
        processed_df = df.copy()
        
        # Use existing days until expiration from database
        # No need to calculate as it's already provided
        
        # Encode categorical variables
        categorical_columns = ['food_type', 'food_item']
        for col in categorical_columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                processed_df[col] = self.label_encoders[col].fit_transform(processed_df[col])
            else:
                processed_df[col] = self.label_encoders[col].transform(processed_df[col])
        
        # Prepare features
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
        """Calculate priority scores based on business rules.
        
        The weightage percentage distribuition for variable types:

        Current weights:

        Expiration (40%): Items closer to expiration get higher priority
        Nutritional ratio (25%): Better nutrition gets higher priority
        Quantity vs customers (35%): Balance between stock and demand
        """
        scores = np.zeros(len(df))
        
        # Higher priority for items closer to expiration
        scores += 1 / (df['days_until_expiry'] + 1) * 40
        
        # Priority based on nutritional ratio
        scores += df['nutritional_ratio'] * 25
        
        # Priority based on current quantity vs weekly customers
        scores += (df['current_quantity'] / df['weekly_customers']) * 35
        
        return scores
        
    def calculate_recommended_quantities(self, df):
        """Calculate recommended quantities based on business rules."""
        # Base calculation on current quantity and weekly customers
        base_quantity = df['current_quantity'] / df['weekly_customers']
        
        # Adjust for expiration
        expiry_factor = 1 + (1 / (df['days_until_expiry'] + 1))
        
        # Adjust for nutritional value
        nutrition_factor = 1 + (df['nutritional_ratio'] / df['nutritional_ratio'].max())
        
        # Calculate final recommended quantities
        quantities = base_quantity * expiry_factor * nutrition_factor
        
        # Ensure minimum nutritional requirements
        quantities = np.maximum(quantities, 1)  # Minimum 1 unit per person
        
        return quantities
        
    def train(self, df):
        """Train the model on the provided data."""
        X = self.preprocess_data(df)
        
        # Target variables: priority_score and recommended_quantity
        y_priority = self.calculate_priority_scores(df)
        y_quantity = self.calculate_recommended_quantities(df)
        
        # Train models
        self.model.fit(X, np.column_stack((y_priority, y_quantity)))
    
    def predict(self, df):
        """Make predictions for new data."""
        X = self.preprocess_data(df)
        predictions = self.model.predict(X)
        
        return {
            'priority_scores': predictions[:, 0],
            'recommended_quantities': predictions[:, 1]
        }
        
    def get_distribution_plan(self, df):
        """Generate a complete distribution plan."""
        predictions = self.predict(df)
        
        # Create results DataFrame
        results = df.copy()
        results['priority_score'] = predictions['priority_scores']
        results['recommended_quantity'] = predictions['recommended_quantities']
        
        # Sort by priority score
        results = results.sort_values('priority_score', ascending=False)
        
        # Add rankings
        results['rank'] = range(1, len(results) + 1)
        
        return results

# Example usage
def main():
    # Initialize database connection
    excel_path = "foodbank_dataset.xlsx" 
    db = FoodBankDatabase(excel_path)
               
    try:
        # Load data
        data = db.load_data()
        
        # Number of rows
        num_rows = data.shape[0]
        
        print()
        print(f"There are {num_rows} entries in the food inventory spreadsheet.")
        print()
        try:
            num_ranks = int(input("Enter the number of entries that you want to be ranked for optimized distribution: "))
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
            return
        
        # Initialize and train model
        model = FoodBankDistributionModel()
        model.train(data)
        
        # Get distribution plan
        distribution_plan = model.get_distribution_plan(data)
        
        # Display results
        print(f"\nTop {num_ranks} Priority Items:")
        print(distribution_plan[['food_item', 'food_type', 'days_until_expiry', 
                               'current_quantity', 'recommended_quantity', 
                               'priority_score', 'rank']].head(num_ranks))
        
        # Save results to Excel
        distribution_plan.to_excel("distribution_plan.xlsx", index=False)
        print("\nFull distribution plan saved to 'distribution_plan.xlsx'")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
