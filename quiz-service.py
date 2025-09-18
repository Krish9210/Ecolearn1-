"""
Quiz Service for EcoLearn Platform
Handles quiz management, submission, grading, and analytics
"""

from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class QuizService:
    def __init__(self, db):
        self.db = db
        self.quizzes_ref = db.collection('quizzes')
        self.attempts_ref = db.collection('attempts')
        self.users_ref = db.collection('users')
    
    def get_all_quizzes(self):
        """
        Get all available quizzes (without answers)
        """
        try:
            quizzes = []
            quiz_docs = self.quizzes_ref.where('status', '==', 'active').stream()
            
            for quiz_doc in quiz_docs:
                quiz_data = quiz_doc.to_dict()
                
                # Remove correct answers from questions for security
                sanitized_questions = []
                for question in quiz_data.get('questions', []):
                    sanitized_question = {
                        'id': question.get('id'),
                        'question': question.get('question'),
                        'options': question.get('options', []),
                        'difficulty': question.get('difficulty', 'medium'),
                        'category': question.get('category', 'general')
                    }
                    sanitized_questions.append(sanitized_question)
                
                quiz_summary = {
                    'id': quiz_doc.id,
                    'title': quiz_data.get('title'),
                    'description': quiz_data.get('description'),
                    'difficulty': quiz_data.get('difficulty'),
                    'category': quiz_data.get('category'),
                    'questions': sanitized_questions,
                    'total_questions': len(sanitized_questions),
                    'points_per_question': quiz_data.get('points_per_question', 10),
                    'time_limit_minutes': quiz_data.get('time_limit_minutes'),
                    'created_at': quiz_data.get('created_at')
                }
                
                quizzes.append(quiz_summary)
            
            # Sort by creation date (newest first)
            quizzes.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
            
            return quizzes
            
        except Exception as e:
            logger.error(f"Error getting all quizzes: {str(e)}")
            raise ValueError(f"Failed to get quizzes: {str(e)}")
    
    def get_quiz_by_id(self, quiz_id):
        """
        Get specific quiz by ID (without answers)
        """
        try:
            quiz_doc = self.quizzes_ref.document(quiz_id).get()
            if not quiz_doc.exists:
                raise ValueError("Quiz not found")
            
            quiz_data = quiz_doc.to_dict()
            
            # Remove answers for security
            sanitized_questions = []
            for question in quiz_data.get('questions', []):
                sanitized_question = {
                    'id': question.get('id'),
                    'question': question.get('question'),
                    'options': question.get('options', []),
                    'difficulty': question.get('difficulty', 'medium'),
                    'category': question.get('category', 'general'),
                    'explanation_preview': question.get('explanation', '')[:100] + '...' if len(question.get('explanation', '')) > 100 else question.get('explanation', '')
                }
                sanitized_questions.append(sanitized_question)
            
            return {
                'id': quiz_doc.id,
                'title': quiz_data.get('title'),
                'description': quiz_data.get('description'),
                'difficulty': quiz_data.get('difficulty'),
                'category': quiz_data.get('category'),
                'questions': sanitized_questions,
                'points_per_question': quiz_data.get('points_per_question', 10),
                'time_limit_minutes': quiz_data.get('time_limit_minutes'),
                'total_questions': len(sanitized_questions)
            }
            
        except Exception as e:
            logger.error(f"Error getting quiz by ID: {str(e)}")
            raise ValueError(f"Failed to get quiz: {str(e)}")
    
    def submit_quiz(self, user_id, quiz_id, answers):
        """
        Submit quiz answers and return graded results
        """
        try:
            # Get quiz with correct answers
            quiz_doc = self.quizzes_ref.document(quiz_id).get()
            if not quiz_doc.exists:
                raise ValueError("Quiz not found")
            
            quiz_data = quiz_doc.to_dict()
            questions = quiz_data.get('questions', [])
            points_per_question = quiz_data.get('points_per_question', 10)
            
            # Grade the quiz
            results = self._grade_quiz(questions, answers, points_per_question)
            
            # Calculate XP earned (base XP + bonuses)
            base_xp = results['correct_answers'] * 10
            bonus_xp = 0
            
            # Perfect score bonus
            if results['score_percentage'] == 100:
                bonus_xp += 20
            # High score bonus (80%+)
            elif results['score_percentage'] >= 80:
                bonus_xp += 10
            
            total_xp = base_xp + bonus_xp
            
            # Create attempt record
            attempt_data = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'quiz_id': quiz_id,
                'quiz_title': quiz_data.get('title'),
                'answers': answers,
                'score': results['correct_answers'],
                'total_questions': results['total_questions'],
                'score_percentage': results['score_percentage'],
                'earned_xp': total_xp,
                'time_taken_seconds': answers.get('time_taken_seconds', 0),
                'question_results': results['question_results'],
                'created_at': datetime.utcnow()
            }
            
            # Save attempt to Firestore
            self.attempts_ref.add(attempt_data)
            
            # Update quiz statistics
            self._update_quiz_stats(quiz_id, results['score_percentage'])
            
            logger.info(f"Quiz submitted - User: {user_id}, Quiz: {quiz_id}, Score: {results['score_percentage']}%")
            
            return {
                'attempt_id': attempt_data['id'],
                'score': results['correct_answers'],
                'total_questions': results['total_questions'],
                'score_percentage': results['score_percentage'],
                'earned_xp': total_xp,
                'base_xp': base_xp,
                'bonus_xp': bonus_xp,
                'question_results': results['question_results'],
                'quiz_completed': True
            }
            
        except Exception as e:
            logger.error(f"Error submitting quiz: {str(e)}")
            raise ValueError(f"Failed to submit quiz: {str(e)}")
    
    def get_user_quiz_attempts(self, user_id, quiz_id=None):
        """
        Get user's quiz attempts, optionally filtered by quiz_id
        """
        try:
            query = self.attempts_ref.where('user_id', '==', user_id)
            
            if quiz_id:
                query = query.where('quiz_id', '==', quiz_id)
            
            attempts = []
            for attempt_doc in query.order_by('created_at', direction='DESCENDING').stream():
                attempt_data = attempt_doc.to_dict()
                
                # Remove sensitive data
                sanitized_attempt = {
                    'id': attempt_data.get('id'),
                    'quiz_id': attempt_data.get('quiz_id'),
                    'quiz_title': attempt_data.get('quiz_title'),
                    'score': attempt_data.get('score'),
                    'total_questions': attempt_data.get('total_questions'),
                    'score_percentage': attempt_data.get('score_percentage'),
                    'earned_xp': attempt_data.get('earned_xp'),
                    'time_taken_seconds': attempt_data.get('time_taken_seconds'),
                    'created_at': attempt_data.get('created_at')
                }
                
                attempts.append(sanitized_attempt)
            
            return attempts
            
        except Exception as e:
            logger.error(f"Error getting user quiz attempts: {str(e)}")
            raise ValueError(f"Failed to get quiz attempts: {str(e)}")
    
    def create_quiz(self, created_by, title, description, difficulty, questions, points_per_question=10):
        """
        Create a new quiz (teacher/admin function)
        """
        try:
            # Validate questions format
            if not questions or len(questions) == 0:
                raise ValueError("Quiz must have at least one question")
            
            validated_questions = []
            for i, question in enumerate(questions):
                if not all(key in question for key in ['question', 'options', 'correct']):
                    raise ValueError(f"Question {i+1} is missing required fields")
                
                validated_question = {
                    'id': str(uuid.uuid4()),
                    'question': question['question'],
                    'options': question['options'],
                    'correct': question['correct'],
                    'explanation': question.get('explanation', ''),
                    'difficulty': question.get('difficulty', difficulty),
                    'category': question.get('category', 'environmental')
                }
                validated_questions.append(validated_question)
            
            quiz_data = {
                'title': title,
                'description': description,
                'difficulty': difficulty,
                'category': 'environmental',
                'questions': validated_questions,
                'points_per_question': points_per_question,
                'time_limit_minutes': 30,  # Default 30 minutes
                'created_by': created_by,
                'status': 'active',
                'total_attempts': 0,
                'average_score': 0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Save to Firestore
            quiz_ref = self.quizzes_ref.add(quiz_data)
            quiz_id = quiz_ref[1].id
            
            logger.info(f"Created new quiz: {title} by user {created_by}")
            
            return {
                'quiz_id': quiz_id,
                'title': title,
                'total_questions': len(validated_questions),
                'message': 'Quiz created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating quiz: {str(e)}")
            raise ValueError(f"Failed to create quiz: {str(e)}")
    
    def _grade_quiz(self, questions, answers, points_per_question):
        """
        Grade quiz answers against correct answers
        """
        correct_answers = 0
        question_results = []
        
        for question in questions:
            question_id = question.get('id')
            correct_option = question.get('correct')
            user_answer = answers.get(question_id)
            
            is_correct = user_answer == correct_option
            if is_correct:
                correct_answers += 1
            
            question_result = {
                'question_id': question_id,
                'question': question.get('question'),
                'correct_answer': correct_option,
                'user_answer': user_answer,
                'is_correct': is_correct,
                'explanation': question.get('explanation', ''),
                'points_earned': points_per_question if is_correct else 0
            }
            question_results.append(question_result)
        
        total_questions = len(questions)
        score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        return {
            'correct_answers': correct_answers,
            'total_questions': total_questions,
            'score_percentage': round(score_percentage, 2),
            'question_results': question_results
        }
    
    def _update_quiz_stats(self, quiz_id, score_percentage):
        """
        Update quiz statistics after submission
        """
        try:
            quiz_ref = self.quizzes_ref.document(quiz_id)
            quiz_doc = quiz_ref.get()
            
            if quiz_doc.exists:
                quiz_data = quiz_doc.to_dict()
                current_attempts = quiz_data.get('total_attempts', 0)
                current_avg = quiz_data.get('average_score', 0)
                
                # Calculate new average
                new_attempts = current_attempts + 1
                new_average = ((current_avg * current_attempts) + score_percentage) / new_attempts
                
                # Update quiz document
                quiz_ref.update({
                    'total_attempts': new_attempts,
                    'average_score': round(new_average, 2),
                    'updated_at': datetime.utcnow()
                })
                
        except Exception as e:
            logger.error(f"Error updating quiz stats: {str(e)}")
    
    def seed_quizzes(self):
        """
        Seed database with initial quiz data
        """
        try:
            sample_quizzes = [
                {
                    'title': 'Environmental Basics',
                    'description': 'Test your knowledge of basic environmental concepts',
                    'difficulty': 'easy',
                    'category': 'environmental',
                    'points_per_question': 10,
                    'time_limit_minutes': 15,
                    'status': 'active',
                    'created_by': 'system',
                    'questions': [
                        {
                            'id': str(uuid.uuid4()),
                            'question': 'What percentage of plastic waste is currently recycled globally?',
                            'options': ['Less than 10%', 'About 25%', 'About 50%', 'Over 75%'],
                            'correct': 0,
                            'explanation': 'Less than 10% of plastic waste is actually recycled globally, highlighting the urgent need for better waste management.',
                            'difficulty': 'medium',
                            'category': 'waste'
                        },
                        {
                            'id': str(uuid.uuid4()),
                            'question': 'Which renewable energy source produces the most electricity worldwide?',
                            'options': ['Solar', 'Wind', 'Hydroelectric', 'Geothermal'],
                            'correct': 2,
                            'explanation': 'Hydroelectric power is currently the largest source of renewable electricity globally.',
                            'difficulty': 'medium',
                            'category': 'energy'
                        },
                        {
                            'id': str(uuid.uuid4()),
                            'question': 'How much water can a leaky faucet waste per day?',
                            'options': ['1 gallon', '5 gallons', '10 gallons', '20+ gallons'],
                            'correct': 3,
                            'explanation': 'A single leaky faucet can waste more than 20 gallons of water per day!',
                            'difficulty': 'easy',
                            'category': 'water'
                        },
                        {
                            'id': str(uuid.uuid4()),
                            'question': 'What is the main cause of deforestation worldwide?',
                            'options': ['Urban development', 'Agriculture', 'Mining', 'Natural disasters'],
                            'correct': 1,
                            'explanation': 'Agriculture is responsible for about 80% of global deforestation.',
                            'difficulty': 'medium',
                            'category': 'forests'
                        },
                        {
                            'id': str(uuid.uuid4()),
                            'question': 'Which transportation method has the lowest carbon footprint per kilometer?',
                            'options': ['Car', 'Bus', 'Train', 'Airplane'],
                            'correct': 2,
                            'explanation': 'Trains are generally the most carbon-efficient form of motorized transportation.',
                            'difficulty': 'medium',
                            'category': 'transportation'
                        }
                    ]
                },
                {
                    'title': 'Climate Change Science',
                    'description': 'Advanced quiz on climate change and global warming',
                    'difficulty': 'hard',
                    'category': 'climate',
                    'points_per_question': 15,
                    'time_limit_minutes': 20,
                    'status': 'active',
                    'created_by': 'system',
                    'questions': [
                        {
                            'id': str(uuid.uuid4()),
                            'question': 'What is the current atmospheric CO2 concentration?',
                            'options': ['350 ppm', '400 ppm', '420 ppm', '450 ppm'],
                            'correct': 2,
                            'explanation': 'As of 2024, atmospheric CO2 levels have exceeded 420 parts per million, the highest in human history.',
                            'difficulty': 'hard',
                            'category': 'climate'
                        },
                        {
                            'id': str(uuid.uuid4()),
                            'question': 'Which greenhouse gas has the highest global warming potential?',
                            'options': ['Carbon dioxide', 'Methane', 'Nitrous oxide', 'Fluorinated gases'],
                            'correct': 3,
                            'explanation': 'Some fluorinated gases have global warming potentials thousands of times higher than CO2.',
                            'difficulty': 'hard',
                            'category': 'climate'
                        }
                    ]
                }
            ]
            
            for quiz_data in sample_quizzes:
                quiz_data['total_attempts'] = 0
                quiz_data['average_score'] = 0
                quiz_data['created_at'] = datetime.utcnow()
                quiz_data['updated_at'] = datetime.utcnow()
                
                self.quizzes_ref.add(quiz_data)
            
            logger.info("Seeded quiz database with sample data")
            return True
            
        except Exception as e:
            logger.error(f"Error seeding quizzes: {str(e)}")
            return False