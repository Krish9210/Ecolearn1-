"""
EcoLearn Backend - Comprehensive Test Suite
"""

# tests/conftest.py
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_firestore():
    """Mock Firestore database"""
    with patch('firebase_admin.firestore.client') as mock_client:
        mock_db = Mock()
        mock_client.return_value = mock_db
        yield mock_db

@pytest.fixture
def mock_auth():
    """Mock Firebase Auth"""
    with patch('firebase_admin.auth') as mock_auth:
        yield mock_auth

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        'id': 'test-user-id',
        'name': 'Test User',
        'email': 'test@example.com',
        'xp': 100,
        'level': 2,
        'points': 50,
        'badges': ['eco-starter'],
        'streak': 3,
        'total_quizzes_completed': 5,
        'total_challenges_completed': 2,
        'created_at': '2024-01-01T00:00:00Z'
    }

# =============================================
# tests/test_auth_service.py
import pytest
from unittest.mock import Mock, patch
from services.auth_service import AuthService

class TestAuthService:
    
    def test_create_user_success(self, mock_firestore, mock_auth):
        """Test successful user creation"""
        # Setup mocks
        mock_auth.create_user.return_value = Mock(uid='new-user-id')
        mock_auth.create_custom_token.return_value = b'custom-token'
        
        auth_service = AuthService(mock_firestore)
        
        result = auth_service.create_user(
            email='new@example.com',
            password='password123',
            name='New User'
        )
        
        assert result['success'] is True
        assert result['user_id'] == 'new-user-id'
        assert result['email'] == 'new@example.com'
        assert 'custom_token' in result
        
        # Verify user document was created
        mock_firestore.collection.assert_called_with('users')
    
    def test_create_user_duplicate_email(self, mock_firestore, mock_auth):
        """Test user creation with duplicate email"""
        from firebase_admin import auth as firebase_auth
        mock_auth.create_user.side_effect = firebase_auth.EmailAlreadyExistsError('Email exists')
        
        auth_service = AuthService(mock_firestore)
        
        with pytest.raises(ValueError, match='Email already exists'):
            auth_service.create_user('existing@example.com', 'password123')
    
    def test_login_user_success(self, mock_firestore, mock_auth):
        """Test successful user login"""
        # Setup mocks
        mock_user_record = Mock(uid='test-user-id')
        mock_auth.get_user_by_email.return_value = mock_user_record
        mock_auth.create_custom_token.return_value = b'login-token'
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {'name': 'Test User', 'xp': 100}
        mock_firestore.collection().document().get.return_value = mock_doc
        
        auth_service = AuthService(mock_firestore)
        
        result = auth_service.login_user('test@example.com', 'password123')
        
        assert result['success'] is True
        assert result['user_id'] == 'test-user-id'
        assert 'custom_token' in result

# =============================================
# tests/test_quiz_service.py
import pytest
from unittest.mock import Mock
from services.quiz_service import QuizService

class TestQuizService:
    
    def test_get_all_quizzes(self, mock_firestore):
        """Test getting all quizzes"""
        # Mock quiz data
        mock_quiz_doc = Mock()
        mock_quiz_doc.id = 'quiz-1'
        mock_quiz_doc.to_dict.return_value = {
            'title': 'Test Quiz',
            'description': 'Test Description',
            'difficulty': 'easy',
            'questions': [
                {
                    'id': 'q1',
                    'question': 'Test question?',
                    'options': ['A', 'B', 'C', 'D'],
                    'correct': 0,
                    'explanation': 'Test explanation'
                }
            ],
            'status': 'active',
            'points_per_question': 10
        }
        
        mock_firestore.collection().where().stream.return_value = [mock_quiz_doc]
        
        quiz_service = QuizService(mock_firestore)
        result = quiz_service.get_all_quizzes()
        
        assert len(result) == 1
        assert result[0]['id'] == 'quiz-1'
        assert result[0]['title'] == 'Test Quiz'
        assert 'correct' not in result[0]['questions'][0]  # Should be sanitized
    
    def test_submit_quiz(self, mock_firestore):
        """Test quiz submission and grading"""
        # Mock quiz document
        mock_quiz_doc = Mock()
        mock_quiz_doc.exists = True
        mock_quiz_doc.to_dict.return_value = {
            'title': 'Test Quiz',
            'questions': [
                {
                    'id': 'q1',
                    'question': 'Test question?',
                    'correct': 0,
                    'explanation': 'Correct answer explanation'
                }
            ],
            'points_per_question': 10
        }
        
        mock_firestore.collection().document().get.return_value = mock_quiz_doc
        
        quiz_service = QuizService(mock_firestore)
        
        result = quiz_service.submit_quiz(
            user_id='test-user',
            quiz_id='quiz-1',
            answers={'q1': 0}  # Correct answer
        )
        
        assert result['score'] == 1
        assert result['score_percentage'] == 100.0
        assert result['earned_xp'] > 0
        assert result['question_results'][0]['is_correct'] is True

