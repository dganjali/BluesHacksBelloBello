# BluesHacks2025-ByteBite

## Project Overview
ByteBite is an inventory management system designed to help food banks manage their stock efficiently. The system includes user authentication, inventory tracking, and integration with the Nutritionix API to fetch nutritional information.

## Features
1. **User Authentication**
   - Sign Up: Users can create an account with a username, email, and password.
   - Sign In: Users can log in using their email or username and password.
   - JWT-based authentication for secure access to protected routes.
   - Logout functionality to clear user session.

2. **Inventory Management**
   - Add new stock items with details such as food type, quantity, and expiration date.
   - Fetch nutritional information for food items using the Nutritionix API.
   - View current stock with details including nutritional information.
   - Delete stock items from the inventory.

3. **Nutritionix API Integration**
   - Search for food items and fetch nutritional information.
   - Debounced search to optimize API calls.

4. **Frontend**
   - Responsive design with a clean and user-friendly interface.
   - Separate pages for sign-in, sign-up, and dashboard.
   - Autocomplete functionality for food type input.

## Project Structure