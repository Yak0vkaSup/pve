# app/utils/rate_limiter.py
import time
import redis
from functools import wraps
from flask import request, jsonify, current_app

# Create Redis client directly to avoid circular imports
redis_client = redis.Redis(host='redis', port=6379, db=0)


def rate_limit(seconds=60):
    """
    Rate limiting decorator that prevents users from calling an endpoint 
    more than once within the specified number of seconds.
    
    Args:
        seconds (int): The cooldown period in seconds (default: 60)
    
    Usage:
        @rate_limit(30)  # 30 seconds cooldown
        @token_required
        def my_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Get user ID from request data
            user_id = None
            if request.method == 'POST':
                data = request.get_json()
                user_id = data.get('id') or data.get('user_id')
            else:
                user_id = request.args.get('id') or request.args.get('user_id')
            
            if not user_id:
                return jsonify({'status': 'error', 'message': 'User ID is required for rate limiting'}), 400
            
            # Create a unique key for this user and endpoint
            endpoint_name = f.__name__
            cache_key = f"rate_limit:{user_id}:{endpoint_name}"
            
            try:
                # Check if user has called this endpoint recently
                last_call_time = redis_client.get(cache_key)
                current_time = time.time()
                
                if last_call_time:
                    last_call_time = float(last_call_time)
                    time_elapsed = current_time - last_call_time
                    
                    if time_elapsed < seconds:
                        remaining_time = int(seconds - time_elapsed)
                        return jsonify({
                            'status': 'error', 
                            'message': f'Rate limit exceeded. Please wait {remaining_time} seconds before trying again.',
                            'retry_after': remaining_time
                        }), 429
                
                # Set the current time as the last call time
                redis_client.setex(cache_key, seconds, current_time)
                
                # Proceed with the original function
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Rate limiting error: {str(e)}")
                # If Redis is down, allow the request to proceed
                # but log the error for monitoring
                return f(*args, **kwargs)
        
        return decorated
    return decorator 