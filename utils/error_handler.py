"""
Error Handler for EcoLearn Platform
Centralized error handling and logging
"""

from flask import jsonify
import logging
import traceback

logger = logging.getLogger(__name__)

class EcoLearnError(Exception):
    """Base exception class for EcoLearn platform"""
    def __init__(self, message, status_code=500, error_code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

class ValidationError(EcoLearnError):
    """Raised when input validation fails"""
    def __init__(self, message, field=None):
        super().__init__(message, status_code=400, error_code='VALIDATION_ERROR')
        self.field = field

class AuthenticationError(EcoLearnError):
    """Raised when authentication fails"""
    def __init__(self, message):
        super().__init__(message, status_code=401, error_code='AUTH_ERROR')

class AuthorizationError(EcoLearnError):
    """Raised when user lacks required permissions"""
    def __init__(self, message):
        super().__init__(message, status_code=403, error_code='PERMISSION_ERROR')

class NotFoundError(EcoLearnError):
    """Raised when requested resource is not found"""
    def __init__(self, message):
        super().__init__(message, status_code=404, error_code='NOT_FOUND')

class DatabaseError(EcoLearnError):
    """Raised when database operation fails"""
    def __init__(self, message):
        super().__init__(message, status_code=500, error_code='DATABASE_ERROR')

class ExternalServiceError(EcoLearnError):
    """Raised when external service call fails"""
    def __init__(self, message, service_name=None):
        super().__init__(message, status_code=503, error_code='SERVICE_ERROR')
        self.service_name = service_name

def handle_error(error):
    """
    Central error handler that converts exceptions to JSON responses
    """
    try:
        # Handle custom EcoLearn errors
        if isinstance(error, EcoLearnError):
            logger.warning(f"EcoLearn error: {error.message}")
            return jsonify({
                'error': error.message,
                'error_code': error.error_code,
                'status': 'error'
            }), error.status_code
        
        # Handle common Python exceptions
        elif isinstance(error, ValueError):
            logger.warning(f"Validation error: {str(error)}")
            return jsonify({
                'error': str(error),
                'error_code': 'VALIDATION_ERROR',
                'status': 'error'
            }), 400
        
        elif isinstance(error, KeyError):
            logger.warning(f"Missing key error: {str(error)}")
            return jsonify({
                'error': f'Missing required field: {str(error)}',
                'error_code': 'MISSING_FIELD',
                'status': 'error'
            }), 400
        
        elif isinstance(error, PermissionError):
            logger.warning(f"Permission error: {str(error)}")
            return jsonify({
                'error': 'Insufficient permissions',
                'error_code': 'PERMISSION_DENIED',
                'status': 'error'
            }), 403
        
        # Handle Firebase errors
        elif 'firebase_admin' in str(type(error)):
            logger.error(f"Firebase error: {str(error)}")
            return jsonify({
                'error': 'Service temporarily unavailable',
                'error_code': 'SERVICE_ERROR',
                'status': 'error'
            }), 503
        
        # Handle connection errors
        elif 'ConnectionError' in str(type(error)) or 'TimeoutError' in str(type(error)):
            logger.error(f"Connection error: {str(error)}")
            return jsonify({
                'error': 'Service temporarily unavailable',
                'error_code': 'CONNECTION_ERROR',
                'status': 'error'
            }), 503
        
        # Handle all other exceptions
        else:
            # Log full traceback for debugging
            logger.error(f"Unhandled error: {str(error)}")
            logger.error(traceback.format_exc())
            
            return jsonify({
                'error': 'An unexpected error occurred',
                'error_code': 'INTERNAL_ERROR',
                'status': 'error'
            }), 500
            
    except Exception as e:
        # Failsafe error handling
        logger.critical(f"Error in error handler: {str(e)}")
        return jsonify({
            'error': 'Critical system error',
            'error_code': 'CRITICAL_ERROR',
            'status': 'error'
        }), 500

def log_api_call(endpoint, user_id=None, duration=None, status_code=200):
    """
    Log API call for monitoring and analytics
    """
    try:
        log_data = {
            'endpoint': endpoint,
            'user_id': user_id,
            'duration_ms': duration,
            'status_code': status_code,
            'timestamp': str(datetime.utcnow())
        }
        
        if status_code >= 400:
            logger.warning(f"API call failed: {log_data}")
        else:
            logger.info(f"API call successful: {log_data}")
            
    except Exception as e:
        logger.error(f"Error logging API call: {str(e)}")

def validate_request_data(data, required_fields, optional_fields=None):
    """
    Validate request data against required and optional fields
    """
    try:
        if not data:
            raise ValidationError("Request body cannot be empty")
        
        # Check required fields
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate field types if specified
        if optional_fields:
            for field, expected_type in optional_fields.items():
                if field in data and data[field] is not None:
                    if not isinstance(data[field], expected_type):
                        raise ValidationError(f"Field '{field}' must be of type {expected_type.__name__}")
        
        return True
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        else:
            raise ValidationError(f"Data validation failed: {str(e)}")

def sanitize_user_input(data):
    """
    Sanitize user input to prevent injection attacks
    """
    try:
        if isinstance(data, str):
            # Basic sanitization - remove potentially dangerous characters
            dangerous_chars = ['<', '>', '"', "'", '&', ';']
            sanitized = data
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, '')
            return sanitized.strip()
        
        elif isinstance(data, dict):
            return {key: sanitize_user_input(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [sanitize_user_input(item) for item in data]
        
        else:
            return data
            
    except Exception as e:
        logger.error(f"Error sanitizing input: {str(e)}")
        return data

def format_success_response(data, message=None):
    """
    Format successful API response
    """
    response = {
        'status': 'success',
        'data': data
    }
    
    if message:
        response['message'] = message
    
    return response

def format_error_response(error_message, error_code=None):
    """
    Format error API response
    """
    response = {
        'status': 'error',
        'error': error_message
    }
    
    if error_code:
        response['error_code'] = error_code
    
    return response