# Firebase Setup Guide

This document explains how to set up Firebase Authentication and Firestore for the WALLS mental health application.

## Overview

WALLS uses Firebase for:
- **Authentication**: Email/password login via Firebase Auth
- **Data Storage**: User profiles, evaluations, and notes via Firestore

The application gracefully degrades when Firebase is not configured:
- Authentication falls back to mock login (any credentials work)
- Data storage falls back to local JSON files

## 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Enter a project name (e.g., "walls-mental-health")
4. Follow the setup wizard

## 2. Enable Authentication

1. In Firebase Console, go to **Authentication** → **Sign-in method**
2. Enable **Email/Password** provider
3. (Optional) Enable other providers as needed

## 3. Create Firestore Database

1. Go to **Firestore Database** → **Create database**
2. Start in **production mode** or **test mode** for development
3. Choose a location closest to your users

## 4. Get Service Account Credentials

1. Go to **Project Settings** → **Service Accounts**
2. Click **Generate new private key**
3. Save the JSON file securely (do NOT commit to git)

## 5. Configure Environment Variables

### Local Development

Create a `.env` file in the project root (copy from `env.example.txt`):

```env
# Flask Configuration
SECRET_KEY=your-secret-key
FLASK_ENV=development
FLASK_DEBUG=true

# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

**Important**: The private key must include the `\n` newline characters.

### Vercel Deployment

Add secrets using Vercel CLI:

```bash
vercel secrets add firebase_project_id "your-project-id"
vercel secrets add firebase_client_email "firebase-adminsdk-xxxxx@..."
vercel secrets add firebase_private_key "-----BEGIN PRIVATE KEY-----..."
vercel secrets add secret_key "your-secret-key"
```

## 6. Firestore Data Model

```
users/
├── {user_id}/                    # Firebase UID
│   ├── email: string
│   ├── created_at: timestamp
│   ├── last_login: timestamp
│   ├── display_name: string?
│   └── accessibility_prefs: map
│
├── {user_id}/evaluations/        # Subcollection
│   └── {eval_id}/
│       ├── timestamp: timestamp
│       ├── inputs: map           # Survey answers
│       ├── scores: map           # ML predictions
│       ├── prediction: string
│       ├── confidence: number
│       ├── probabilities: map
│       ├── classifications: map
│       ├── text_features: string
│       └── intensity_values: map
│
└── {user_id}/notes/              # Subcollection
    └── {note_id}/
        ├── text: string
        ├── tags: array
        ├── timestamp: timestamp
        └── updated_at: timestamp?
```

## 7. Security Rules

Add these rules in Firestore → **Rules**:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      
      // Subcollections inherit parent permissions
      match /evaluations/{evalId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
      
      match /notes/{noteId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
  }
}
```

## 8. Login Flow

### Frontend (login.html)

1. User enters email/password
2. Firebase JS SDK calls `signInWithEmailAndPassword()`
3. On success, get ID token: `user.getIdToken()`
4. POST token to `/auth/login`

### Backend (/auth/login)

1. Receive ID token
2. Verify with Firebase Admin SDK
3. Extract user claims (uid, email, etc.)
4. Create Flask session
5. Create/update user profile in Firestore

### Session Management

- Session stored in Flask's secure cookie
- Contains: `user_id`, `user_email`, `is_authenticated`
- Expires when browser closes (or configured timeout)

## 9. API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | Validate ID token, create session |
| `/auth/logout` | POST | Clear session |
| `/auth/status` | GET | Check authentication status |

### Evaluations (Firestore-backed)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/evaluations/` | GET | List user's evaluations |
| `/api/evaluations/<id>` | GET | Get single evaluation |
| `/api/evaluations/<id>` | DELETE | Delete evaluation |
| `/api/evaluations/metrics` | GET | Get computed metrics |
| `/api/evaluations/latest` | GET | Get most recent |

## 10. Development Without Firebase

If Firebase is not configured, the application uses fallback storage:

- **Auth**: Any email/password works (mock login)
- **Storage**: In-memory dictionary (lost on restart)
- **Files**: `user_data/{user_id}.json` for persistence

This allows development without Firebase credentials.

## 11. Troubleshooting

### "Firebase not available" message

Check that environment variables are set:
```bash
echo $FIREBASE_PROJECT_ID
```

### "Invalid token" on login

- Ensure Firebase Web SDK config matches project
- Check that Auth is enabled in Firebase Console
- Verify the private key format (newlines)

### Data not persisting

- Check Firestore security rules
- Verify user is authenticated
- Check browser console for errors

## 12. Testing

```bash
# Start the app
python app.py

# Test auth status
curl http://localhost:5000/auth/status

# Login (mock mode)
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"idToken": "mock_token", "email": "test@example.com"}'

# Get evaluations
curl http://localhost:5000/api/evaluations/ \
  -H "X-User-ID: mock_test_example_com"
```

