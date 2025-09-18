"""
User Service for EcoLearn Platform
Handles user profile management, XP calculation, level progression
"""

from datetime import datetime, timedelta
import logging
import math

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db):
        self.db = db
        self.users_ref = db.collection('users')
        self.attempts_ref = db.collection('attempts')
    
    def get_user_profile(self, user_id):
        """
        Get complete user profile with calculated stats
        """
        try:
            user_doc = self.users_ref.document(user_id).get()
            if not user_doc.exists:
                raise ValueError("User not found")
            
            user_data = user_doc.to_dict()
            
            # Calculate level progress
            current_level = user_data.get('level', 1)
            current_xp = user_data.get('xp', 0)
            xp_for_current_level = self._calculate_xp_for_level(current_level)
            xp_for_next_level = self._calculate_xp_for_level(current_level + 1)
            
            level_progress = {
                'current_level': current_level,
                'current_xp': current_xp,
                'xp_for_current_level': xp_for_current_level,
                'xp_for_next_level': xp_for_next_level,
                'xp_in_level': current_xp - xp_for_current_level,
                'xp_needed_for_next': xp_for_next_level - current_xp,
                'progress_percentage': min(100, ((current_xp - xp_for_current_level) / (xp_for_next_level - xp_for_current_level)) * 100)
            }
            
            # Get recent activity stats
            recent_stats = self._get_recent_activity_stats(user_id)
            
            # Update streak if needed
            self._update_user_streak(user_id, user_data)
            
            profile = {
                **user_data,
                'level_progress': level_progress,
                'recent_stats': recent_stats,
                'account_age_days': (datetime.utcnow() - user_data.get('created_at', datetime.utcnow())).days
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            raise ValueError(f"Failed to get user profile: {str(e)}")
    
    def update_user_profile(self, user_id, update_data):
        """
        Update user profile information
        """
        try:
            # Allowed fields for user update
            allowed_fields = ['name', 'avatar_url', 'bio', 'preferences']
            
            filtered_data = {
                k: v for k, v in update_data.items() 
                if k in allowed_fields
            }
            
            if not filtered_data:
                raise ValueError("No valid fields to update")
            
            # Add timestamp
            filtered_data['updated_at'] = datetime.utcnow()
            
            # Update in Firestore
            self.users_ref.document(user_id).update(filtered_data)
            
            logger.info(f"Updated profile for user: {user_id}")
            
            return {
                'success': True,
                'updated_fields': list(filtered_data.keys()),
                'message': 'Profile updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            raise ValueError(f"Failed to update profile: {str(e)}")
    
    def update_user_stats_after_quiz(self, user_id, quiz_result):
        """
        Update user XP, level, and stats after quiz completion
        """
        try:
            user_doc = self.users_ref.document(user_id).get()
            if not user_doc.exists:
                raise ValueError("User not found")
            
            user_data = user_doc.to_dict()
            
            # Calculate XP gained
            xp_gained = quiz_result.get('earned_xp', 0)
            new_xp = user_data.get('xp', 0) + xp_gained
            
            # Calculate new level
            new_level = self._calculate_level_from_xp(new_xp)
            old_level = user_data.get('level', 1)
            
            # Update stats
            update_data = {
                'xp': new_xp,
                'level': new_level,
                'points': user_data.get('points', 0) + quiz_result.get('score', 0),
                'total_quizzes_completed': user_data.get('total_quizzes_completed', 0) + 1,
                'last_active_date': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Handle level up
            level_up_rewards = []
            if new_level > old_level:
                level_up_rewards = self._handle_level_up(user_id, old_level, new_level)
                update_data['level_up_rewards'] = level_up_rewards
            
            # Update streak
            streak_data = self._update_daily_streak(user_data)
            update_data.update(streak_data)
            
            # Update in Firestore
            self.users_ref.document(user_id).update(update_data)
            
            # Update leaderboard
            self._update_user_leaderboard_position(user_id, new_xp, new_level)
            
            logger.info(f"Updated user stats after quiz: {user_id}, XP: {new_xp}, Level: {new_level}")
            
            return {
                'xp_gained': xp_gained,
                'new_xp': new_xp,
                'new_level': new_level,
                'level_up': new_level > old_level,
                'level_up_rewards': level_up_rewards,
                'streak_updated': streak_data.get('current_streak_days', 0)
            }
            
        except Exception as e:
            logger.error(f"Error updating user stats after quiz: {str(e)}")
            raise ValueError(f"Failed to update user stats: {str(e)}")
    
    def update_user_stats_after_challenge(self, user_id, challenge_result):
        """
        Update user stats after challenge completion
        """
        try:
            user_doc = self.users_ref.document(user_id).get()
            if not user_doc.exists:
                raise ValueError("User not found")
            
            user_data = user_doc.to_dict()
            
            # Calculate rewards
            xp_gained = challenge_result.get('xp_reward', 0)
            points_gained = challenge_result.get('points_reward', 0)
            
            new_xp = user_data.get('xp', 0) + xp_gained
            new_level = self._calculate_level_from_xp(new_xp)
            old_level = user_data.get('level', 1)
            
            # Update stats
            update_data = {
                'xp': new_xp,
                'level': new_level,
                'points': user_data.get('points', 0) + points_gained,
                'total_challenges_completed': user_data.get('total_challenges_completed', 0) + 1,
                'last_active_date': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Handle level up
            if new_level > old_level:
                level_up_rewards = self._handle_level_up(user_id, old_level, new_level)
                update_data['level_up_rewards'] = level_up_rewards
            
            # Update in Firestore
            self.users_ref.document(user_id).update(update_data)
            
            # Update leaderboard
            self._update_user_leaderboard_position(user_id, new_xp, new_level)
            
            logger.info(f"Updated user stats after challenge: {user_id}, XP: {new_xp}")
            
            return {
                'xp_gained': xp_gained,
                'points_gained': points_gained,
                'new_xp': new_xp,
                'new_level': new_level,
                'level_up': new_level > old_level
            }
            
        except Exception as e:
            logger.error(f"Error updating user stats after challenge: {str(e)}")
            raise ValueError(f"Failed to update user stats: {str(e)}")
    
    def get_class_progress(self, class_id):
        """
        Get progress overview for a class (teacher feature)
        """
        try:
            # Query users by class_id (assuming class_id is stored in user profiles)
            users_query = self.users_ref.where('class_id', '==', class_id).stream()
            
            class_stats = {
                'total_students': 0,
                'average_level': 0,
                'average_xp': 0,
                'total_quizzes_completed': 0,
                'total_challenges_completed': 0,
                'students': []
            }
            
            total_xp = 0
            total_level = 0
            
            for user_doc in users_query:
                user_data = user_doc.to_dict()
                class_stats['total_students'] += 1
                
                student_xp = user_data.get('xp', 0)
                student_level = user_data.get('level', 1)
                
                total_xp += student_xp
                total_level += student_level
                
                class_stats['total_quizzes_completed'] += user_data.get('total_quizzes_completed', 0)
                class_stats['total_challenges_completed'] += user_data.get('total_challenges_completed', 0)
                
                class_stats['students'].append({
                    'id': user_doc.id,
                    'name': user_data.get('name', 'Unknown'),
                    'xp': student_xp,
                    'level': student_level,
                    'badges': len(user_data.get('badges', [])),
                    'quizzes_completed': user_data.get('total_quizzes_completed', 0),
                    'challenges_completed': user_data.get('total_challenges_completed', 0),
                    'last_active': user_data.get('last_active_date')
                })
            
            # Calculate averages
            if class_stats['total_students'] > 0:
                class_stats['average_xp'] = total_xp / class_stats['total_students']
                class_stats['average_level'] = total_level / class_stats['total_students']
            
            # Sort students by XP
            class_stats['students'].sort(key=lambda x: x['xp'], reverse=True)
            
            return class_stats
            
        except Exception as e:
            logger.error(f"Error getting class progress: {str(e)}")
            raise ValueError(f"Failed to get class progress: {str(e)}")
    
    def _calculate_level_from_xp(self, xp):
        """
        Calculate level based on XP using formula: Level = floor(sqrt(XP / 100)) + 1
        """
        if xp <= 0:
            return 1
        return math.floor(math.sqrt(xp / 100)) + 1
    
    def _calculate_xp_for_level(self, level):
        """
        Calculate XP required for a specific level
        """
        if level <= 1:
            return 0
        return ((level - 1) ** 2) * 100
    
    def _handle_level_up(self, user_id, old_level, new_level):
        """
        Handle level up rewards and notifications
        """
        rewards = []
        
        for level in range(old_level + 1, new_level + 1):
            # Level milestone rewards
            if level % 5 == 0:  # Every 5 levels
                rewards.append({
                    'type': 'bonus_xp',
                    'amount': 50,
                    'reason': f'Level {level} milestone bonus'
                })
            
            if level == 10:
                rewards.append({
                    'type': 'badge',
                    'badge_id': 'eco-veteran',
                    'reason': 'Reached Level 10'
                })
        
        logger.info(f"User {user_id} leveled up from {old_level} to {new_level}")
        return rewards
    
    def _update_daily_streak(self, user_data):
        """
        Update user's daily activity streak
        """
        now = datetime.utcnow().date()
        last_active = user_data.get('last_active_date')
        
        if not last_active:
            # First activity
            return {
                'current_streak_days': 1,
                'longest_streak_days': max(user_data.get('longest_streak_days', 0), 1),
                'streak_last_updated': datetime.utcnow()
            }
        
        last_active_date = last_active.date() if hasattr(last_active, 'date') else last_active
        days_diff = (now - last_active_date).days
        
        current_streak = user_data.get('current_streak_days', 0)
        
        if days_diff == 0:
            # Same day, no streak update
            return {}
        elif days_diff == 1:
            # Next day, continue streak
            new_streak = current_streak + 1
            return {
                'current_streak_days': new_streak,
                'longest_streak_days': max(user_data.get('longest_streak_days', 0), new_streak),
                'streak_last_updated': datetime.utcnow()
            }
        else:
            # Streak broken
            return {
                'current_streak_days': 1,
                'streak_last_updated': datetime.utcnow()
            }
    
    def _update_user_streak(self, user_id, user_data):
        """
        Update user streak if needed (called during profile fetch)
        """
        streak_data = self._update_daily_streak(user_data)
        if streak_data:
            self.users_ref.document(user_id).update(streak_data)
    
    def _get_recent_activity_stats(self, user_id):
        """
        Get user's recent activity statistics
        """
        try:
            # Get recent quiz attempts (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_attempts = self.attempts_ref.where('user_id', '==', user_id).where('created_at', '>=', week_ago).stream()
            
            recent_stats = {
                'quizzes_this_week': 0,
                'average_score_this_week': 0,
                'xp_earned_this_week': 0,
                'days_active_this_week': set()
            }
            
            total_score = 0
            total_xp = 0
            
            for attempt in recent_attempts:
                attempt_data = attempt.to_dict()
                recent_stats['quizzes_this_week'] += 1
                total_score += attempt_data.get('score', 0)
                total_xp += attempt_data.get('earned_xp', 0)
                
                # Track active days
                attempt_date = attempt_data.get('created_at', datetime.utcnow()).date()
                recent_stats['days_active_this_week'].add(attempt_date)
            
            if recent_stats['quizzes_this_week'] > 0:
                recent_stats['average_score_this_week'] = total_score / recent_stats['quizzes_this_week']
            
            recent_stats['xp_earned_this_week'] = total_xp
            recent_stats['days_active_this_week'] = len(recent_stats['days_active_this_week'])
            
            return recent_stats
            
        except Exception as e:
            logger.error(f"Error getting recent activity stats: {str(e)}")
            return {
                'quizzes_this_week': 0,
                'average_score_this_week': 0,
                'xp_earned_this_week': 0,
                'days_active_this_week': 0
            }
    
    def _update_user_leaderboard_position(self, user_id, xp, level):
        """
        Update user's position in leaderboards
        """
        try:
            # Update global leaderboard
            leaderboard_ref = self.db.collection('leaderboards').document('global')
            
            # This is a simplified approach - in production, consider using more efficient methods
            leaderboard_doc = leaderboard_ref.get()
            
            if leaderboard_doc.exists:
                leaderboard_data = leaderboard_doc.to_dict()
                entries = leaderboard_data.get('entries', [])
                
                # Find and update user entry
                user_found = False
                for entry in entries:
                    if entry.get('user_id') == user_id:
                        entry['xp'] = xp
                        entry['level'] = level
                        entry['updated_at'] = datetime.utcnow()
                        user_found = True
                        break
                
                # Add user if not found
                if not user_found:
                    entries.append({
                        'user_id': user_id,
                        'xp': xp,
                        'level': level,
                        'updated_at': datetime.utcnow()
                    })
                
                # Sort by XP and keep top 1000
                entries.sort(key=lambda x: x['xp'], reverse=True)
                entries = entries[:1000]
                
                # Update leaderboard
                leaderboard_ref.update({
                    'entries': entries,
                    'updated_at': datetime.utcnow()
                })
            else:
                # Create new leaderboard
                leaderboard_ref.set({
                    'scope': 'global',
                    'entries': [{
                        'user_id': user_id,
                        'xp': xp,
                        'level': level,
                        'updated_at': datetime.utcnow()
                    }],
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
                
        except Exception as e:
            logger.error(f"Error updating user leaderboard position: {str(e)}")