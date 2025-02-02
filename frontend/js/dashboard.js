import { logout } from './auth.js';

const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:5001' 
    : 'https://blueshacksbellobello.onrender.com';

const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

document.addEventListener("DOMContentLoaded", async () => {
    // Get both token and username from localStorage
    const token = localStorage.getItem("token");
    const username = localStorage.getItem("username");
    
    if (!token) {
        window.location.href = "signin.html";
        return;
    }

    // Update username display
    const usernameDisplay = document.getElementById("username-display");
    if (usernameDisplay && username) {
        usernameDisplay.textContent = username;
    }

    const inventoryBody = document.getElementById("inventory-body");
    const addStockForm = document.getElementById("add-stock-form");
    const foodTypeInput = document.getElementById("food-type");
    const suggestionsList = document.getElementById("suggestions-list");

    // Logout functionality
    document.getElementById("logoutButton").addEventListener("click", logout);

    // Fetch inventory data and update the table
    const fetchInventory = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/inventory`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            const inventoryData = await response.json();
            
            // Update inventory table
            inventoryBody.innerHTML = "";
            inventoryData.forEach(item => {
                const row = createInventoryRow(item);
                inventoryBody.appendChild(row);
            });
            
            // Fetch distribution plan
            await fetchDistributionPlan(inventoryData);
            
        } catch (error) {
            console.error("Failed to load inventory data", error);
        }
    };

    // Add this function after fetchInventory
    const fetchDistributionPlan = async (inventoryData) => {
        try {
            const response = await fetch(`${API_BASE}/api/predict`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const data = await response.json();
            if (data.success) {
                updateDistributionPlanTable(data.distribution_plan);
            } else {
                console.error('Failed to get distribution plan:', data.error);
            }
        } catch (error) {
            console.error('Error fetching distribution plan:', error);
        }
    };

    const updateDistributionPlanTable = (distributionPlan) => {
        const tableBody = document.getElementById('distribution-plan-body');
        tableBody.innerHTML = '';
        
        distributionPlan.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.food_item}</td>
                <td>${item.current_quantity}</td>
                <td>${Math.round(item.recommended_quantity)}</td>
                <td>${item.priority_score.toFixed(2)}</td>
                <td>${item.rank}</td>
            `;
            tableBody.appendChild(row);
        });
    };

    // Update the inventory table row creation
    const createInventoryRow = (item) => {
        const daysUntilExpiry = Math.ceil((new Date(item.expiration_date) - new Date()) / (1000 * 60 * 60 * 24));
        const nutritionalRatio = item.nutritional_value.calories / (item.nutritional_value.sugars + 1);
        
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.type}</td>
            <td>${item.food_type}</td>
            <td>${item.quantity}</td>
            <td>${new Date(item.expiration_date).toLocaleDateString()}</td>
            <td>${daysUntilExpiry}</td>
            <td>${item.nutritional_value.calories}</td>
            <td>${item.nutritional_value.sugars}</td>
            <td>${item.weekly_customers}</td>
            <td>${nutritionalRatio.toFixed(2)}</td>
            <td>
                <button class="btn-delete" onclick="deleteItem('${item._id}')">Delete</button>
            </td>
        `;
        return row;
    };

    // Add delete function
    window.deleteItem = async (itemId) => {
        if (!confirm('Are you sure you want to delete this item?')) return;

        try {
            const response = await fetch(`${API_BASE}/api/inventory/delete/${itemId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                fetchInventory(); // Refresh the table
            } else {
                alert('Failed to delete item');
            }
        } catch (error) {
            console.error('Error deleting item:', error);
            alert('Error deleting item');
        }
    };

    // Update the add stock form handler
    const addStockFormHandler = async (e) => {
        e.preventDefault();

        const type = foodTypeInput.value;
        const category = document.getElementById("food-category").value;
        const quantity = document.getElementById("quantity").value;
        const expiration_date = document.getElementById("expiration-date").value;

        if (!type || !category || !quantity || !expiration_date) {
            alert("Please fill in all fields");
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/inventory/add`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ 
                    type, 
                    category,
                    quantity: Number(quantity), 
                    expiration_date 
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.details || 'Failed to add stock');
            }

            if (data.success) {
                const row = createInventoryRow(data.newItem);
                inventoryBody.insertBefore(row, inventoryBody.firstChild);
                addStockForm.reset();
                await fetchInventory();
            }
        } catch (error) {
            console.error("Error adding stock:", error);
            alert(error.message || "An error occurred while adding stock");
        }
    };

    addStockForm.addEventListener("submit", addStockFormHandler);

    // Add autocomplete functionality
    const handleFoodTypeInput = async (query) => {
        if (!query) {
            suggestionsList.innerHTML = '';
            suggestionsList.classList.remove('active');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) throw new Error('Failed to fetch suggestions');
            
            const suggestions = await response.json();
            
            suggestionsList.innerHTML = '';
            if (suggestions.length > 0) {
                suggestionsList.classList.add('active');
                suggestions.forEach(suggestion => {
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    div.textContent = suggestion;
                    div.addEventListener('click', () => {
                        foodTypeInput.value = suggestion;
                        suggestionsList.innerHTML = '';
                        suggestionsList.classList.remove('active');
                    });
                    suggestionsList.appendChild(div);
                });
            } else {
                suggestionsList.classList.remove('active');
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    };

    // Add input event listener with debounce
    foodTypeInput.addEventListener('input', debounce((e) => {
        handleFoodTypeInput(e.target.value);
    }, 300));

    // Close suggestions when clicking outside
    document.addEventListener('click', (e) => {
        if (!foodTypeInput.contains(e.target) && !suggestionsList.contains(e.target)) {
            suggestionsList.classList.remove('active');
        }
    });

    // Initial fetch of inventory
    fetchInventory();

    // Add weekly customers update handler
    document.getElementById('update-customers').addEventListener('click', async () => {
        const weeklyCustomers = document.getElementById('weekly-customers').value;
        try {
            const response = await fetch(`${API_BASE}/api/inventory/update-customers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ weekly_customers: Number(weeklyCustomers) })
            });
            
            if (response.ok) {
                fetchInventory(); // Refresh inventory
            } else {
                alert('Failed to update weekly customers');
            }
        } catch (error) {
            console.error('Error updating weekly customers:', error);
        }
    });

    // Add refresh distribution plan button handler
    document.getElementById('refresh-distribution').addEventListener('click', async () => {
        try {
            const loadingText = 'Refreshing...';
            const originalText = document.getElementById('refresh-distribution').textContent;
            document.getElementById('refresh-distribution').textContent = loadingText;
            document.getElementById('refresh-distribution').disabled = true;

            const response = await fetch(`${API_BASE}/api/predict`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                updateDistributionPlanTable(data.distribution_plan);
            } else {
                console.error('Failed to refresh distribution plan:', data.error);
                alert('Failed to refresh distribution plan: ' + data.error);
            }
        } catch (error) {
            console.error('Error refreshing distribution plan:', error);
            alert('Error refreshing distribution plan');
        } finally {
            document.getElementById('refresh-distribution').textContent = originalText;
            document.getElementById('refresh-distribution').disabled = false;
        }
    });
});

