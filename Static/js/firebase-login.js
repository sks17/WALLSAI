/**
 * Firebase Login Module
 * 
 * Handles Firebase Authentication with:
 * - Email/Password authentication
 * - Google Sign-In
 * 
 * Sends ID token to Flask backend for session creation
 */

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { 
    getAuth, 
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signInWithPopup,
    GoogleAuthProvider,
    signOut,
    onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// Firebase configuration from template-injected variables
const firebaseConfig = {
    apiKey: window._FIREBASE_API_KEY,
    authDomain: window._FIREBASE_AUTH_DOMAIN,
    projectId: window._FIREBASE_PROJECT_ID,
    appId: window._FIREBASE_APP_ID
};

// Initialize Firebase
let app = null;
let auth = null;
let googleProvider = null;

try {
    // Only initialize if we have valid config
    if (firebaseConfig.apiKey && firebaseConfig.apiKey !== 'None' && firebaseConfig.apiKey !== '') {
        app = initializeApp(firebaseConfig);
        auth = getAuth(app);
        googleProvider = new GoogleAuthProvider();
        
        // Add scopes for Google Sign-In
        googleProvider.addScope('email');
        googleProvider.addScope('profile');
        
        console.log('[Firebase] Web SDK initialized with Google provider');
    } else {
        console.log('[Firebase] No config provided, using mock auth');
    }
} catch (error) {
    console.warn('[Firebase] Failed to initialize:', error);
}

/**
 * Send ID token to Flask backend
 */
async function sendTokenToBackend(idToken, email) {
    const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
            idToken: idToken,
            email: email
        })
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
        throw new Error(data.error || 'Backend authentication failed');
    }
    
    return data;
}

/**
 * Sign in with email and password
 */
async function login(email, password) {
    if (auth) {
        // Real Firebase auth
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const idToken = await userCredential.user.getIdToken();
        await sendTokenToBackend(idToken, email);
        return userCredential.user;
    } else {
        // Mock auth fallback
        console.log('[Firebase] Using mock login');
        const mockToken = 'mock_' + Date.now();
        await sendTokenToBackend(mockToken, email);
        return { uid: mockToken, email: email };
    }
}

/**
 * Create account with email and password
 */
async function signup(email, password) {
    if (auth) {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const idToken = await userCredential.user.getIdToken();
        await sendTokenToBackend(idToken, email);
        return userCredential.user;
    } else {
        // Mock signup fallback
        console.log('[Firebase] Using mock signup');
        const mockToken = 'mock_' + Date.now();
        await sendTokenToBackend(mockToken, email);
        return { uid: mockToken, email: email };
    }
}

/**
 * Sign in with Google
 */
async function signInWithGoogle() {
    if (!auth || !googleProvider) {
        // Mock Google sign-in for development
        console.log('[Firebase] Using mock Google sign-in');
        const mockEmail = 'google_user_' + Date.now() + '@gmail.com';
        const mockToken = 'mock_google_' + Date.now();
        await sendTokenToBackend(mockToken, mockEmail);
        return { 
            uid: mockToken, 
            email: mockEmail,
            displayName: 'Google User'
        };
    }
    
    try {
        const result = await signInWithPopup(auth, googleProvider);
        const user = result.user;
        const idToken = await user.getIdToken();
        
        console.log('[Firebase] Google sign-in successful:', user.email);
        
        // Send token to backend
        await sendTokenToBackend(idToken, user.email);
        
        return user;
    } catch (error) {
        console.error('[Firebase] Google sign-in error:', error);
        throw error;
    }
}

/**
 * Sign out
 */
async function logout() {
    if (auth) {
        await signOut(auth);
    }
    // Also clear Flask session
    await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include'
    });
}

/**
 * Get current user
 */
function getCurrentUser() {
    return auth ? auth.currentUser : null;
}

/**
 * Check if Firebase is configured
 */
function isConfigured() {
    return auth !== null;
}

/**
 * Check if Google Sign-In is available
 */
function isGoogleAvailable() {
    return googleProvider !== null;
}

// Export functions for use in templates
window.FirebaseLogin = {
    login,
    signup,
    signInWithGoogle,
    logout,
    getCurrentUser,
    isConfigured,
    isGoogleAvailable,
    auth
};

// Hook into login form when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const errorEl = document.getElementById('auth-error');
    const errorText = document.getElementById('auth-error-text');
    const successEl = document.getElementById('auth-success');
    const successText = document.getElementById('auth-success-text');
    
    function showError(message) {
        if (errorText) errorText.textContent = message;
        else if (errorEl) errorEl.textContent = message;
        if (errorEl) errorEl.classList.add('visible');
        if (successEl) successEl.classList.remove('visible');
    }
    
    function showSuccess(message) {
        if (successText) successText.textContent = message;
        else if (successEl) successEl.textContent = message;
        if (successEl) successEl.classList.add('visible');
        if (errorEl) errorEl.classList.remove('visible');
    }
    
    function setLoading(btn, loading) {
        if (!btn) return;
        const textEl = btn.querySelector('.btn-text') || btn;
        if (loading) {
            btn.disabled = true;
            btn.dataset.originalText = textEl.textContent;
            textEl.innerHTML = '<span class="spinner"></span> Please wait...';
        } else {
            btn.disabled = false;
            textEl.textContent = btn.dataset.originalText || 'Submit';
        }
    }
    
    // Login form handler
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = loginForm.querySelector('[name="email"]')?.value;
            const password = loginForm.querySelector('[name="password"]')?.value;
            const btn = loginForm.querySelector('button[type="submit"]');
            
            if (!email || !password) {
                showError('Email and password are required');
                return;
            }
            
            setLoading(btn, true);
            
            try {
                await login(email, password);
                showSuccess('Login successful! Redirecting...');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } catch (error) {
                console.error('[Firebase] Login error:', error);
                
                // Map Firebase error codes
                const errorMessages = {
                    'auth/user-not-found': 'No account found with this email.',
                    'auth/wrong-password': 'Incorrect password.',
                    'auth/invalid-email': 'Invalid email address.',
                    'auth/too-many-requests': 'Too many attempts. Try again later.',
                    'auth/invalid-credential': 'Invalid email or password.'
                };
                
                showError(errorMessages[error.code] || error.message || 'Login failed');
                setLoading(btn, false);
            }
        });
    }
    
    // Signup form handler
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = signupForm.querySelector('[name="email"]')?.value;
            const password = signupForm.querySelector('[name="password"]')?.value;
            const confirm = signupForm.querySelector('[name="confirm"]')?.value;
            const btn = signupForm.querySelector('button[type="submit"]');
            
            if (!email || !password) {
                showError('Email and password are required');
                return;
            }
            
            if (password !== confirm) {
                showError('Passwords do not match');
                return;
            }
            
            if (password.length < 6) {
                showError('Password must be at least 6 characters');
                return;
            }
            
            setLoading(btn, true);
            
            try {
                await signup(email, password);
                showSuccess('Account created! Redirecting...');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } catch (error) {
                console.error('[Firebase] Signup error:', error);
                
                const errorMessages = {
                    'auth/email-already-in-use': 'Email already in use.',
                    'auth/invalid-email': 'Invalid email address.',
                    'auth/weak-password': 'Password too weak.'
                };
                
                showError(errorMessages[error.code] || error.message || 'Signup failed');
                setLoading(btn, false);
            }
        });
    }
});

console.log('[Firebase] Login module loaded');
