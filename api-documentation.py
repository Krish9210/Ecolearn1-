"""
EcoLearn Platform API Documentation
Complete REST API reference with examples

Base URL: https://your-project.cloudfunctions.net/api
         or http://localhost:5001/your-project/us-central1/api (development)

Authentication: Bearer <Firebase_ID_Token>
Content-Type: application/json
"""

# =============================================
# AUTHENTICATION ENDPOINTS
# =============================================

"""
1. POST /auth/signup
   Create a new user account

   Request Body:
   {
     "email": "user@example.com",
     "password": "securePassword123",
     "name": "Eco Warrior",
     "avatarUrl": "https://example.com/avatar.jpg"
   }

   Response (201):
   {
     "success": true,
     "user_id": "firebase-uid",
     "email": "user@example.com",
     "name": "Eco Warrior",
     "custom_token": "firebase-custom-token",
     "message": "User created successfully"
   }

   Errors:
   400: Missing email/password
   409: Email already exists
"""

"""
2. POST /auth/login
   Login existing user

   Request Body:
   {
     "email": "user@example.com",
     "password": "securePassword123"
   }

   Response (200):
   {
     "success": true,
     "user_id": "firebase-uid",
     "email": "user@example.com",
     "name": "Eco Warrior",
     "custom_token": "firebase-custom-token",
     "profile": {
       "xp": 150,
       "level": 2,
       "points": 75,
       "badges": ["eco-starter", "quiz-master"],
       "streak": 5
     }
   }
"""

# =============================================
# USER ENDPOINTS
# =============================================

"""
3. GET /user/{user_id}
   Get user profile and stats

   Headers:
   Authorization: Bearer <firebase-id-token>

   Response (200):
   {
     "id": "firebase-uid",
     "name": "Eco Warrior",
     "email": "user@example.com",
     "xp": 150,
     "level": 2,
     "points": 75,
     "badges": ["eco-starter", "quiz-master"],
     "streak": 5,
     "total_quizzes_completed": 8,
     "total_challenges_completed": 3,
     "level_progress": {
       "current_level": 2,
       "current_xp": 150,
       "xp_for_next_level": 400,
       "progress_percentage": 37.5
     },
     "recent_stats": {
       "quizzes_this_week": 3,
       "average_score_this_week": 85.5,
       "xp_earned_this_week": 45
     }
   }
"""

"""
4. PUT /user/{user_id}
   Update user profile

   Headers:
   Authorization: Bearer <firebase-id-token>

   Request Body:
   {
     "name": "Updated Name",
     "avatar_url": "https://example.com/new-avatar.jpg",
     "bio": "Environmental enthusiast"
   }

   Response (200):
   {
     "success": true,
     "updated_fields": ["name", "avatar_url", "bio"],
     "message": "Profile updated successfully"
   }
"""

# =============================================
# QUIZ ENDPOINTS
# =============================================

"""
5. GET /quizzes
   Get all available quizzes

   Headers:
   Authorization: Bearer <firebase-id-token>

   Response (200):
   {
     "quizzes": [
       {
         "id": "quiz-id-1",
         "title": "Environmental Basics",
         "description": "Test your knowledge of basic environmental concepts",
         "difficulty": "easy",
         "total_questions": 5,
         "points_per_question": 10,
         "questions": [
           {
             "id": "q1",
             "question": "What percentage of plastic waste is recycled globally?",
             "options": ["Less than 10%", "About 25%", "About 50%", "Over 75%"],
             "difficulty": "medium",
             "category": "waste"
           }
         ]
       }
     ]
   }
"""

"""
6. GET /quiz/{quiz_id}
   Get specific quiz details

   Response (200):
   {
     "id": "quiz-id-1",
     "title": "Environmental Basics",
     "description": "Test your knowledge of basic environmental concepts",
     "difficulty": "easy",
     "total_questions": 5,
     "points_per_question": 10,
     "questions": [...]
   }
"""

