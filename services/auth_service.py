"""
Authentication Service for EcoLearn Platform
Handles user registration, login, and Firebase Auth integration
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from firebase_admin import auth, firestore
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db):
        self.db = db
        self.users_ref = db.collection('users')
    
    def create_user(self, email, password, name="EcoWarrior", avatar_url=""):
        """
        Create a new user account with Firebase Auth and Firestore profile
        """
        try:
            # Create user in Firebase Auth
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )
            
            # Create user profile in Firestore
            user_data = {
                'id': user_record.uid,
                'name': name,
                'email': email,
                'avatar_url': avatar_url,
                'xp': 0,
                'level': 1,
                'points': 0,
                'badges': [],
                'streak': 0,
                'total_quizzes_completed': 0,
                'total_challenges_completed': 0,
                'current_streak_days': 0,
                'last_active_date': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Save to Firestore
            self.users_ref.document(user_record.uid).set(user_data)
            
            # Generate custom token for immediate login
            custom_token = auth.create_custom_token(user_record.uid)
            
            logger.info(f"Created new user: {email} with ID: {user_record.uid}")
            
            return {
                'success': True,
                'user_id': user_record.uid,
                'email': email,
                'name': name,
                'custom_token': custom_token.decode('utf-8'),
                'message': 'User created successfully'
            }
            
        except auth.EmailAlreadyExistsError:
            logger.warning(f"Attempt to create user with existing email: {email}")
            raise ValueError("Email already exists")
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise ValueError(f"Failed to create user: {str(e)}")
    
    def login_user(self, email, password):
        """
        Login user and return custom token (Note: Firebase Admin SDK doesn't verify passwords)
        This is a simplified implementation - in production, use Firebase Auth client SDK
        """
        try:
            # Get user by email from Firebase Auth
            user_record = auth.get_user_by_email(email)
            
            # Generate custom token
            custom_token = auth.create_custom_token(user_record.uid)
            
            # Get user profile from Firestore (auto-create if missing)
            user_doc_ref = self.users_ref.document(user_record.uid)
            user_doc = user_doc_ref.get()
            if not user_doc.exists:
                # Auto-heal: create a minimal profile if missing
                user_data = {
                    'id': user_record.uid,
                    'name': getattr(user_record, 'display_name', None) or 'EcoWarrior',
                    'email': email,
                    'avatar_url': '',
                    'xp': 0,
                    'level': 1,
                    'points': 0,
                    'badges': [],
                    'streak': 0,
                    'total_quizzes_completed': 0,
                    'total_challenges_completed': 0,
                    'current_streak_days': 0,
                    'last_active_date': None,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                self.users_ref.document(user_record.uid).set(user_data)
            else:
                user_data = user_doc.to_dict()
            
            # Update last login time
            self.users_ref.document(user_record.uid).update({
                'last_login_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            logger.info(f"User logged in: {email}")
            
            return {
                'success': True,
                'user_id': user_record.uid,
                'email': email,
                'name': user_data.get('name', 'EcoWarrior'),
                'custom_token': custom_token.decode('utf-8'),
                'profile': {
                    'xp': user_data.get('xp', 0),
                    'level': user_data.get('level', 1),
                    'points': user_data.get('points', 0),
                    'badges': user_data.get('badges', []),
                    'streak': user_data.get('streak', 0)
                }
            }
            
        except auth.UserNotFoundError:
            logger.warning(f"Login attempt with non-existent email: {email}")
            raise ValueError("User not found")
        except Exception as e:
            logger.error(f"Error logging in user: {str(e)}")
            raise ValueError(f"Failed to login: {str(e)}")
    
    def verify_user_token(self, id_token):
        """
        Verify Firebase ID token and return decoded user info
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return {
                'success': True,
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email', ''),
                'email_verified': decoded_token.get('email_verified', False)
            }
        except auth.InvalidIdTokenError:
            logger.warning("Invalid ID token provided")
            raise ValueError("Invalid token")
        except auth.ExpiredIdTokenError:
            logger.warning("Expired ID token provided")
            raise ValueError("Token expired")
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise ValueError(f"Token verification failed: {str(e)}")
    
    def get_user_by_uid(self, uid):
        """
        Get user data by Firebase UID
        """
        try:
            user_doc = self.users_ref.document(uid).get()
            if not user_doc.exists:
                return None
            
            return user_doc.to_dict()
        except Exception as e:
            logger.error(f"Error getting user by UID: {str(e)}")
            return None
    
    def update_user_auth_info(self, uid, **kwargs):
        """
        Update Firebase Auth user information
        """
        try:
            auth.update_user(uid, **kwargs)
            logger.info(f"Updated auth info for user: {uid}")
            return True
        except Exception as e:
            logger.error(f"Error updating user auth info: {str(e)}")
            return False
    
    def delete_user(self, uid):
        """
        Delete user from both Firebase Auth and Firestore
        """
        try:
            # Delete from Firebase Auth
            auth.delete_user(uid)
            
            # Delete from Firestore
            self.users_ref.document(uid).delete()
            
            logger.info(f"Deleted user: {uid}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False
    
    def reset_password(self, email):
        """
        Generate password reset link (simplified implementation)
        """
        try:
            reset_link = auth.generate_password_reset_link(email)
            logger.info(f"Generated password reset link for: {email}")
            return {
                'success': True,
                'reset_link': reset_link,
                'message': 'Password reset link generated'
            }
        except auth.UserNotFoundError:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            raise ValueError("User not found")
        except Exception as e:
            logger.error(f"Error generating password reset link: {str(e)}")
            raise ValueError(f"Failed to generate reset link: {str(e)}")
