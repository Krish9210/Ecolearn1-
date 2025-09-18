"""
EcoLearn Backend - Gamified Environmental Education Platform
Firebase Cloud Functions + Firestore Backend

Main entry point for the Flask API wrapped as Firebase Functions
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_functions import https_fn, options
from firebase_admin import initialize_app, get_app, credentials, firestore, auth
import logging

# Import our services
from services.auth_service import AuthService
from flask import Flask, send_file

from services.user_service import UserService
from services.quiz_service import QuizService
from services.badge_service import BadgeService
from services.leaderboard_service import LeaderboardService
from services.challenge_service import ChallengeService
from utils.auth_middleware import require_auth, get_user_from_token
from utils.error_handler import handle_error

# Initialize Firebase Admin SDK
try:
    # Try to get the default app
    app = get_app()
except (ValueError, ImportError) as e:
    # If the app doesn't exist, initialize it
    try:
        # For local development, use service account key
        cred_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            app = initialize_app(cred)
        else:
            # Use default credentials in production
            app = initialize_app()
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise

# Initialize Firestore client
db = firestore.client()

# Initialize Flask app
app = Flask(__name__)


CORS(app)

# Initialize services
auth_service = AuthService(db)
user_service = UserService(db)
quiz_service = QuizService(db)
badge_service = BadgeService(db)
leaderboard_service = LeaderboardService(db)
challenge_service = ChallengeService(db)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Local testing routes with /api prefix
@app.route("/api/")
def api_root():
    return "Ecolearn API root"

@app.route("/api/test")
def api_test():
    return {"message": "Test route working!"}


# Root route for browser testing
@app.route("/")
def home():
    return send_file("index.html")

# Example test route
@app.route("/test")
def test():
    return {"message": "Test route working!"}


# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ecolearn-backend',
        'version': '1.0.0'
    })

# ============= AUTH ENDPOINTS =============

@app.route('/auth/signup', methods=['POST'])
def signup():
    """Register a new user"""
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        # Normalize email casing to prevent duplicate vs not-found issues
        email = data.get('email', '').strip().lower()

        result = auth_service.create_user(
            email=email,
            password=data['password'],
            name=data.get('name', 'EcoWarrior'),
            avatar_url=data.get('avatarUrl', '')
        )
        
        return jsonify(result), 201
    except Exception as e:
        return handle_error(e)

@app.route('/auth/login', methods=['POST'])
def login():
    """Login user and return custom token"""
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        # Normalize email casing
        email = data.get('email', '').strip().lower()

        result = auth_service.login_user(email, data['password'])
        return jsonify(result)
    except Exception as e:
        return handle_error(e)

@app.route('/auth/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
            
        decoded_token = auth.verify_id_token(token)
        return jsonify({
            'valid': True,
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email', '')
        })
    except Exception as e:
        return handle_error(e)

# ============= USER ENDPOINTS =============

@app.route('/user/<user_id>', methods=['GET'])
@require_auth
def get_user_profile(user_id):
    """Get user profile with stats"""
    try:
        # Verify user can access this profile
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        if current_user['uid'] != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        profile = user_service.get_user_profile(user_id)
        return jsonify(profile)
    except Exception as e:
        return handle_error(e)

@app.route('/user/<user_id>', methods=['PUT'])
@require_auth
def update_user_profile(user_id):
    """Update user profile"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        if current_user['uid'] != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        data = request.get_json()
        result = user_service.update_user_profile(user_id, data)
        return jsonify(result)
    except Exception as e:
        return handle_error(e)

# ============= QUIZ ENDPOINTS =============

@app.route('/quizzes', methods=['GET'])
@require_auth
def get_quizzes():
    """Get all available quizzes"""
    try:
        quizzes = quiz_service.get_all_quizzes()
        return jsonify({'quizzes': quizzes})
    except Exception as e:
        return handle_error(e)

@app.route('/quiz/<quiz_id>', methods=['GET'])
@require_auth
def get_quiz(quiz_id):
    """Get specific quiz by ID"""
    try:
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        return jsonify(quiz)
    except Exception as e:
        return handle_error(e)

@app.route('/quiz/<quiz_id>/submit', methods=['POST'])
@require_auth
def submit_quiz(quiz_id):
    """Submit quiz answers and get results"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        data = request.get_json()
        
        if not data or 'answers' not in data:
            return jsonify({'error': 'Answers required'}), 400
            
        result = quiz_service.submit_quiz(
            user_id=current_user['uid'],
            quiz_id=quiz_id,
            answers=data['answers']
        )
        
        # Update user stats after quiz submission
        user_service.update_user_stats_after_quiz(current_user['uid'], result)
        
        return jsonify(result)
    except Exception as e:
        return handle_error(e)

@app.route('/quiz/<quiz_id>/attempts', methods=['GET'])
@require_auth
def get_quiz_attempts(quiz_id):
    """Get user's quiz attempts"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        attempts = quiz_service.get_user_quiz_attempts(current_user['uid'], quiz_id)
        return jsonify({'attempts': attempts})
    except Exception as e:
        return handle_error(e)

