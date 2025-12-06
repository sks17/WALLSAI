/**
 * Firebase Initialization Module
 * 
 * Initializes Firebase app and auth, exports shared instances.
 * Tracks auth state and exposes USER_UID globally.
 * 
 * Usage:
 *   import { auth, app } from "./firebase-init.js";
 */

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { 
    getAuth, 
    onAuthStateChanged,
    signOut as firebaseSignOut
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// Firebase configuration from environment (injected by Flask template)
const firebaseConfig = {
    apiKey: window.ENV_FIREBASE_API_KEY || window._FIREBASE_API_KEY,
    authDomain: window.ENV_FIREBASE_AUTH_DOMAIN || window._FIREBASE_AUTH_DOMAIN,
    projectId: window.ENV_FIREBASE_PROJECT_ID || window._FIREBASE_PROJECT_ID,
    storageBucket: window.ENV_FIREBASE_STORAGE_BUCKET || window._FIREBASE_STORAGE_BUCKET,
    messagingSenderId: window.ENV_FIREBASE_MESSAGING_SENDER_ID || window._FIREBASE_MESSAGING_SENDER_ID,
    appId: window.ENV_FIREBASE_APP_ID || window._FIREBASE_APP_ID
};

// Check if Firebase is configured
const isConfigured = Boolean(
    firebaseConfig.apiKey && 
    firebaseConfig.apiKey !== 'None' && 
    firebaseConfig.apiKey !== ''
);

// Initialize Firebase app and auth
let app = null;
let auth = null;

if (isConfigured) {
    try {
        app = initializeApp(firebaseConfig);
        auth = getAuth(app);
        console.log('[Firebase] Initialized with project:', firebaseConfig.projectId);
    } catch (error) {
        console.error('[Firebase] Initialization failed:', error);
    }
} else {
    console.log('[Firebase] Not configured, using mock mode');
}

// Global user ID (null if not logged in)
window.USER_UID = null;
window.USER_EMAIL = null;
window.USER_DISPLAY_NAME = null;

// Auth state listener
if (auth) {
    onAuthStateChanged(auth, (user) => {
        if (user) {
            window.USER_UID = user.uid;
            window.USER_EMAIL = user.email;
            window.USER_DISPLAY_NAME = user.displayName;
            
            console.log('[Firebase] User signed in:', user.uid);
            
            // Dispatch custom event for other modules
            window.dispatchEvent(new CustomEvent('firebase-auth-change', { 
                detail: { user, signedIn: true } 
            }));
            
            // Initialize user profile in Firestore
            initUserProfile(user);
        } else {
            window.USER_UID = null;
            window.USER_EMAIL = null;
            window.USER_DISPLAY_NAME = null;
            
            console.log('[Firebase] User signed out');
            
            window.dispatchEvent(new CustomEvent('firebase-auth-change', { 
                detail: { user: null, signedIn: false } 
            }));
        }
    });
}

/**
 * Initialize user profile in Firestore after login
 */
async function initUserProfile(user) {
    try {
        const response = await fetch('/api/user/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                uid: user.uid,
                email: user.email,
                displayName: user.displayName
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('[Firebase] User profile initialized:', data.new ? 'new' : 'existing');
        }
    } catch (error) {
        console.warn('[Firebase] Failed to init user profile:', error);
    }
}

/**
 * Get current user
 */
function getCurrentUser() {
    return auth?.currentUser || null;
}

/**
 * Get current user ID
 */
function getCurrentUID() {
    return window.USER_UID || auth?.currentUser?.uid || null;
}

/**
 * Check if user is signed in
 */
function isSignedIn() {
    return window.USER_UID !== null;
}

/**
 * Sign out
 */
async function signOut() {
    if (auth) {
        await firebaseSignOut(auth);
    }
    
    // Also clear backend session
    try {
        await fetch('/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (e) {
        console.warn('[Firebase] Backend logout failed:', e);
    }
    
    window.USER_UID = null;
    window.USER_EMAIL = null;
    window.USER_DISPLAY_NAME = null;
}

/**
 * Wait for auth to be ready
 */
function waitForAuth() {
    return new Promise((resolve) => {
        if (window.USER_UID !== null) {
            resolve(window.USER_UID);
            return;
        }
        
        if (!auth) {
            resolve(null);
            return;
        }
        
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            unsubscribe();
            resolve(user?.uid || null);
        });
    });
}

// Export for ES modules
export { 
    app, 
    auth, 
    isConfigured,
    getCurrentUser,
    getCurrentUID,
    isSignedIn,
    signOut,
    waitForAuth
};

// Also expose on window for non-module scripts
window.FirebaseApp = {
    app,
    auth,
    isConfigured,
    getCurrentUser,
    getCurrentUID,
    isSignedIn,
    signOut,
    waitForAuth
};

console.log('[Firebase] Init module loaded, configured:', isConfigured);

