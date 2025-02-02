require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const bodyParser = require('body-parser');
const path = require('path');
const cors = require('cors');
const axios = require('axios');
const debounce = require('debounce-promise');
const User = require('./models/User');
const { spawn } = require('child_process');

const app = express();
app.use(cors({
  origin: ['http://localhost:5001', 'https://blueshacksbellobello.onrender.com'],
  credentials: true
}));
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// Environment variables
const PORT = process.env.PORT || 5001;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/foodbank';
const JWT_SECRET = process.env.JWT_SECRET;
const NUTRITIONIX_APP_ID = process.env.NUTRITIONIX_APP_ID;
const NUTRITIONIX_API_KEY = process.env.NUTRITIONIX_API_KEY;

// MongoDB connection
mongoose.connect(MONGODB_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
    serverSelectionTimeoutMS: 30000, // Increased timeout
    retryWrites: true,
    w: 'majority'
}).then(() => {
    console.log('Connected to MongoDB');
}).catch((err) => {
    console.error('MongoDB connection error:', err);
});

// MongoDB schemas
const StockSchema = new mongoose.Schema({
  type: String,
  food_type: {
    type: String,
    enum: ['Snacks', 'Protein', 'Vegetables', 'Grain', 'Dairy', 'Canned Goods'],
    required: true
  },
  quantity: Number,
  expiration_date: Date,
  days_until_expiry: {
    type: Number,
    default: function() {
      return Math.ceil((this.expiration_date - new Date()) / (1000 * 60 * 60 * 24));
    }
  },
  weekly_customers: { type: Number, default: 100 },
  nutritional_value: {
    calories: Number,
    sugars: Number,
    nutritional_ratio: {
      type: Number,
      default: function() {
        return this.nutritional_value.calories / (this.nutritional_value.sugars + 1);
      }
    }
  },
  addedBy: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  createdAt: { type: Date, default: Date.now }
});

const Stock = mongoose.model('Stock', StockSchema);

// Middleware to verify JWT token for restricted pages
const verifyToken = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(403).json({ error: 'Invalid or expired token' });
  }
};

// Nutritionix API Integration
const searchNutritionix = debounce(async (query) => {
  try {
    const response = await axios.get(
      'https://trackapi.nutritionix.com/v2/search/instant',
      {
        params: { query },
        headers: {
          'x-app-id': NUTRITIONIX_APP_ID,
          'x-app-key': NUTRITIONIX_API_KEY
        }
      }
    );
    return response.data.common.slice(0, 5).map(item => item.food_name);
  } catch (error) {
    console.error('Error searching Nutritionix:', error);
    return [];
  }
}, 300);

// Function to fetch nutritional info
const getNutritionalInfo = async (foodType) => {
  try {
    const response = await axios.post(
      'https://trackapi.nutritionix.com/v2/natural/nutrients',
      { query: foodType },
      {
        headers: {
          'x-app-id': NUTRITIONIX_APP_ID,
          'x-app-key': NUTRITIONIX_API_KEY,
        }
      }
    );

    if (response.data?.foods?.[0]) {
      const food = response.data.foods[0];
      return {
        calories: food.nf_calories,
        total_fat: food.nf_total_fat,
        protein: food.nf_protein,
        carbohydrates: food.nf_total_carbohydrate,
        sugars: food.nf_sugars,
        sodium: food.nf_sodium
      };
    }
    return null;
  } catch (error) {
    console.error('Error fetching nutritional info:', error);
    return null;
  }
};

// Auth endpoints
app.post('/api/signup', async (req, res) => {
  try {
    const { username, email, password } = req.body;

    // Validate input
    if (!username || !email || !password) {
      return res.status(400).json({ 
        success: false, 
        message: 'All fields are required' 
      });
    }

    // Check if user exists already
    const existingUser = await User.findOne({ 
      $or: [
        { email: email },
        { username: username }
      ]
    });

    if (existingUser) {
      return res.status(400).json({ 
        success: false, 
        message: 'User already exists' 
      });
    }

    // Create new user
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = new User({
      username,
      email,
      password: hashedPassword
    });
    
    await user.save();
    res.json({ success: true, message: 'User created successfully' });
  } catch (error) {
    console.error('Signup error:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Error creating user' 
    });
  }
});

