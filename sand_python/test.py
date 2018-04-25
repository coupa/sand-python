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


class TestSandLib(TestCase):
    def setUp(self):
        self.req_factory = RequestFactory()
        self.ss = SandService()

    #, MagicMock(return_value='YOU R R'))
    @mock.patch('sand_python.sand_service.requests.post')
    def test_service1(self, mock_get):
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


        ## 2. get_service_token
        mock_response = mock.Mock()
        mock_response.status_code = 200
        service_token1 = "service_token_1"
        token_expiry = 1
        mock_response.json.return_value = {"access_token":service_token1,"expires_in":token_expiry,"scope":"coupa","token_type":"bearer"}
        mock_get.return_value = mock_response
        self.assertEqual(self.ss.get_service_token(), service_token1)

        # Sleep for 1 second, for the token to expire. The TTL set to 1 second in the test_settings
        time.sleep(1)
        mock_response2 = mock.Mock()
        mock_response2.status_code = 401
        mock_response2.json.return_value = {"error":"invalid_client","error_description":"Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method)","statusCode":401}
        mock_get.return_value = mock_response2
        with self.assertRaises(ServiceTokenError):
            self.ss.get_service_token()

        ## 3. get_cache_expiry_secs
        # The ttl for token has been set to 1 second in test_settings
        curr = datetime.now()
        dt = timedelta(seconds=3599)
        exp_date = (curr + dt).strftime("%Y-%m-%dT%H:%M:%S.974664101Z")
        self.assertEqual(self.ss.get_cache_expiry_secs(exp_date), 1)


        ## 4. validate_with_sand
        curr = datetime.now()
        dt = timedelta(seconds=3599)
        iat = curr.strftime("%Y-%m-%dT%H:%M:%SZ")
        exp_date = (curr + dt).strftime("%Y-%m-%dT%H:%M:%S.974664101Z")

        mock_response3 = mock.Mock()
        mock_response3.status_code = 200
        mock_response3.json.return_value = {"sub":"coupa-development","scopes":["coupa"],"iss":"https://sand-dev.io.coupadev.com","aud":"coupa-development","iat":iat,"exp":exp_date,"ext":None,"allowed":True}
        mock_get.return_value = mock_response3
        self.assertTrue(self.ss.validate_with_sand(cl_bearer_token1, service_token1, request1))

