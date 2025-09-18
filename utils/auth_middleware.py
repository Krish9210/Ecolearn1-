"""
Authentication Middleware for EcoLearn Platform
Handles Firebase token validation and request authentication
"""

from functools import wraps
from flask import request, jsonify
from firebase_admin import auth
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    """
    Decorator to require authentication for API endpoints
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authorization header required'}), 401
            
            # Extract token (remove 'Bearer ' prefix)
            token = auth_header.replace('Bearer ', '').strip()
            if not token:
                return jsonify({'error': 'Valid token required'}), 401
            
            # Verify token with Firebase
            decoded_token = auth.verify_id_token(token)
            
            # Add user info to request context
            request.current_user = decoded_token
            
            return f(*args, **kwargs)
            
        except auth.ExpiredIdTokenError:
            logger.warning("Expired token provided")
            return jsonify({'error': 'Token expired'}), 401
        except auth.InvalidIdTokenError:
            logger.warning("Invalid token provided")
            return jsonify({'error': 'Invalid token'}), 401
        except auth.RevokedIdTokenError:
            logger.warning("Revoked token provided")
            return jsonify({'error': 'Token revoked'}), 401
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
    
    return decorated_function

def get_user_from_token(token):
    """
    Extract user information from Firebase ID token
    """
    try:
        if not token:
            return None
        
        # Remove 'Bearer ' prefix if present
        clean_token = token.replace('Bearer ', '').strip()
        
        # Verify and decode token
        decoded_token = auth.verify_id_token(clean_token)
        
        return {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email', ''),
            'email_verified': decoded_token.get('email_verified', False),
            'name': decoded_token.get('name', ''),
            'picture': decoded_token.get('picture', ''),
            'firebase_claims': decoded_token
        }
        
    except Exception as e:
        logger.error(f"Error extracting user from token: {str(e)}")
        return None

def require_admin(f):
    """
    Decorator to require admin privileges
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # First check authentication
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authorization header required'}), 401
            
            token = auth_header.replace('Bearer ', '').strip()
            decoded_token = auth.verify_id_token(token)
            
            # Check for admin claim
            is_admin = decoded_token.get('admin', False)
            if not is_admin:
                # Also check custom claims
                custom_claims = decoded_token.get('custom_claims', {})
                is_admin = custom_claims.get('admin', False)
            
            if not is_admin:
                logger.warning(f"Non-admin user attempted admin action: {decoded_token['uid']}")
                return jsonify({'error': 'Admin privileges required'}), 403
            
            request.current_user = decoded_token
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Admin authentication error: {str(e)}")
            return jsonify({'error': 'Admin authentication failed'}), 401
    
    return decorated_function

def require_teacher(f):
    """
    Decorator to require teacher privileges
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # First check authentication
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authorization header required'}), 401
            
            token = auth_header.replace('Bearer ', '').strip()
            decoded_token = auth.verify_id_token(token)
            
            # Check for teacher or admin claim
            is_teacher = decoded_token.get('teacher', False)
            is_admin = decoded_token.get('admin', False)
            
            # Also check custom claims
            custom_claims = decoded_token.get('custom_claims', {})
            is_teacher = is_teacher or custom_claims.get('teacher', False)
            is_admin = is_admin or custom_claims.get('admin', False)
            
            if not (is_teacher or is_admin):
                logger.warning(f"Non-teacher user attempted teacher action: {decoded_token['uid']}")
                return jsonify({'error': 'Teacher privileges required'}), 403
            
            request.current_user = decoded_token
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Teacher authentication error: {str(e)}")
            return jsonify({'error': 'Teacher authentication failed'}), 401
    
    return decorated_function

def optional_auth(f):
    """
    Decorator for endpoints where auth is optional
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header:
                token = auth_header.replace('Bearer ', '').strip()
                if token:
                    try:
                        decoded_token = auth.verify_id_token(token)
                        request.current_user = decoded_token
                    except:
                        # Invalid token, but continue without auth
                        request.current_user = None
                else:
                    request.current_user = None
            else:
                request.current_user = None
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Optional auth error: {str(e)}")
            request.current_user = None
            return f(*args, **kwargs)
    
    return decorated_function

def validate_api_key(f):
    """
    Decorator to validate API key for external integrations
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get API key from header
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({'error': 'API key required'}), 401
            
            # Validate API key (this would check against stored keys)
            # For now, just check for a basic key
            valid_keys = ['ecolearn-api-key-2024']  # This would be in environment variables
            
            if api_key not in valid_keys:
                logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
                return jsonify({'error': 'Invalid API key'}), 401
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return jsonify({'error': 'API key validation failed'}), 401
    
    return decorated_function

def rate_limit(max_requests=100, per_minutes=60):
    """
    Basic rate limiting decorator (simplified implementation)
    In production, use Redis or similar for distributed rate limiting
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This is a simplified implementation
            # In production, implement proper rate limiting with Redis
            try:
                # For now, just pass through
                # TODO: Implement proper rate limiting
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Rate limiting error: {str(e)}")
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator