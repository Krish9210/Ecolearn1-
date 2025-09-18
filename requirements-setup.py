# requirements.txt
# Firebase and Google Cloud dependencies
firebase-admin>=6.2.0
firebase-functions>=0.1.0
google-cloud-firestore>=2.11.1
google-cloud-storage>=2.10.0

# Web framework
Flask>=2.3.2
Flask-CORS>=4.0.0

# Utilities
python-dateutil>=2.8.2
pytz>=2023.3
requests>=2.31.0

# Development dependencies
pytest>=7.4.0
pytest-mock>=3.11.1
python-dotenv>=1.0.0

# =============================================
# firebase.json - Firebase configuration
"""
{
  "functions": [
    {
      "source": ".",
      "codebase": "default",
      "ignore": [
        "node_modules",
        ".git",
        "firebase-debug.log",
        "firebase-debug.*.log",
        "*.pyc",
        "__pycache__",
        ".pytest_cache",
        "venv",
        ".env"
      ],
      "runtime": "python311"
    }
  ],
  "firestore": {
    "rules": "firestore.rules",
    "indexes": "firestore.indexes.json"
  },
  "emulators": {
    "functions": {
      "port": 5001
    },
    "firestore": {
      "port": 8080
    },
    "ui": {
      "enabled": true,
      "port": 4000
    }
  }
}
"""

# =============================================
# firestore.rules - Security rules
"""
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own profile
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      allow read: if request.auth != null; // Allow reading other users for leaderboards
    }
    
    // Quizzes are readable by authenticated users
    match /quizzes/{quizId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        resource.data.created_by == request.auth.uid;
    }
    
    // Quiz attempts are private to the user
    match /attempts/{attemptId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
      allow create: if request.auth != null && 
        request.resource.data.user_id == request.auth.uid;
    }
    
    // Badges are readable by all authenticated users
    match /badges/{badgeId} {
      allow read: if request.auth != null;
    }
    
    // User badges are readable by the user
    match /user_badges/{userBadgeId} {
      allow read: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
      allow create: if request.auth != null && 
        request.resource.data.user_id == request.auth.uid;
    }
    
    // Challenges are readable by authenticated users
    match /challenges/{challengeId} {
      allow read: if request.auth != null;
    }
    
    // User challenges are private to the user
    match /user_challenges/{userChallengeId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
      allow create: if request.auth != null && 
        request.resource.data.user_id == request.auth.uid;
    }
    
    // Leaderboards are readable by authenticated users
    match /leaderboards/{leaderboardId} {
      allow read: if request.auth != null;
    }
  }
}
"""

# =============================================
# firestore.indexes.json - Database indexes
"""
{
  "indexes": [
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "xp",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "level",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "attempts",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "attempts",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "quiz_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "user_challenges",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "completed_at",
          "order": "DESCENDING"
        }
      ]
    }
  ],
  "fieldOverrides": []
}
"""

# =============================================
# .env.example - Environment variables template
"""
# Firebase Configuration
GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey.json
FIREBASE_PROJECT_ID=ecolearn-platform
FIREBASE_WEB_API_KEY=your-web-api-key

# Environment
ENVIRONMENT=development
DEBUG=True

# API Configuration
API_VERSION=1.0.0
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Rate Limiting
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
"""

# =============================================
# deploy.py - Deployment script
"""
#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, check=True):
    \"\"\"Run a shell command\"\"\"
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, check=check)
    return result.returncode == 0

def deploy_functions():
    \"\"\"Deploy Firebase Cloud Functions\"\"\"
    print("🚀 Deploying EcoLearn Backend to Firebase...")
    
    # Check if Firebase CLI is installed
    if not run_command("firebase --version", check=False):
        print("❌ Firebase CLI not found. Please install it first:")
        print("npm install -g firebase-tools")
        sys.exit(1)
    
    # Check if logged in to Firebase
    if not run_command("firebase projects:list", check=False):
        print("❌ Not logged in to Firebase. Please run:")
        print("firebase login")
        sys.exit(1)
    
    # Install dependencies
    print("📦 Installing dependencies...")
    if not run_command("pip install -r requirements.txt"):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Run tests (optional)
    print("🧪 Running tests...")
    run_command("python -m pytest tests/", check=False)
    
    # Deploy functions
    print("🔥 Deploying to Firebase...")
    if run_command("firebase deploy --only functions"):
        print("✅ Deployment successful!")
        print("🌐 Your API is now live!")
    else:
        print("❌ Deployment failed")
        sys.exit(1)
    
    # Deploy Firestore rules and indexes
    print("📋 Deploying Firestore rules and indexes...")
    if run_command("firebase deploy --only firestore"):
        print("✅ Firestore rules deployed!")
    else:
        print("⚠️  Firestore rules deployment failed")

def setup_environment():
    \"\"\"Setup development environment\"\"\"
    print("🔧 Setting up development environment...")
    
    # Create .env from template if it doesn't exist
    if not Path(".env").exists() and Path(".env.example").exists():
        run_command("cp .env.example .env")
        print("📝 Created .env file from template")
        print("⚠️  Please update .env with your configuration")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    run_command("pip install -r requirements.txt")
    
    print("✅ Environment setup complete!")
    print("💡 Don't forget to:")
    print("   1. Update .env with your Firebase config")
    print("   2. Place serviceAccountKey.json in project root")
    print("   3. Run 'firebase login' if not already logged in")

def start_emulators():
    \"\"\"Start Firebase emulators for local development\"\"\"
    print("🔧 Starting Firebase emulators...")
    run_command("firebase emulators:start")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deploy.py setup    - Setup development environment")
        print("  python deploy.py deploy   - Deploy to Firebase")
        print("  python deploy.py emulator - Start local emulators")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "setup":
        setup_environment()
    elif action == "deploy":
        deploy_functions()
    elif action == "emulator":
        start_emulators()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
"""