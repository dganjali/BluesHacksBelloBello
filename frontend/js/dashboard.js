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
    const token = localStorage.getItem("token");
    const username = localStorage.getItem("username");
    const inventoryBody = document.getElementById("inventory-body");
    const addStockForm = document.getElementById("add-stock-form");
    const foodTypeInput = document.getElementById("food-type");
    const suggestionsList = document.getElementById("suggestions-list");

    if (!token) {
        window.location.href = "signin.html";
        return;
    }

    // Display username
    document.getElementById("username-display").textContent = username;

    // Logout functionality
    document.getElementById("logoutButton").addEventListener("click", logout);

    // Fetch inventory data and update the table
    const fetchInventory = async () => {
        inventoryBody.innerHTML = "";
        try {
            const response = await fetch(`${API_BASE}/api/inventory`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            const inventoryData = await response.json();
            
            inventoryData.forEach(item => {
                const row = createInventoryRow(item);
                inventoryBody.appendChild(row);
            });
        } catch (error) {
            console.error("Failed to load inventory data", error);
        }
    };

    // Update the inventory table row creation
    const createInventoryRow = (item) => {
        let nutritionalInfo = "N/A";
        if (item.nutritional_value) {
            const nv = item.nutritional_value;
            nutritionalInfo = `
                Calories: ${nv.calories} kcal<br/>
                Fat: ${nv.total_fat} g<br/>
                Protein: ${nv.protein} g<br/>
                Carbs: ${nv.carbohydrates} g<br/>
                Sugars: ${nv.sugars} g<br/>
                Sodium: ${nv.sodium} mg
            `;
        }

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.type}</td>
            <td>${item.quantity}</td>
            <td>${new Date(item.expiration_date).toLocaleDateString()}</td>
            <td>${nutritionalInfo}</td>
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

    // Add stock form handler
    addStockForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const type = foodTypeInput.value;
        const quantity = document.getElementById("quantity").value;
        const expiration_date = document.getElementById("expiration-date").value;

        try {
            const response = await fetch(`${API_BASE}/api/inventory/add`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ type, quantity, expiration_date }),
            });

            const data = await response.json();
            if (response.ok) {
                fetchInventory();
                addStockForm.reset();
            } else {
                alert(data.error || "Failed to add stock");
            }
        } catch (error) {
            console.error("Error adding stock:", error);
            alert("An error occurred while adding stock");
        }
    });

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
            const suggestions = await response.json();

            if (suggestions.length > 0) {
                suggestionsList.innerHTML = '';
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
                suggestionsList.classList.add('active');
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
});