# =============================================
# tests/test_user_service.py
import pytest
from unittest.mock import Mock
from services.user_service import UserService

class TestUserService:
    
    def test_calculate_level_from_xp(self, mock_firestore):
        """Test XP to level calculation"""
        user_service = UserService(mock_firestore)
        
        assert user_service._calculate_level_from_xp(0) == 1
        assert user_service._calculate_level_from_xp(100) == 2
        assert user_service._calculate_level_from_xp(400) == 3
        assert user_service._calculate_level_from_xp(900) == 4
    
    def test_calculate_xp_for_level(self, mock_firestore):
        """Test level to XP requirement calculation"""
        user_service = UserService(mock_firestore)
        
        assert user_service._calculate_xp_for_level(1) == 0
        assert user_service._calculate_xp_for_level(2) == 100
        assert user_service._calculate_xp_for_level(3) == 400
        assert user_service._calculate_xp_for_level(4) == 900
    
    def test_update_user_stats_after_quiz(self, mock_firestore, sample_user_data):
        """Test user stats update after quiz completion"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_user_data
        mock_firestore.collection().document().get.return_value = mock_doc
        
        user_service = UserService(mock_firestore)
        
        quiz_result = {
            'earned_xp': 50,
            'score': 5
        }
        
        result = user_service.update_user_stats_after_quiz('test-user', quiz_result)
        
        assert result['xp_gained'] == 50
        assert result['new_xp'] == 150  # 100 + 50
        assert result['new_level'] >= 2

# =============================================
# tests/test_badge_service.py
import pytest
from unittest.mock import Mock
from services.badge_service import BadgeService

class TestBadgeService:
    
    def test_check_badge_criteria_xp_threshold(self, mock_firestore):
        """Test XP threshold badge criteria"""
        badge_service = BadgeService(mock_firestore)
        
        badge = {
            'criteria': {
                'type': 'xp_threshold',
                'xp_required': 100
            }
        }
        
        user_data = {'xp': 150}
        
        result = badge_service._check_badge_criteria('test-user', badge, user_data)
        assert result is True
        
        user_data = {'xp': 50}
        result = badge_service._check_badge_criteria('test-user', badge, user_data)
        assert result is False
    
    def test_check_badge_criteria_quiz_completion(self, mock_firestore):
        """Test quiz completion badge criteria"""
        badge_service = BadgeService(mock_firestore)
        
        badge = {
            'criteria': {
                'type': 'quiz_completion',
                'quizzes_required': 5
            }
        }
        
        user_data = {'total_quizzes_completed': 10}
        result = badge_service._check_badge_criteria('test-user', badge, user_data)
        assert result is True
        
        user_data = {'total_quizzes_completed': 3}
        result = badge_service._check_badge_criteria('test-user', badge, user_data)
        assert result is False

# =============================================
# tests/test_challenge_service.py
import pytest
from unittest.mock import Mock
from services.challenge_service import ChallengeService

class TestChallengeService:
    
    def test_get_difficulty_multiplier(self, mock_firestore):
        """Test difficulty multiplier calculation"""
        challenge_service = ChallengeService(mock_firestore)
        
        assert challenge_service._get_difficulty_multiplier('easy') == 1.0
        assert challenge_service._get_difficulty_multiplier('medium') == 1.2
        assert challenge_service._get_difficulty_multiplier('hard') == 1.5
        assert challenge_service._get_difficulty_multiplier('expert') == 2.0
    
    def test_complete_challenge(self, mock_firestore):
        """Test challenge completion"""
        # Mock challenge document
        mock_challenge_doc = Mock()
        mock_challenge_doc.exists = True
        mock_challenge_doc.to_dict.return_value = {
            'title': 'Test Challenge',
            'difficulty': 'medium',
            'xp_reward': 50,
            'points_reward': 25,
            'type': 'one-time'
        }
        
        mock_firestore.collection().document().get.return_value = mock_challenge_doc
        mock_firestore.collection().where().where().limit().stream.return_value = []
        
        challenge_service = ChallengeService(mock_firestore)
        
        result = challenge_service.complete_challenge(
            user_id='test-user',
            challenge_id='challenge-1',
            proof='Completed the challenge'
        )
        
        assert result['challenge_id'] == 'challenge-1'
        assert result['xp_reward'] == 60  # 50 * 1.2 multiplier
        assert result['points_reward'] == 30  # 25 * 1.2 multiplier

# =============================================
# tests/test_api_endpoints.py
import pytest
from unittest.mock import Mock, patch
import json
from main import app

@pytest.fixture
def client():
    """Test client for Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestAPIEndpoints:
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    @patch('firebase_admin.auth.verify_id_token')
    def test_get_user_profile_success(self, mock_verify_token, client):
        """Test get user profile endpoint"""
        mock_verify_token.return_value = {'uid': 'test-user-id'}
        
        with patch('services.user_service.UserService.get_user_profile') as mock_get_profile:
            mock_get_profile.return_value = {
                'id': 'test-user-id',
                'name': 'Test User',
                'xp': 100
            }
            
            response = client.get(
                '/user/test-user-id',
                headers={'Authorization': 'Bearer fake-token'}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['name'] == 'Test User'
    
    def test_get_user_profile_unauthorized(self, client):
        """Test get user profile without authorization"""
        response = client.get('/user/test-user-id')
        assert response.status_code == 401

# =============================================
# tests/test_integration.py
import pytest
from unittest.mock import Mock, patch

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @patch('firebase_admin.firestore.client')
    @patch('firebase_admin.auth')
    def test_complete_quiz_workflow(self, mock_auth, mock_firestore):
        """Test complete quiz submission workflow"""
        from services.quiz_service import QuizService
        from services.user_service import UserService
        
        # Mock quiz data
        mock_quiz_doc = Mock()
        mock_quiz_doc.exists = True
        mock_quiz_doc.to_dict.return_value = {
            'title': 'Integration Test Quiz',
            'questions': [
                {
                    'id': 'q1',
                    'question': 'Test question?',
                    'correct': 0,
                    'explanation': 'Test explanation'
                }
            ],
            'points_per_question': 10
        }
        
        # Mock user data
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            'xp': 100,
            'level': 2,
            'points': 50,
            'badges': []
        }
        
        mock_db = Mock()
        mock_db.collection().document().get.return_value = mock_quiz_doc
        mock_firestore.return_value = mock_db
        
        # Test workflow
        quiz_service = QuizService(mock_db)
        user_service = UserService(mock_db)
        
        # 1. Submit quiz
        quiz_result = quiz_service.submit_quiz(
            user_id='test-user',
            quiz_id='test-quiz',
            answers={'q1': 0}
        )
        
        assert quiz_result['score_percentage'] == 100.0
        
        # 2. Update user stats
        mock_db.collection().document().get.return_value = mock_user_doc
        
        user_update = user_service.update_user_stats_after_quiz(
            'test-user',
            quiz_result
        )
        
        assert user_update['xp_gained'] > 0

