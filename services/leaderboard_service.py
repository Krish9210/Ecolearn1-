"""
Leaderboard Service for EcoLearn Platform
Handles global and scoped leaderboards with real-time ranking
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class LeaderboardService:
    def __init__(self, db):
        self.db = db
        self.users_ref = db.collection('users')
        self.leaderboards_ref = db.collection('leaderboards')
        self.attempts_ref = db.collection('attempts')
    
    def get_leaderboard(self, scope='global', period='all', limit=50, current_user_id=None):
        """
        Get leaderboard data based on scope and time period
        """
        try:
            if scope == 'global':
                return self._get_global_leaderboard(period, limit, current_user_id)
            elif scope == 'school':
                return self._get_school_leaderboard(period, limit, current_user_id)
            elif scope == 'class':
                return self._get_class_leaderboard(period, limit, current_user_id)
            else:
                raise ValueError("Invalid leaderboard scope")
                
        except Exception as e:
            logger.error(f"Error getting leaderboard: {str(e)}")
            raise ValueError(f"Failed to get leaderboard: {str(e)}")
    
    def _get_global_leaderboard(self, period, limit, current_user_id):
        """
        Get global leaderboard for all users
        """
        try:
            # Calculate time filter if needed
            time_filter = self._get_time_filter(period)
            
            if period == 'all':
                # Use user XP for all-time leaderboard
                users_query = self.users_ref.order_by('xp', direction='DESCENDING').limit(limit)
                entries = []
                
                rank = 1
                current_user_rank = None
                current_user_data = None
                
                for user_doc in users_query.stream():
                    user_data = user_doc.to_dict()
                    
                    entry = {
                        'rank': rank,
                        'user_id': user_doc.id,
                        'name': user_data.get('name', 'EcoWarrior'),
                        'xp': user_data.get('xp', 0),
                        'level': user_data.get('level', 1),
                        'badges': len(user_data.get('badges', [])),
                        'avatar_url': user_data.get('avatar_url', ''),
                        'streak': user_data.get('current_streak_days', 0)
                    }
                    
                    entries.append(entry)
                    
                    # Track current user
                    if user_doc.id == current_user_id:
                        current_user_rank = rank
                        current_user_data = entry
                    
                    rank += 1
                
                # If current user not in top results, find their rank
                if current_user_id and current_user_rank is None:
                    current_user_rank, current_user_data = self._find_user_rank(current_user_id, 'xp')
                
            else:
                # Use period-based scoring (quiz attempts)
                entries, current_user_rank, current_user_data = self._get_period_leaderboard(
                    time_filter, limit, current_user_id
                )
            
            return {
                'scope': 'global',
                'period': period,
                'entries': entries,
                'current_user': {
                    'rank': current_user_rank,
                    'data': current_user_data
                } if current_user_data else None,
                'total_entries': len(entries),
                'updated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting global leaderboard: {str(e)}")
            raise
    
    def _get_period_leaderboard(self, time_filter, limit, current_user_id):
        """
        Get leaderboard for a specific time period based on quiz performance
        """
        try:
            # Get all quiz attempts in the time period
            attempts_query = self.attempts_ref.where('created_at', '>=', time_filter).stream()
            
            # Aggregate user scores
            user_scores = {}
            
            for attempt_doc in attempts_query:
                attempt_data = attempt_doc.to_dict()
                user_id = attempt_data.get('user_id')
                earned_xp = attempt_data.get('earned_xp', 0)
                
                if user_id not in user_scores:
                    user_scores[user_id] = {
                        'xp': 0,
                        'attempts': 0,
                        'total_score': 0
                    }
                
                user_scores[user_id]['xp'] += earned_xp
                user_scores[user_id]['attempts'] += 1
                user_scores[user_id]['total_score'] += attempt_data.get('score', 0)
            
            # Get user details and create entries
            entries = []
            current_user_rank = None
            current_user_data = None
            
            # Sort by XP
            sorted_users = sorted(user_scores.items(), key=lambda x: x[1]['xp'], reverse=True)
            
            for rank, (user_id, score_data) in enumerate(sorted_users[:limit], 1):
                # Get user profile
                user_doc = self.users_ref.document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    
                    entry = {
                        'rank': rank,
                        'user_id': user_id,
                        'name': user_data.get('name', 'EcoWarrior'),
                        'xp': score_data['xp'],
                        'level': user_data.get('level', 1),
                        'badges': len(user_data.get('badges', [])),
                        'avatar_url': user_data.get('avatar_url', ''),
                        'period_attempts': score_data['attempts'],
                        'average_score': score_data['total_score'] / score_data['attempts'] if score_data['attempts'] > 0 else 0
                    }
                    
                    entries.append(entry)
                    
                    if user_id == current_user_id:
                        current_user_rank = rank
                        current_user_data = entry
            
            # Find current user rank if not in top results
            if current_user_id and current_user_rank is None:
                user_rank = 1
                for user_id, score_data in sorted_users:
                    if user_id == current_user_id:
                        user_doc = self.users_ref.document(user_id).get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            current_user_data = {
                                'rank': user_rank,
                                'user_id': user_id,
                                'name': user_data.get('name', 'EcoWarrior'),
                                'xp': score_data['xp'],
                                'level': user_data.get('level', 1),
                                'badges': len(user_data.get('badges', [])),
                                'period_attempts': score_data['attempts']
                            }
                            current_user_rank = user_rank
                        break
                    user_rank += 1
            
            return entries, current_user_rank, current_user_data
            
        except Exception as e:
            logger.error(f"Error getting period leaderboard: {str(e)}")
            return [], None, None
    
    def _get_school_leaderboard(self, period, limit, current_user_id):
        """
        Get school-specific leaderboard (placeholder implementation)
        """
        # This would filter users by school_id
        # For now, return empty as it requires school association
        return {
            'scope': 'school',
            'period': period,
            'entries': [],
            'current_user': None,
            'total_entries': 0,
            'message': 'School leaderboards require school association',
            'updated_at': datetime.utcnow()
        }
    
    def _get_class_leaderboard(self, period, limit, current_user_id):
        """
        Get class-specific leaderboard (placeholder implementation)
        """
        # This would filter users by class_id
        # For now, return empty as it requires class association
        return {
            'scope': 'class',
            'period': period,
            'entries': [],
            'current_user': None,
            'total_entries': 0,
            'message': 'Class leaderboards require class association',
            'updated_at': datetime.utcnow()
        }
    
    def _find_user_rank(self, user_id, field='xp'):
        """
        Find a user's rank in the global leaderboard
        """
        try:
            user_doc = self.users_ref.document(user_id).get()
            if not user_doc.exists:
                return None, None
            
            user_data = user_doc.to_dict()
            user_score = user_data.get(field, 0)
            
            # Count users with higher scores
            higher_scores_count = len(list(
                self.users_ref.where(field, '>', user_score).stream()
            ))
            
            rank = higher_scores_count + 1
            
            return rank, {
                'rank': rank,
                'user_id': user_id,
                'name': user_data.get('name', 'EcoWarrior'),
                'xp': user_data.get('xp', 0),
                'level': user_data.get('level', 1),
                'badges': len(user_data.get('badges', [])),
                'avatar_url': user_data.get('avatar_url', '')
            }
            
        except Exception as e:
            logger.error(f"Error finding user rank: {str(e)}")
            return None, None
    
    def _get_time_filter(self, period):
        """
        Get datetime filter for period-based queries
        """
        now = datetime.utcnow()
        
        if period == 'weekly':
            return now - timedelta(days=7)
        elif period == 'monthly':
            return now - timedelta(days=30)
        elif period == 'daily':
            return now - timedelta(days=1)
        else:
            return datetime.min  # All time
    
    def update_user_leaderboard_position(self, user_id, xp, level):
        """
        Update user's position in cached leaderboards
        """
        try:
            # Update global leaderboard cache
            global_board_ref = self.leaderboards_ref.document('global')
            global_doc = global_board_ref.get()
            
            user_entry = {
                'user_id': user_id,
                'xp': xp,
                'level': level,
                'updated_at': datetime.utcnow()
            }
            
            if global_doc.exists:
                board_data = global_doc.to_dict()
                entries = board_data.get('entries', [])
                
                # Find and update user entry
                user_found = False
                for i, entry in enumerate(entries):
                    if entry.get('user_id') == user_id:
                        entries[i] = {**entry, **user_entry}
                        user_found = True
                        break
                
                # Add new user if not found
                if not user_found:
                    entries.append(user_entry)
                
                # Sort by XP and limit to top 1000
                entries.sort(key=lambda x: x.get('xp', 0), reverse=True)
                entries = entries[:1000]
                
                global_board_ref.update({
                    'entries': entries,
                    'updated_at': datetime.utcnow()
                })
            else:
                # Create new leaderboard
                global_board_ref.set({
                    'scope': 'global',
                    'entries': [user_entry],
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
            
            logger.info(f"Updated leaderboard position for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating leaderboard position: {str(e)}")
    
    def get_leaderboard_stats(self):
        """
        Get overall leaderboard statistics
        """
        try:
            # Count total active users
            total_users = len(list(self.users_ref.where('xp', '>', 0).stream()))
            
            # Get top performer
            top_user_query = self.users_ref.order_by('xp', direction='DESCENDING').limit(1)
            top_user_data = None
            
            for user_doc in top_user_query.stream():
                user_data = user_doc.to_dict()
                top_user_data = {
                    'name': user_data.get('name', 'EcoWarrior'),
                    'xp': user_data.get('xp', 0),
                    'level': user_data.get('level', 1)
                }
                break
            
            # Calculate average XP
            total_xp = 0
            user_count = 0
            for user_doc in self.users_ref.stream():
                user_data = user_doc.to_dict()
                total_xp += user_data.get('xp', 0)
                user_count += 1
            
            average_xp = total_xp / user_count if user_count > 0 else 0
            
            return {
                'total_users': total_users,
                'top_performer': top_user_data,
                'average_xp': round(average_xp, 2),
                'total_xp_earned': total_xp
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard stats: {str(e)}")
            raise ValueError(f"Failed to get leaderboard stats: {str(e)}")
    
    def reset_periodic_leaderboards(self, period='weekly'):
        """
        Reset periodic leaderboards (scheduled task)
        """
        try:
            # This would be called by a scheduled cloud function
            # to reset weekly/monthly leaderboards
            
            leaderboard_doc = f"{period}_leaderboard_{datetime.utcnow().strftime('%Y_%m_%d')}"
            
            # Archive current period leaderboard
            current_board = self._get_global_leaderboard(period, 100, None)
            
            archived_ref = self.leaderboards_ref.document(f'archived_{leaderboard_doc}')
            archived_ref.set({
                **current_board,
                'archived_at': datetime.utcnow()
            })
            
            logger.info(f"Archived {period} leaderboard: {leaderboard_doc}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting periodic leaderboards: {str(e)}")
            return False