# ============= CHALLENGE ENDPOINTS =============

@app.route('/challenges', methods=['GET'])
@require_auth
def get_challenges():
    """Get all available challenges"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        challenges = challenge_service.get_user_challenges(current_user['uid'])
        return jsonify({'challenges': challenges})
    except Exception as e:
        return handle_error(e)

@app.route('/challenge/<challenge_id>/complete', methods=['POST'])
@require_auth
def complete_challenge(challenge_id):
    """Mark challenge as completed"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        data = request.get_json()
        
        result = challenge_service.complete_challenge(
            user_id=current_user['uid'],
            challenge_id=challenge_id,
            proof=data.get('proof', '')
        )
        
        # Update user stats after challenge completion
        user_service.update_user_stats_after_challenge(current_user['uid'], result)
        
        return jsonify(result)
    except Exception as e:
        return handle_error(e)

# ============= BADGE ENDPOINTS =============

@app.route('/badges', methods=['GET'])
@require_auth
def get_badges():
    """Get all available badges"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        badges = badge_service.get_user_badges(current_user['uid'])
        return jsonify({'badges': badges})
    except Exception as e:
        return handle_error(e)

@app.route('/badges/check', methods=['POST'])
@require_auth
def check_badge_eligibility():
    """Check and award eligible badges for user"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        newly_earned = badge_service.check_and_award_badges(current_user['uid'])
        return jsonify({
            'newly_earned': newly_earned,
            'count': len(newly_earned)
        })
    except Exception as e:
        return handle_error(e)

# ============= LEADERBOARD ENDPOINTS =============

@app.route('/leaderboard', methods=['GET'])
@require_auth
def get_leaderboard():
    """Get leaderboard data"""
    try:
        scope = request.args.get('scope', 'global')  # global, school, class
        period = request.args.get('period', 'all')   # weekly, monthly, all
        limit = int(request.args.get('limit', 50))
        
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        
        leaderboard = leaderboard_service.get_leaderboard(
            scope=scope,
            period=period,
            limit=limit,
            current_user_id=current_user['uid']
        )
        
        return jsonify(leaderboard)
    except Exception as e:
        return handle_error(e)

# ============= TEACHER ENDPOINTS =============

@app.route('/teacher/quiz', methods=['POST'])
@require_auth
def create_quiz():
    """Teacher creates a new quiz"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        # TODO: Add teacher role verification
        
        data = request.get_json()
        if not data or not data.get('title') or not data.get('questions'):
            return jsonify({'error': 'Title and questions required'}), 400
            
        quiz = quiz_service.create_quiz(
            created_by=current_user['uid'],
            title=data['title'],
            description=data.get('description', ''),
            difficulty=data.get('difficulty', 'medium'),
            questions=data['questions'],
            points_per_question=data.get('points_per_question', 10)
        )
        
        return jsonify(quiz), 201
    except Exception as e:
        return handle_error(e)

@app.route('/teacher/class-progress/<class_id>', methods=['GET'])
@require_auth
def get_class_progress(class_id):
    """Teacher gets class progress overview"""
    try:
        current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        # TODO: Add teacher role verification and class ownership check
        
        progress = user_service.get_class_progress(class_id)
        return jsonify(progress)
    except Exception as e:
        return handle_error(e)

# ============= ADMIN/SEED ENDPOINTS =============

@app.route('/admin/seed', methods=['POST'])
def seed_database():
    """Seed database with initial data (for development)"""
    try:
        # Only allow in development environment
        if os.environ.get('ENVIRONMENT') != 'development':
            return jsonify({'error': 'Not allowed in production'}), 403
            
        # Seed quizzes
        quiz_service.seed_quizzes()
        
        # Seed challenges
        challenge_service.seed_challenges()
        
        # Seed badges
        badge_service.seed_badges()
        
        return jsonify({
            'message': 'Database seeded successfully',
            'collections_seeded': ['quizzes', 'challenges', 'badges']
        })
    except Exception as e:
        return handle_error(e)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

# Firebase Cloud Function wrapper
@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins=["*"],
        cors_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
)
def api(req):
    """Main Cloud Function entry point"""
    with app.request_context(req.environ):
        return app.full_dispatch_request()

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)