# =============================================
# Additional Test Utilities
import unittest
from unittest.mock import patch

class MockFirestoreCollection:
    """Mock Firestore collection for testing"""
    
    def __init__(self, data=None):
        self.data = data or {}
        self.documents = {}
    
    def document(self, doc_id):
        return MockFirestoreDocument(doc_id, self.documents.get(doc_id, {}))
    
    def where(self, field, operator, value):
        return MockFirestoreQuery(self.data, field, operator, value)
    
    def stream(self):
        for doc_id, doc_data in self.documents.items():
            doc = MockFirestoreDocument(doc_id, doc_data)
            yield doc

class MockFirestoreDocument:
    """Mock Firestore document"""
    
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
        self.exists = bool(data)
    
    def get(self):
        return self
    
    def to_dict(self):
        return self._data
    
    def set(self, data):
        self._data = data
        self.exists = True
    
    def update(self, data):
        self._data.update(data)

class MockFirestoreQuery:
    """Mock Firestore query"""
    
    def __init__(self, data, field, operator, value):
        self.data = data
        self.field = field
        self.operator = operator
        self.value = value
    
    def where(self, field, operator, value):
        return MockFirestoreQuery(self.data, field, operator, value)
    
    def limit(self, count):
        return self
    
    def order_by(self, field, direction='ASCENDING'):
        return self
    
    def stream(self):
        # Simple mock implementation
        return []

