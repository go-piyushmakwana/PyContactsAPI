from functools import wraps
from quart import request, jsonify, g
import jwt
from config import config

def jwt_required(f):
    """
    A decorator to protect routes with JWT authentication.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Bearer token malformed'}), 401

        if not token:
            return jsonify({'error': 'Token is missing!'}), 401

        try:
            payload = jwt.decode(
                token,
                config.JWT_SECRET_KEY,
                algorithms=["HS256"]
            )
            g.username = payload['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return await f(*args, **kwargs)
    return decorated_function