"""
7. POST /quiz/{quiz_id}/submit
   Submit quiz answers

   Headers:
   Authorization: Bearer <firebase-id-token>

   Request Body:
   {
     "answers": {
       "q1": 0,
       "q2": 2,
       "q3": 1
     },
     "time_taken_seconds": 180
   }

   Response (200):
   {
     "attempt_id": "attempt-uuid",
     "score": 4,
     "total_questions": 5,
     "score_percentage": 80,
     "earned_xp": 50,
     "base_xp": 40,
     "bonus_xp": 10,
     "question_results": [
       {
         "question_id": "q1",
         "question": "What percentage of plastic waste is recycled globally?",
         "correct_answer": 0,
         "user_answer": 0,
         "is_correct": true,
         "explanation": "Less than 10% of plastic waste is actually recycled globally.",
         "points_earned": 10
       }
     ],
     "quiz_completed": true
   }
"""

# =============================================
# CHALLENGE ENDPOINTS
# =============================================

"""
8. GET /challenges
   Get all challenges with user's completion status

   Headers:
   Authorization: Bearer <firebase-id-token>

   Response (200):
   {
     "challenges": [
       {
         "id": "challenge-1",
         "title": "Plant a Tree 🌱",
         "description": "Plant a tree or donate to a tree-planting organization",
         "category": "environmental",
         "difficulty": "medium",
         "xp_reward": 50,
         "points_reward": 25,
         "completed": false,
         "completion_data": null
       }
     ],
     "completed_count": 2,
     "available_count": 6,
     "total_count": 8
   }
"""

"""
9. POST /challenge/{challenge_id}/complete
   Mark challenge as completed

   Headers:
   Authorization: Bearer <firebase-id-token>

   Request Body:
   {
     "proof": "I planted an oak tree in my backyard"
   }

   Response (200):
   {
     "challenge_id": "challenge-1",
     "challenge_title": "Plant a Tree 🌱",
     "xp_reward": 50,
     "points_reward": 25,
     "difficulty_multiplier": 1.2,
     "completion_message": "Great job reducing waste! Every action counts towards a cleaner planet.",
     "next_suggested_challenges": [
       {
         "id": "challenge-2",
         "title": "Water Conservation",
         "difficulty": "easy",
         "xp_reward": 30
       }
     ]
   }
"""

# =============================================
# BADGE ENDPOINTS
# =============================================

"""
10. GET /badges
    Get all badges with user's earned status

    Headers:
    Authorization: Bearer <firebase-id-token>

    Response (200):
    {
      "all_badges": [
        {
          "id": "eco-starter",
          "name": "Eco Starter",
          "description": "Complete your first quiz",
          "icon_url": "🌱",
          "category": "beginner",
          "earned": true,
          "earned_at": "2024-01-15T10:30:00Z"
        }
      ],
      "earned_badges": [...],
      "available_badges": [...],
      "total_badges": 9,
      "earned_count": 3
    }
"""

"""
11. POST /badges/check
    Check and award eligible badges

    Headers:
    Authorization: Bearer <firebase-id-token>

    Response (200):
    {
      "newly_earned": [
        {
          "id": "quiz-master",
          "name": "Quiz Master",
          "description": "Score 100% on a quiz",
          "icon_url": "🧠"
        }
      ],
      "count": 1
    }
"""

# =============================================
# LEADERBOARD ENDPOINTS
# =============================================

"""
12. GET /leaderboard?scope=global&period=weekly&limit=50
    Get leaderboard data

    Headers:
    Authorization: Bearer <firebase-id-token>

    Query Parameters:
    - scope: global|school|class (default: global)
    - period: all|weekly|monthly|daily (default: all)
    - limit: number of entries (default: 50, max: 100)

    Response (200):
    {
      "scope": "global",
      "period": "weekly",
      "entries": [
        {
          "rank": 1,
          "user_id": "firebase-uid-1",
          "name": "GreenThumb99",
          "xp": 1250,
          "level": 8,
          "badges": 6,
          "avatar_url": "",
          "streak": 15
        }
      ],
      "current_user": {
        "rank": 23,
        "data": {
          "rank": 23,
          "user_id": "current-user-id",
          "name": "Your Name",
          "xp": 150,
          "level": 2,
          "badges": 3
        }
      },
      "total_entries": 50,
      "updated_at": "2024-01-15T12:00:00Z"
    }
"""