app.post('/api/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    // Look for user by email or username
    const user = await User.findOne({
      $or: [
        { email: email },
        { username: email } // This allows logging in with username too
      ]
    });

    if (!user) {
      return res.status(400).json({ success: false, message: 'User not found' });
    }

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(400).json({ success: false, message: 'Invalid password' });
    }

    const token = jwt.sign(
      { id: user._id, email: user.email },
      JWT_SECRET,
      { expiresIn: '24h' }
    );

    res.json({ 
      success: true, 
      token,
      email: user.email,
      username: user.username // Use the actual username
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ success: false, message: 'Error logging in' });
  }
});

// Inventory endpoints
app.get('/api/search', async (req, res) => {
  const { query } = req.query;
  if (!query) return res.json([]);

  try {
    const suggestions = await searchNutritionix(query);
    res.json(suggestions);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch suggestions' });
  }
});

app.get('/api/inventory', verifyToken, async (req, res) => {
  try {
    const inventory = await Stock.find().sort({ createdAt: -1 });
    res.json(inventory);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch inventory' });
  }
});

app.post('/api/inventory/add', verifyToken, async (req, res) => {
  try {
    const { type, category, quantity, expiration_date } = req.body;
    
    const nutritionalValue = await getNutritionalInfo(type);
    if (!nutritionalValue) {
      return res.status(400).json({ error: 'Could not fetch nutritional information' });
    }

    const newItem = new Stock({
      type,
      category,
      quantity,
      expiration_date,
      nutritional_value: nutritionalValue,
      addedBy: req.user.id
    });

    await newItem.save();

    // Update user's Excel file
    const pythonProcess = spawn('python', [
      path.join(__dirname, '../backend-model/api.py'),
      'add_item',
      JSON.stringify({
        user_id: req.user.id,
        item_data: {
          type,
          category,
          quantity,
          expiration_date,
          nutritional_value: nutritionalValue
        }
      })
    ]);

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Python Error: ${data}`);
    });

    res.json({ success: true, newItem });
  } catch (error) {
    console.error('Error adding inventory:', error);
    res.status(500).json({ error: 'Failed to add item to inventory' });
  }
});

// Add delete endpoint
app.delete('/api/inventory/delete/:id', verifyToken, async (req, res) => {
    try {
        const item = await Stock.findById(req.params.id);
        if (!item) {
            return res.status(404).json({ error: 'Item not found' });
        }
        
        // Remove the ownership check since items are shared
        await Stock.findByIdAndDelete(req.params.id);
        res.json({ success: true });
    } catch (error) {
        console.error('Delete error:', error);
        res.status(500).json({ error: 'Failed to delete item' });
    }
});

app.post('/api/predict', verifyToken, async (req, res) => {
    try {
        const userId = req.user.id;
        const inventoryData = await Stock.find({ addedBy: userId }).sort({ createdAt: -1 });
        
        // Spawn Python process with user ID
        const pythonProcess = spawn('python', [
            path.join(__dirname, '../backend-model/api.py'),
            'predict',
            JSON.stringify({
                user_id: userId,
                inventory_data: inventoryData
            })
        ]);

        let result = '';

        pythonProcess.stdout.on('data', (data) => {
            result += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            console.error(`Python Error: ${data}`);
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                return res.status(500).json({ 
                    success: false, 
                    error: 'Failed to process prediction' 
                });
            }
            try {
                const predictionData = JSON.parse(result);
                res.json(predictionData);
            } catch (error) {
                res.status(500).json({ 
                    success: false, 
                    error: 'Failed to parse prediction results' 
                });
            }
        });
    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: 'Failed to get inventory data' 
        });
    }
});

// Serve the sign-in page on root
app.get('/signin', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend', 'signin.html'));
});

// Protect the dashboard route with verifyToken middleware
app.get('/dashboard', verifyToken, (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend', 'dashboard.html'));
});

// Serve other frontend pages (signup, index, etc.)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend', 'index.html'));
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
// Inventory endpoints

// Fetch inventory items (protected route)
app.get('/api/inventory', verifyToken, async (req, res) => {
  try {
    const inventory = await Stock.find({ addedBy: req.user.id }).sort({ createdAt: -1 });
    res.json(inventory);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch inventory' });
  }
});
