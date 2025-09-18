"""
Badge Service for EcoLearn Platform
Handles badge management, criteria checking, and awarding system
"""

from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

class BadgeService:
    def __init__(self, db):
        self.db = db
        self.badges_ref = db.collection('badges')
        self.users_ref = db.collection('users')
        self.attempts_ref = db.collection('attempts')
        self.user_badges_ref = db.collection('user_badges')
    
    def get_all_badges(self):
        """
        Get all available badges in the system
        """
        try:
            badges = []
            for badge_doc in self.badges_ref.stream():
                badge_data = badge_doc.to_dict()
                badge_data['id'] = badge_doc.id
                badges.append(badge_data)
            
            # Sort by creation order
            badges.sort(key=lambda x: x.get('created_at', datetime.min))
            return badges
            
        except Exception as e:
            logger.error(f"Error getting all badges: {str(e)}")
            raise ValueError(f"Failed to get badges: {str(e)}")
    
    def get_user_badges(self, user_id):
        """
        Get user's earned badges along with available badges
        """
        try:
            # Get user's earned badges
            user_badges_query = self.user_badges_ref.where('user_id', '==', user_id).stream()
            earned_badge_ids = set()
            earned_badges = []
            
            for user_badge_doc in user_badges_query:
                user_badge_data = user_badge_doc.to_dict()
                earned_badge_ids.add(user_badge_data['badge_id'])
                earned_badges.append(user_badge_data)
            
            # Get all available badges
            all_badges = self.get_all_badges()
            
            # Mark which badges are earned
            for badge in all_badges:
                badge['earned'] = badge['id'] in earned_badge_ids
                badge['earned_at'] = None
                
                # Add earned date if available
                for earned_badge in earned_badges:
                    if earned_badge['badge_id'] == badge['id']:
                        badge['earned_at'] = earned_badge.get('earned_at')
                        break
            
            return {
                'all_badges': all_badges,
                'earned_badges': [b for b in all_badges if b['earned']],
                'available_badges': [b for b in all_badges if not b['earned']],
                'total_badges': len(all_badges),
                'earned_count': len([b for b in all_badges if b['earned']])
            }
            
        except Exception as e:
            logger.error(f"Error getting user badges: {str(e)}")
            raise ValueError(f"Failed to get user badges: {str(e)}")
    
    def check_and_award_badges(self, user_id):
        """
        Check user's eligibility for badges and award new ones
        """
        try:
            # Get user data
            user_doc = self.users_ref.document(user_id).get()
            if not user_doc.exists:
                raise ValueError("User not found")
            
            user_data = user_doc.to_dict()
            
            # Get user's current badges
            current_badges = self._get_user_earned_badge_ids(user_id)
            
            # Get all badge definitions
            all_badges = self.get_all_badges()
            
            newly_earned = []
            
            for badge in all_badges:
                if badge['id'] not in current_badges:
                    # Check if user meets criteria
                    if self._check_badge_criteria(user_id, badge, user_data):
                        self._award_badge_to_user(user_id, badge['id'])
                        newly_earned.append(badge)
            
            logger.info(f"Checked badges for user {user_id}, awarded {len(newly_earned)} new badges")
            return newly_earned
            
        except Exception as e:
            logger.error(f"Error checking badge eligibility: {str(e)}")
            raise ValueError(f"Failed to check badge eligibility: {str(e)}")
    
    def _check_badge_criteria(self, user_id, badge, user_data):
        """
        Check if user meets specific badge criteria
        """
        try:
            criteria = badge.get('criteria', {})
            badge_type = criteria.get('type')
            
            if badge_type == 'xp_threshold':
                return user_data.get('xp', 0) >= criteria.get('xp_required', 0)
            
            elif badge_type == 'level_threshold':
                return user_data.get('level', 1) >= criteria.get('level_required', 1)
            
            elif badge_type == 'quiz_completion':
                return user_data.get('total_quizzes_completed', 0) >= criteria.get('quizzes_required', 1)
            
            elif badge_type == 'perfect_score':
                # Check if user has any perfect quiz scores
                return self._has_perfect_quiz_score(user_id)
            
            elif badge_type == 'challenge_completion':
                return user_data.get('total_challenges_completed', 0) >= criteria.get('challenges_required', 1)
            
            elif badge_type == 'streak':
                return user_data.get('current_streak_days', 0) >= criteria.get('streak_days_required', 1)
            
            elif badge_type == 'category_mastery':
                category = criteria.get('category')
                required_score = criteria.get('average_score_required', 80)
                return self._check_category_mastery(user_id, category, required_score)
            
            elif badge_type == 'social':
                # Check social achievements like sharing, teaching others
                return self._check_social_criteria(user_id, criteria)
            
            elif badge_type == 'time_based':
                # Check time-based achievements
                return self._check_time_based_criteria(user_id, criteria, user_data)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking badge criteria: {str(e)}")
            return False
    
    def _has_perfect_quiz_score(self, user_id):
        """
        Check if user has achieved a perfect score on any quiz
        """
        try:
            perfect_attempts = self.attempts_ref.where('user_id', '==', user_id).where('score_percentage', '==', 100.0).limit(1).stream()
            return len(list(perfect_attempts)) > 0
        except:
            return False
    
    def _check_category_mastery(self, user_id, category, required_score):
        """
        Check if user has mastered a specific category
        """
        try:
            # This would require storing category info in attempts
            # For now, return False as it needs more complex query logic
            return False
        except:
            return False
    
    def _check_social_criteria(self, user_id, criteria):
        """
        Check social-based badge criteria
        """
        # Placeholder for social features
        return False
    
    def _check_time_based_criteria(self, user_id, criteria, user_data):
        """
        Check time-based badge criteria
        """
        try:
            if criteria.get('account_age_days'):
                account_age = (datetime.utcnow() - user_data.get('created_at', datetime.utcnow())).days
                return account_age >= criteria.get('account_age_days')
            
            if criteria.get('consecutive_days'):
                return user_data.get('current_streak_days', 0) >= criteria.get('consecutive_days')
            
            return False
        except:
            return False
    
    def _get_user_earned_badge_ids(self, user_id):
        """
        Get list of badge IDs that user has already earned
        """
        try:
            earned_badges = set()
            for badge_doc in self.user_badges_ref.where('user_id', '==', user_id).stream():
                badge_data = badge_doc.to_dict()
                earned_badges.add(badge_data['badge_id'])
            return earned_badges
        except:
            return set()
    
    def _award_badge_to_user(self, user_id, badge_id):
        """
        Award a badge to a user
        """
        try:
            # Create user badge record
            user_badge_data = {
                'user_id': user_id,
                'badge_id': badge_id,
                'earned_at': datetime.utcnow(),
                'created_at': datetime.utcnow()
            }
            
            self.user_badges_ref.add(user_badge_data)
            
            # Update user's badge list
            user_doc = self.users_ref.document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                current_badges = user_data.get('badges', [])
                if badge_id not in current_badges:
                    current_badges.append(badge_id)
                    self.users_ref.document(user_id).update({
                        'badges': current_badges,
                        'updated_at': datetime.utcnow()
                    })
            
            logger.info(f"Awarded badge {badge_id} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error awarding badge: {str(e)}")
            return False
    
    def create_badge(self, name, description, icon_url, criteria, category='general'):
        """
        Create a new badge (admin function)
        """
        try:
            badge_data = {
                'name': name,
                'description': description,
                'icon_url': icon_url,
                'criteria': criteria,
                'category': category,
                'rarity': criteria.get('rarity', 'common'),
                'points_value': criteria.get('points_value', 10),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'active': True
            }
            
            badge_ref = self.badges_ref.add(badge_data)
            badge_id = badge_ref[1].id
            
            logger.info(f"Created new badge: {name}")
            
            return {
                'badge_id': badge_id,
                'name': name,
                'message': 'Badge created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating badge: {str(e)}")
            raise ValueError(f"Failed to create badge: {str(e)}")
    
    def seed_badges(self):
        """
        Seed database with initial badge data
        """
        try:
            sample_badges = [
                {
                    'name': 'Eco Starter',
                    'description': 'Complete your first quiz',
                    'icon_url': '🌱',
                    'category': 'beginner',
                    'rarity': 'common',
                    'points_value': 10,
                    'criteria': {
                        'type': 'quiz_completion',
                        'quizzes_required': 1
                    }
                },
                {
                    'name': 'Quiz Master',
                    'description': 'Score 100% on a quiz',
                    'icon_url': '🧠',
                    'category': 'achievement',
                    'rarity': 'uncommon',
                    'points_value': 25,
                    'criteria': {
                        'type': 'perfect_score'
                    }
                },
                {
                    'name': 'Waste Warrior',
                    'description': 'Complete 3 eco challenges',
                    'icon_url': '♻️',
                    'category': 'challenge',
                    'rarity': 'uncommon',
                    'points_value': 30,
                    'criteria': {
                        'type': 'challenge_completion',
                        'challenges_required': 3
                    }
                },
                {
                    'name': 'Energy Saver',
                    'description': 'Reach Level 3',
                    'icon_url': '⚡',
                    'category': 'progression',
                    'rarity': 'common',
                    'points_value': 20,
                    'criteria': {
                        'type': 'level_threshold',
                        'level_required': 3
                    }
                },
                {
                    'name': 'Eco Champion',
                    'description': 'Earn 500 XP',
                    'icon_url': '👑',
                    'category': 'progression',
                    'rarity': 'rare',
                    'points_value': 50,
                    'criteria': {
                        'type': 'xp_threshold',
                        'xp_required': 500
                    }
                },
                {
                    'name': 'Planet Protector',
                    'description': 'Complete all available challenges',
                    'icon_url': '🌍',
                    'category': 'mastery',
                    'rarity': 'epic',
                    'points_value': 100,
                    'criteria': {
                        'type': 'challenge_completion',
                        'challenges_required': 8
                    }
                },
                {
                    'name': 'Streak Keeper',
                    'description': 'Maintain a 7-day learning streak',
                    'icon_url': '🔥',
                    'category': 'consistency',
                    'rarity': 'uncommon',
                    'points_value': 35,
                    'criteria': {
                        'type': 'streak',
                        'streak_days_required': 7
                    }
                },
                {
                    'name': 'Knowledge Seeker',
                    'description': 'Complete 10 quizzes',
                    'icon_url': '📚',
                    'category': 'dedication',
                    'rarity': 'uncommon',
                    'points_value': 40,
                    'criteria': {
                        'type': 'quiz_completion',
                        'quizzes_required': 10
                    }
                },
                {
                    'name': 'Early Adopter',
                    'description': 'Join EcoLearn in its first month',
                    'icon_url': '🚀',
                    'category': 'special',
                    'rarity': 'legendary',
                    'points_value': 75,
                    'criteria': {
                        'type': 'time_based',
                        'account_age_days': 30
                    }
                }
            ]
            
            for badge_data in sample_badges:
                badge_data['created_at'] = datetime.utcnow()
                badge_data['updated_at'] = datetime.utcnow()
                badge_data['active'] = True
                
                self.badges_ref.add(badge_data)
            
            logger.info("Seeded badge database with sample data")
            return True
            
        except Exception as e:
            logger.error(f"Error seeding badges: {str(e)}")
            return False