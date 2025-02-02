document.getElementById('signup-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const message = document.getElementById('message');

    try {
        const response = await fetch('http://localhost:5001/api/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (data.success) {
            message.textContent = 'Signup successful! Redirecting to signin...';
            message.style.color = 'green';
            setTimeout(() => {
                window.location.href = 'signin.html'; // Remove the leading slash
            }, 1500);
        } else {
            message.textContent = data.message || 'Signup failed';
            message.style.color = 'red';
        }
    } catch (error) {
        message.textContent = 'Error during signup. Please try again.';
        message.style.color = 'red';
        console.error('Error during signup:', error);
    }
});