app.post('/api/predict', verifyToken, async (req, res) => {
  try {
    const userId = req.user.id;
    const inventory = await Stock.find({ addedBy: userId }).sort({ createdAt: -1 });

    if (!inventory.length) {
      return res.json({
        success: true,
        distribution_plan: []
      });
    }

    const formattedInventory = inventory.map(item => ({
      food_item: item.type,
      food_type: item.food_type,
      current_quantity: item.quantity,
      expiration_date: item.expiration_date,
      days_until_expiry: Math.ceil((new Date(item.expiration_date) - new Date()) / (1000 * 60 * 60 * 24)),
      calories: item.nutritional_value.calories,
      sugars: item.nutritional_value.sugars,
      nutritional_ratio: item.nutritional_value.calories / (item.nutritional_value.sugars + 1),
      weekly_customers: item.weekly_customers || 100
    }));

    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    const pythonProcess = spawn(pythonPath, [
      path.resolve(__dirname, '../backend-model/api.py'),
      'predict',
      JSON.stringify({
        user_id: userId,
        inventory_data: formattedInventory
      })
    ]);

    let result = '';
    let pythonError = '';

    pythonProcess.stdout.on('data', (data) => {
      result += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      pythonError += data.toString();
      console.error('Python Error:', data.toString());
    });

    return new Promise((resolve, reject) => {
      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          console.error('Python process failed:', pythonError);
          reject(new Error(`Python process failed: ${pythonError}`));
          return;
        }

        try {
          console.log('Raw Python output:', result);
          const predictionData = JSON.parse(result.trim());
          resolve(res.json(predictionData));
        } catch (error) {
          console.error('Failed to parse Python output:', error);
          console.error('Raw output:', result);
          reject(new Error('Failed to parse prediction results'));
        }
      });

      pythonProcess.on('error', (error) => {
        console.error('Python process error:', error);
        reject(new Error(`Failed to start Python process: ${error.message}`));
      });
    });
  } catch (error) {
    console.error('Error in distribution plan:', error);
    throw error;
  }
});

// Update distribution plan table
function updateDistributionPlanTable(plan) {
  const tbody = document.getElementById('distribution-plan-body');
  tbody.innerHTML = '';

  plan.forEach(item => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${item.food_item}</td>
      <td>${item.current_quantity}</td>
      <td>${Math.round(item.recommended_quantity)}</td>
      <td>${item.priority_score.toFixed(2)}</td>
      <td>${item.rank}</td>
    `;
    tbody.appendChild(row);
  });
}

// Event listener for logout
document.getElementById('logout').addEventListener('click', () => {
  localStorage.removeItem('token');
  localStorage.removeItem('username');
  window.location.href = '/signin.html';
});

// Form validation
function validateForm() {
  const type = document.getElementById('food-type').value;
  const category = document.getElementById('food-category').value;
  const quantity = document.getElementById('quantity').value;
  const expiration = document.getElementById('expiration-date').value;

  if (!type || !category || !quantity || !expiration) {
    alert('Please fill in all fields');
    return false;
  }

  if (quantity <= 0) {
    alert('Quantity must be greater than 0');
    return false;
  }

  const expirationDate = new Date(expiration);
  if (expirationDate < new Date()) {
    alert('Expiration date must be in the future');
    return false;
  }

  return true;
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  try {
    await fetchInventory();
    await fetchDistributionPlan();
  } catch (error) {
    console.error('Initialization error:', error);
    alert('Failed to initialize dashboard');
  }
});
