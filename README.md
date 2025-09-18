<<<<<<< HEAD
# EcoLearn - Gamified Environmental Education Platform

A Firebase Cloud Functions backend for an environmental education platform with gamification elements.

## Prerequisites

1. Python 3.7+
2. Firebase account and project
3. Firebase CLI (for deployment)
4. Google Cloud SDK (for local development)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd project-directory
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Firebase**
   - Create a new Firebase project at [Firebase Console](https://console.firebase.google.com/)
   - Download the service account key (serviceAccountKey.json) and place it in the project root
   - Enable Firestore and Authentication in your Firebase project

5. **Environment Variables**
   Create a `.env` file in the project root with the following content:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey.json
   ```

## Running Locally

1. Start the local development server:
   ```bash
   python ecolearn-main.py
   ```

2. The API will be available at `http://localhost:8080`

## API Endpoints

- `GET /health` - Health check
- `POST /auth/signup` - User registration
- `POST /auth/login` - User login
- `POST /auth/verify` - Verify authentication token
- `GET /user/{user_id}` - Get user profile
- `GET /quizzes` - List all quizzes
- `GET /quiz/{quiz_id}` - Get specific quiz
- `POST /quiz/{quiz_id}/submit` - Submit quiz answers
- And more...

## Project Structure

- `ecolearn-main.py` - Main application entry point
- `services/` - Business logic modules
  - `auth_service.py` - Authentication and user management
  - `user_service.py` - User profile and statistics
  - `quiz_service.py` - Quiz management and submission
  - `badge_service.py` - Badge and achievement system
  - `leaderboard_service.py` - Leaderboard functionality
  - `challenge_service.py` - Environmental challenges
- `utils/` - Utility modules
  - `auth_middleware.py` - Authentication middleware
  - `error_handler.py` - Error handling utilities

## Testing

Run the test suite with:
```bash
pytest test-suite.py
```

## Deployment

1. Install Firebase CLI:
   ```bash
   npm install -g firebase-tools
   ```

2. Login to Firebase:
   ```bash
   firebase login
   ```

3. Deploy the functions:
   ```bash
   firebase deploy --only functions
   ```

## License

This project is licensed under the MIT License.
=======
# Ecolearn
>>>>>>> 2f28c90c19cced661fbb1e5c26a8ba4d5e5fb5ad
