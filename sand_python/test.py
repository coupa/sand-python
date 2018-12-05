import json
import time
from datetime import datetime, timedelta
from .sand_service import SandService
from .sand_service import ServiceTokenError

from django.test import TestCase, override_settings, modify_settings
from django.test.client import RequestFactory

import requests
import mock
from mock import patch, MagicMock


##
## To run the tests, call the following command in parent directory of the lib
## python -m sand_python.runtest
##

def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if args[0] == 'http://sand-py-test/token_verify':
        curr = datetime.now()
        dt = timedelta(seconds=3599)
        iat = curr.strftime("%Y-%m-%dT%H:%M:%SZ")
        exp_date = (curr + dt).strftime("%Y-%m-%dT%H:%M:%S.974664101Z")
        return MockResponse({"sub":"sand-development","scopes":["some_sand"],"iss":"http://sand-py-test/token_verify","aud":"sand-development","iat":iat,"exp":exp_date,"ext":None,"allowed":True}, 200)
    elif args[0] == 'http://sand-py-test/token':
        return MockResponse({"error":"invalid_client","error_description":"Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method)","statusCode":401}, 401)

    return MockResponse(None, 404)

class dummy_cache:
    def get(self):
        return "some key"
    def set(self, key, val, ttl):
        return True
    def delete(self, key, val):
        return True


class TestSandLib(TestCase):
    def setUp(self):
        self.req_factory = RequestFactory()
        self.ss = SandService("http://sand-py-test/token", "sand_client_id", "sand_client_secret", dummy_cache(), {"sand_token_verify_url": "http://sand-py-test/token_verify", "sand_service_resource":"sand_service_resource", "sand_target_scopes": "sand_target_scopes"})

    # Even though we are mocking POST request, the mock method is called mock_get
    @mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_get)
    @mock.patch('sand_python.sand_service.time.time')
    def test_service1(self, mock_get, mock_time):
        ## 1. get_client_token
        cl_bearer_token1 = "CLIENT_ACCESS_TOKEN"
        request1 = self.req_factory.get("https://mock-fds.com/something", HTTP_AUTHORIZATION="Bearer " + cl_bearer_token1)
        self.assertEqual(self.ss.get_client_token(request1), cl_bearer_token1)

        request2 = self.req_factory.get("https://mock-fds.com/something", HTTP_AUTHORIZATION="bearer " + cl_bearer_token1)
        self.assertEqual(self.ss.get_client_token(request2), cl_bearer_token1)

        request3 = self.req_factory.get("https://mock-fds.com/something", HTTP_AUTHORIZATION="arer " + cl_bearer_token1)
        with self.assertRaises(ServiceTokenError):
            self.ss.get_client_token(request3)

        request4 = self.req_factory.get("https://mock-fds.com/something", HTTP_AUTHORIZATION="Bearer ")
        with self.assertRaises(ServiceTokenError):
            self.ss.get_client_token(request4)


        with self.assertRaises(ServiceTokenError):
            self.ss.request_sand_token("some_sand", 3)

        ## 2. get_sand_token
        service_token1 = "service_token_1"
        mock_request_sand_token = mock.MagicMock(return_value=service_token1)
        self.ss.request_sand_token = mock_request_sand_token 
        sand_request_options = {"max_retries": 3, "action": "any", "resource": "some_resource", "scopes": "scope"}
        # Force sand token request as we are not testing cache retrieval
        self.assertEqual(self.ss.get_sand_token(sand_request_options, True), service_token1)

        ## 3. validate_with_sand
        service_token1 = "service_token_1"
        cl_bearer_token1 = "CLIENT_ACCESS_TOKEN"
        request1 = self.req_factory.get("https://mock-fds.com/something", HTTP_AUTHORIZATION="Bearer " + cl_bearer_token1)
        curr = datetime.now()
        dt = timedelta(seconds=3599)
        iat = curr.strftime("%Y-%m-%dT%H:%M:%SZ")
        exp_date = (curr + dt).strftime("%Y-%m-%dT%H:%M:%S.974664101Z")
        self.assertTrue(self.ss.validate_with_sand(cl_bearer_token1, service_token1, request1, sand_request_options))


        ## 4. request_sand_token
        mock_response = mock.Mock()
        mock_response.status_code = 200
        service_token1 = "service_token_1"
        token_expiry = 1
        sand_request_options = {"max_retries": 3, "action": "any", "resource": "some_resource", "scopes": "scope"}
        mock_response.json.return_value = {"access_token":service_token1,"expires_in":token_expiry,"scope":"some_sand","token_type":"bearer"}
        mock_get.return_value = mock_response
        self.assertEqual(self.ss.request_sand_token(sand_request_options), service_token1)

