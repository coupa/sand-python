import datetime
import json
import re
import requests
import sys
import time

from .sand_service import SandService
from .sand_service import ServiceTokenError
from django.http import HttpResponse
from django.http import JsonResponse

from . import settings



class SandMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request):
        service_opts = {
            "sand_token_verify_url": settings.SAND_TOKEN_VERIFY_URL,
            "sand_service_resource": settings.SAND_SERVICE_RESOURCE,
            "sand_target_scopes": [settings.SAND_TARGET_SCOPES]
        }
        sand_service = SandService(sand_token_url, sand_client_id, sand_client_secret, cache, service_opts)
        if 'test' in sys.argv:
            return None
        if request.path == '/health':
            return None
        try:
            # Retrieve client token from the HTTP request object
            client_token = sand_service.get_client_token(request)
            if client_token == False:
                return JsonResponse({"Message": 'Missing token'}, status=401)
        except:
            return JsonResponse({"Message": 'Missing token'}, status=401)

        options = {
            "max_retries": 3,
            "action": "any",
            "resource": settings.SAND_SERVICE_RESOURCE,
            "scopes": [settings.SAND_TARGET_SCOPES],
            "context": ""
        }
        try:
            # Check if the token is valid and authorized to access the endpoint
            is_valid = sand_service.validate_request(client_token, request, options)
        except ServiceTokenError as e:
            return JsonResponse({"Message": e.value}, status=502)

        if is_valid != True:
            return JsonResponse({"Message": 'Request not permitted'}, status=401)
        else:
            return None