# =============================================
# TEACHER ENDPOINTS
# =============================================

"""
13. POST /teacher/quiz
    Create a new quiz (teacher/admin only)

    Headers:
    Authorization: Bearer <firebase-id-token>

    Request Body:
    {
      "title": "Advanced Climate Science",
      "description": "Test advanced knowledge of climate change",
      "difficulty": "hard",
      "points_per_question": 15,
      "questions": [
        {
          "question": "What is the current atmospheric CO2 concentration?",
          "options": ["350 ppm", "400 ppm", "420 ppm", "450 ppm"],
          "correct": 2,
          "explanation": "As of 2024, atmospheric CO2 levels have exceeded 420 parts per million.",
          "difficulty": "hard",
          "category": "climate"
        }
      ]
    }

    Response (201):
    {
      "quiz_id": "new-quiz-id",
      "title": "Advanced Climate Science",
      "total_questions": 1,
      "message": "Quiz created successfully"
    }
"""

# =============================================
# ADMIN/SEED ENDPOINTS
# =============================================

"""
14. POST /admin/seed
    Seed database with initial data (development only)

    Request Body: {} (empty)

    Response (200):
    {
      "message": "Database seeded successfully",
      "collections_seeded": ["quizzes", "challenges", "badges"]
    }

    Note: Only works when ENVIRONMENT=development
"""

# =============================================
# ERROR RESPONSES
# =============================================

"""
Standard Error Response Format:
{
  "error": "Error message description",
  "error_code": "ERROR_CODE",
  "status": "error"
}

Common Error Codes:
- VALIDATION_ERROR (400): Invalid input data
- AUTH_ERROR (401): Authentication failed
- PERMISSION_ERROR (403): Insufficient permissions
- NOT_FOUND (404): Resource not found
- SERVICE_ERROR (503): External service unavailable
- INTERNAL_ERROR (500): Unexpected server error
"""

# =============================================
# JAVASCRIPT FETCH EXAMPLES
# =============================================

javascript_examples = """
// Authentication
const signUp = async (email, password, name) => {
  const response = await fetch('/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name })
  });
  return response.json();
};

// Get user profile
const getUserProfile = async (userId, token) => {
  const response = await fetch(`/user/${userId}`, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
};

// Submit quiz
const submitQuiz = async (quizId, answers, token) => {
  const response = await fetch(`/quiz/${quizId}/submit`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ answers })
  });
  return response.json();
};

// Complete challenge
const completeChallenge = async (challengeId, proof, token) => {
  const response = await fetch(`/challenge/${challengeId}/complete`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ proof })
  });
  return response.json();
};

// Get leaderboard
const getLeaderboard = async (scope = 'global', period = 'all', token) => {
  const response = await fetch(`/leaderboard?scope=${scope}&period=${period}`, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
};
"""

# =============================================
# DEPLOYMENT INSTRUCTIONS
# =============================================

deployment_instructions = """
DEPLOYMENT INSTRUCTIONS

1. Prerequisites:
   - Python 3.11+
   - Firebase CLI: npm install -g firebase-tools
   - Firebase project with Authentication, Firestore enabled

2. Setup:
   - Clone repository
   - Run: python deploy.py setup
   - Update .env with your Firebase configuration
   - Add serviceAccountKey.json to project root

3. Local Development:
   - Run: python deploy.py emulator
   - API available at: http://localhost:5001/your-project/us-central1/api

4. Deployment:
   - Run: firebase login
   - Run: python deploy.py deploy
   - API available at: https://your-project.cloudfunctions.net/api

5. Database Seeding:
   - POST to /admin/seed with ENVIRONMENT=development
   - This creates sample quizzes, challenges, and badges

6. Frontend Integration:
   - Update HTML file to use deployed API endpoints
   - Replace fetch calls with your Cloud Function URLs
   - Implement Firebase Authentication in frontend

7. Monitoring:
   - Check Firebase Console for function logs
   - Monitor Firestore usage and billing
   - Set up alerting for errors and rate limits
"""