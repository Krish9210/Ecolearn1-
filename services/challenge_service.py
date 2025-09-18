"""
Challenge Service for EcoLearn Platform
Handles eco-challenges, completion tracking, and reward distribution
"""

from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

class ChallengeService:
    def __init__(self, db):
        self.db = db
        self.challenges_ref = db.collection('challenges')
        self.user_challenges_ref = db.collection('user_challenges')
        self.users_ref = db.collection('users')
    
    def get_all_challenges(self):
        """
        Get all available challenges
        """
        try:
            challenges = []
            for challenge_doc in self.challenges_ref.where('status', '==', 'active').stream():
                challenge_data = challenge_doc.to_dict()
                challenge_data['id'] = challenge_doc.id
                challenges.append(challenge_data)
            
            # Sort by creation date
            challenges.sort(key=lambda x: x.get('created_at', datetime.min))
            return challenges
            
        except Exception as e:
            logger.error(f"Error getting all challenges: {str(e)}")
            raise ValueError(f"Failed to get challenges: {str(e)}")
    
    def get_user_challenges(self, user_id):
        """
        Get challenges with user's completion status
        """
        try:
            # Get all challenges
            all_challenges = self.get_all_challenges()
            
            # Get user's completed challenges
            completed_challenges = set()
            user_challenge_docs = self.user_challenges_ref.where('user_id', '==', user_id).stream()
            
            user_completions = {}
            for doc in user_challenge_docs:
                completion_data = doc.to_dict()
                challenge_id = completion_data['challenge_id']
                completed_challenges.add(challenge_id)
                user_completions[challenge_id] = completion_data
            
            # Enhance challenges with user status
            for challenge in all_challenges:
                challenge_id = challenge['id']
                challenge['completed'] = challenge_id in completed_challenges
                challenge['completion_data'] = user_completions.get(challenge_id)
                
                # Calculate progress if applicable
                if challenge.get('type') == 'recurring':
                    challenge['progress'] = self._calculate_recurring_progress(user_id, challenge)
            
            return {
                'challenges': all_challenges,
                'completed_count': len(completed_challenges),
                'available_count': len([c for c in all_challenges if not c['completed']]),
                'total_count': len(all_challenges)
            }
            
        except Exception as e:
            logger.error(f"Error getting user challenges: {str(e)}")
            raise ValueError(f"Failed to get user challenges: {str(e)}")
    
    def complete_challenge(self, user_id, challenge_id, proof=""):
        """
        Mark a challenge as completed for a user
        """
        try:
            # Get challenge details
            challenge_doc = self.challenges_ref.document(challenge_id).get()
            if not challenge_doc.exists:
                raise ValueError("Challenge not found")
            
            challenge_data = challenge_doc.to_dict()
            
            # Check if already completed
            existing_completion = self.user_challenges_ref.where('user_id', '==', user_id).where('challenge_id', '==', challenge_id).limit(1).stream()
            
            if len(list(existing_completion)) > 0:
                # For recurring challenges, allow multiple completions
                if challenge_data.get('type') != 'recurring':
                    raise ValueError("Challenge already completed")
            
            # Calculate rewards
            base_xp = challenge_data.get('xp_reward', 0)
            base_points = challenge_data.get('points_reward', 0)
            
            # Apply multipliers for difficulty
            difficulty_multiplier = self._get_difficulty_multiplier(challenge_data.get('difficulty', 'medium'))
            
            final_xp = int(base_xp * difficulty_multiplier)
            final_points = int(base_points * difficulty_multiplier)
            
            # Create completion record
            completion_data = {
                'user_id': user_id,
                'challenge_id': challenge_id,
                'challenge_title': challenge_data.get('title', ''),
                'challenge_category': challenge_data.get('category', 'general'),
                'xp_reward': final_xp,
                'points_reward': final_points,
                'proof_submitted': proof,
                'status': 'completed',
                'completed_at': datetime.utcnow(),
                'created_at': datetime.utcnow()
            }
            
            # Save completion record
            self.user_challenges_ref.add(completion_data)
            
            # Update challenge statistics
            self._update_challenge_stats(challenge_id)
            
            # Check for challenge-based achievements
            self._check_challenge_achievements(user_id)
            
            logger.info(f"Challenge completed - User: {user_id}, Challenge: {challenge_id}, XP: {final_xp}")
            
            return {
                'challenge_id': challenge_id,
                'challenge_title': challenge_data.get('title'),
                'xp_reward': final_xp,
                'points_reward': final_points,
                'difficulty_multiplier': difficulty_multiplier,
                'completion_message': self._get_completion_message(challenge_data),
                'next_suggested_challenges': self._get_suggested_challenges(user_id, challenge_data.get('category'))
            }
            
        except Exception as e:
            logger.error(f"Error completing challenge: {str(e)}")
            raise ValueError(f"Failed to complete challenge: {str(e)}")
    
    def get_user_challenge_stats(self, user_id):
        """
        Get user's challenge completion statistics
        """
        try:
            completions = list(self.user_challenges_ref.where('user_id', '==', user_id).stream())
            
            if not completions:
                return {
                    'total_completed': 0,
                    'total_xp_earned': 0,
                    'total_points_earned': 0,
                    'categories': {},
                    'recent_completions': [],
                    'streak_data': {'current_streak': 0, 'longest_streak': 0}
                }
            
            total_xp = 0
            total_points = 0
            categories = {}
            recent_completions = []
            
            # Process completions
            completion_dates = []
            
            for doc in completions:
                completion_data = doc.to_dict()
                
                total_xp += completion_data.get('xp_reward', 0)
                total_points += completion_data.get('points_reward', 0)
                
                # Track by category
                category = completion_data.get('challenge_category', 'general')
                if category not in categories:
                    categories[category] = {'count': 0, 'xp': 0}
                categories[category]['count'] += 1
                categories[category]['xp'] += completion_data.get('xp_reward', 0)
                
                # Recent completions (last 10)
                if len(recent_completions) < 10:
                    recent_completions.append({
                        'challenge_title': completion_data.get('challenge_title'),
                        'completed_at': completion_data.get('completed_at'),
                        'xp_earned': completion_data.get('xp_reward', 0)
                    })
                
                # Track completion dates for streak calculation
                completed_date = completion_data.get('completed_at')
                if completed_date:
                    completion_dates.append(completed_date.date())
            
            # Calculate streaks
            streak_data = self._calculate_challenge_streak(completion_dates)
            
            # Sort recent completions by date
            recent_completions.sort(key=lambda x: x.get('completed_at', datetime.min), reverse=True)
            
            return {
                'total_completed': len(completions),
                'total_xp_earned': total_xp,
                'total_points_earned': total_points,
                'categories': categories,
                'recent_completions': recent_completions,
                'streak_data': streak_data
            }
            
        except Exception as e:
            logger.error(f"Error getting challenge stats: {str(e)}")
            raise ValueError(f"Failed to get challenge stats: {str(e)}")
    
    def create_challenge(self, title, description, category, difficulty, xp_reward, points_reward, challenge_type='one-time'):
        """
        Create a new challenge (admin function)
        """
        try:
            challenge_data = {
                'title': title,
                'description': description,
                'category': category,
                'difficulty': difficulty,  # easy, medium, hard
                'type': challenge_type,    # one-time, recurring, daily
                'xp_reward': xp_reward,
                'points_reward': points_reward,
                'status': 'active',
                'total_completions': 0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            challenge_ref = self.challenges_ref.add(challenge_data)
            challenge_id = challenge_ref[1].id
            
            logger.info(f"Created new challenge: {title}")
            
            return {
                'challenge_id': challenge_id,
                'title': title,
                'message': 'Challenge created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating challenge: {str(e)}")
            raise ValueError(f"Failed to create challenge: {str(e)}")
    
    def _get_difficulty_multiplier(self, difficulty):
        """
        Get XP/Points multiplier based on difficulty
        """
        multipliers = {
            'easy': 1.0,
            'medium': 1.2,
            'hard': 1.5,
            'expert': 2.0
        }
        return multipliers.get(difficulty, 1.0)
    
    def _get_completion_message(self, challenge_data):
        """
        Generate completion message based on challenge
        """
        category = challenge_data.get('category', 'general')
        difficulty = challenge_data.get('difficulty', 'medium')
        
        messages = {
            'waste': "Great job reducing waste! Every action counts towards a cleaner planet.",
            'energy': "Excellent energy conservation! You're helping reduce carbon emissions.",
            'water': "Amazing water conservation effort! You're protecting this precious resource.",
            'transportation': "Fantastic eco-friendly transportation choice! You've reduced your carbon footprint.",
            'food': "Wonderful sustainable food choice! You're supporting eco-friendly practices.",
            'education': "Great job spreading environmental awareness! Knowledge is power for change."
        }
        
        base_message = messages.get(category, "Congratulations on completing this eco-challenge!")
        
        if difficulty == 'hard':
            base_message += " This was a challenging task - you should be proud!"
        
        return base_message
    
    def _get_suggested_challenges(self, user_id, completed_category):
        """
        Get suggested next challenges based on completion
        """
        try:
            # Get challenges from same category that user hasn't completed
            user_completed = set()
            for doc in self.user_challenges_ref.where('user_id', '==', user_id).stream():
                user_completed.add(doc.to_dict().get('challenge_id'))
            
            suggestions = []
            for doc in self.challenges_ref.where('category', '==', completed_category).where('status', '==', 'active').limit(3).stream():
                if doc.id not in user_completed:
                    challenge_data = doc.to_dict()
                    suggestions.append({
                        'id': doc.id,
                        'title': challenge_data.get('title'),
                        'difficulty': challenge_data.get('difficulty'),
                        'xp_reward': challenge_data.get('xp_reward')
                    })
            
            return suggestions
        except:
            return []
    
    def _update_challenge_stats(self, challenge_id):
        """
        Update challenge completion statistics
        """
        try:
            challenge_ref = self.challenges_ref.document(challenge_id)
            challenge_doc = challenge_ref.get()
            
            if challenge_doc.exists:
                current_completions = challenge_doc.to_dict().get('total_completions', 0)
                challenge_ref.update({
                    'total_completions': current_completions + 1,
                    'updated_at': datetime.utcnow()
                })
        except Exception as e:
            logger.error(f"Error updating challenge stats: {str(e)}")
    
    def _check_challenge_achievements(self, user_id):
        """
        Check for challenge-based achievements/badges
        """
        try:
            # Count user's total challenge completions
            total_completions = len(list(self.user_challenges_ref.where('user_id', '==', user_id).stream()))
            
            # This would integrate with badge service to check for milestone badges
            # For now, just log the achievement
            milestones = [1, 3, 5, 10, 25, 50]
            if total_completions in milestones:
                logger.info(f"User {user_id} reached challenge milestone: {total_completions} completions")
        except Exception as e:
            logger.error(f"Error checking challenge achievements: {str(e)}")
    
    def _calculate_challenge_streak(self, completion_dates):
        """
        Calculate challenge completion streak
        """
        if not completion_dates:
            return {'current_streak': 0, 'longest_streak': 0}
        
        # Sort dates
        sorted_dates = sorted(set(completion_dates), reverse=True)
        
        current_streak = 1
        longest_streak = 1
        temp_streak = 1
        
        # Calculate current streak (from most recent date)
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i-1] - sorted_dates[i]).days == 1:
                current_streak += 1
            else:
                break
        
        # Calculate longest streak
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i-1] - sorted_dates[i]).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak
        }
    
    def _calculate_recurring_progress(self, user_id, challenge):
        """
        Calculate progress for recurring challenges
        """
        try:
            # This is a placeholder for recurring challenge logic
            # Would track weekly/monthly completions
            return {
                'current_period': 0,
                'target': challenge.get('target_completions', 1),
                'progress_percentage': 0
            }
        except:
            return {'current_period': 0, 'target': 1, 'progress_percentage': 0}
    
    def seed_challenges(self):
        """
        Seed database with initial challenge data
        """
        try:
            sample_challenges = [
                {
                    'title': 'Plant a Tree 🌱',
                    'description': 'Plant a tree or donate to a tree-planting organization to help combat climate change',
                    'category': 'environmental',
                    'difficulty': 'medium',
                    'type': 'one-time',
                    'xp_reward': 50,
                    'points_reward': 25,
                    'status': 'active'
                },
                {
                    'title': 'Plastic-Free Day 🛍️',
                    'description': 'Avoid using single-use plastics for one full day',
                    'category': 'waste',
                    'difficulty': 'easy',
                    'type': 'recurring',
                    'xp_reward': 30,
                    'points_reward': 15,
                    'status': 'active'
                },
                {
                    'title': 'Bike to Work 🚲',
                    'description': 'Use a bicycle instead of a car for transportation to reduce carbon emissions',
                    'category': 'transportation',
                    'difficulty': 'easy',
                    'type': 'recurring',
                    'xp_reward': 25,
                    'points_reward': 12,
                    'status': 'active'
                },
                {
                    'title': 'Energy Conservation 💡',
                    'description': 'Reduce home energy usage by 20% for a week through conscious conservation efforts',
                    'category': 'energy',
                    'difficulty': 'medium',
                    'type': 'one-time',
                    'xp_reward': 40,
                    'points_reward': 20,
                    'status': 'active'
                },
                {
                    'title': 'Water Warrior 💧',
                    'description': 'Take shorter showers and fix any leaky faucets to conserve water',
                    'category': 'water',
                    'difficulty': 'easy',
                    'type': 'one-time',
                    'xp_reward': 35,
                    'points_reward': 18,
                    'status': 'active'
                },
                {
                    'title': 'Local Food Hero 🥬',
                    'description': 'Buy only locally sourced food for a week to reduce food miles',
                    'category': 'food',
                    'difficulty': 'medium',
                    'type': 'one-time',
                    'xp_reward': 45,
                    'points_reward': 22,
                    'status': 'active'
                },
                {
                    'title': 'Recycling Champion ♻️',
                    'description': 'Properly sort and recycle all waste for a month',
                    'category': 'waste',
                    'difficulty': 'hard',
                    'type': 'one-time',
                    'xp_reward': 60,
                    'points_reward': 30,
                    'status': 'active'
                },
                {
                    'title': 'Eco Educator 📚',
                    'description': 'Teach someone about environmental conservation and share knowledge',
                    'category': 'education',
                    'difficulty': 'medium',
                    'type': 'recurring',
                    'xp_reward': 55,
                    'points_reward': 25,
                    'status': 'active'
                }
            ]
            
            for challenge_data in sample_challenges:
                challenge_data['total_completions'] = 0
                challenge_data['created_at'] = datetime.utcnow()
                challenge_data['updated_at'] = datetime.utcnow()
                
                self.challenges_ref.add(challenge_data)
            
            logger.info("Seeded challenge database with sample data")
            return True
            
        except Exception as e:
            logger.error(f"Error seeding challenges: {str(e)}")
            return False