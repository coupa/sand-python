# Add the following in app/extensions.py
from app.sand.sand_service import SandService

def configure_sand(app):
    if app.config['ENV'] == 'PROD':
        sand_service = SandService(app.config['SAND_TOKEN_SITE'],
                                   app.config['SAND_CLIENT_ID'],
                                   app.config['SAND_CLIENT_SECRET'],
                                   app.config['SAND_TARGET_SCOPES'],
                                   app.config['SAND_SERVICE_SCOPES'],
                                   app.config['SAND_CACHE'])
        app.sand_service = sand_service


# Add the following in app/api/auth.py
from functools import wraps
from app.sand.sand_service import SandService
from app.exceptions import SandError
from flask import jsonify, request, current_app

def auth(f):
    @wraps(f)
    def sand_auth(*args, **kwargs):
        try:
            # Check if the token is valid and authorized to access the endpoint
            is_valid = current_app.sand_service.validate_request(request)['allowed']
        except SandError as e:
            return (jsonify({'error': e.value}), 502)

        if is_valid is not True:
            return (jsonify({'error': 'Request not permitted'}), 401)
        else:
            return f(*args, **kwargs)
    return sand_auth
