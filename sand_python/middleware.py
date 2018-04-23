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



class SandMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request):
        sand_service = SandService()
        print "middleware::process_request::request path: " + request.path
        if 'test' in sys.argv:
            return None
        if request.path == '/health':
            return None
        try:
            # Retrieve client token from the HTTP request object
            client_token = sand_service.get_client_token(request)
            if client_token == False:
                print 'middleware::process_request::No client token'
                return JsonResponse({"Message": 'Missing token'}, status=401)
        except:
            print 'middleware::process_request::Exception while reading client token'
            return JsonResponse({"Message": 'Missing token'}, status=401)

        try:
            # Check if the token is valid and authorized to access the endpoint
            is_valid = sand_service.validate_request(client_token, request)
        except ServiceTokenError as e:
            print 'middleware::process_request::', e.value
            return JsonResponse({"Message": e.value}, status=502)

        if is_valid != True:
            print 'middleware::process_request: Not a valid token'
            return JsonResponse({"Message": 'Request not permitted'}, status=401)
        else:
            return None