# =============================================
# pytest.ini configuration
pytest_ini_content = """
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v 
    --tb=short 
    --strict-markers
    --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Tests that take longer to run
"""

# =============================================
# Run tests script
run_tests_script = """
#!/usr/bin/env python3
import subprocess
import sys

def run_tests():
    \"\"\"Run the complete test suite\"\"\"
    print("🧪 Running EcoLearn Backend Tests...")
    
    # Run unit tests
    print("Running unit tests...")
    result = subprocess.run([
        'python', '-m', 'pytest', 
        'tests/', 
        '-v',
        '--tb=short'
    ])
    
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
"""

print("✅ EcoLearn Backend Development Complete!")
print("""
FINAL PROJECT STRUCTURE:
📁 ecolearn-backend/
├── main.py                    # Main Flask app & Cloud Functions entry
├── requirements.txt           # Python dependencies
├── firebase.json             # Firebase configuration
├── firestore.rules          # Database security rules
├── firestore.indexes.json   # Database indexes
├── .env.example             # Environment variables template
├── deploy.py                # Deployment script
├── services/
│   ├── auth_service.py      # Authentication logic
│   ├── user_service.py      # User management & XP system
│   ├── quiz_service.py      # Quiz management & grading
│   ├── badge_service.py     # Badge system
│   ├── challenge_service.py # Eco-challenges
│   └── leaderboard_service.py # Rankings & leaderboards
├── utils/
│   ├── auth_middleware.py   # Authentication middleware
│   └── error_handler.py     # Error handling utilities
└── tests/
    ├── conftest.py          # Test configuration
    ├── test_auth_service.py # Authentication tests
    ├── test_quiz_service.py # Quiz functionality tests
    ├── test_user_service.py # User management tests
    └── test_integration.py  # Integration tests

DEPLOYMENT STEPS:
1. pip install -r requirements.txt
2. firebase login
3. python deploy.py setup
4. Update .env with your Firebase config
5. python deploy.py deploy
6. POST /admin/seed to populate initial data

API FEATURES:
✅ Firebase Authentication integration
✅ User profiles with XP/level progression  
✅ Quiz system with auto-grading
✅ Badge system with dynamic criteria checking
✅ Real-world eco-challenges
✅ Global/scoped leaderboards
✅ Teacher quiz creation tools
✅ Comprehensive error handling
✅ Rate limiting & security
✅ Full test suite
✅ Production-ready deployment config
""")
