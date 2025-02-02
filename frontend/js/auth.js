const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
const TOKEN_KEY = 'token';
const USERNAME_KEY = 'username';

export function isAuthenticated() {
    return localStorage.getItem(TOKEN_KEY) !== null;
}

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

export function setAuthData(token, username) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USERNAME_KEY, username);
}

export function clearAuthData() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
}

export function logout() {
    clearAuthData();
    window.location.href = 'signin.html';
}
