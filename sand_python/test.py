#import pytest
import json
#from .sand_service import SandService
#from .middleware import SandMiddleware
from .sand_service import SandService
from .sand_service import ServiceTokenError

from django.test import TestCase
from django.test.client import RequestFactory


class TestSandLib(TestCase):
    def setUp(self):
        self.modify_settings(SAND_SERVICE = {
            "SAND_CLIENT_ID": 'coupa-development',
            "SAND_CLIENT_SECRET": 'cX0@kM^Jwua(-$56.?aQo*Pl',
            "SAND_TOKEN_URL": 'https://sand-dev.io.coupadev.com/oauth2/token',
            "SAND_TOKEN_VERIFY_URL": 'https://sand-dev.io.coupadev.com/warden/token/allowed',
            "SAND_SERVICE_SCOPES": "hydra coupa",
            "SAND_TARGET_SCOPES": "coupa",
            "SAND_SERVICE_RESOURCE": 'coupa:service:fds-dev.io.coupadev.com',
            "SAND_TOKEN_CACHE_TTL": 3600,
        })
        self.req_factory = RequestFactory()
        

    def test_service(self):
        ss = SandService()
        token = ss.get_service_token()
        self.assertIsNotNone(token)

        request = self.req_factory.get('/something', HTTP_AUTHORIZATION="Bearer " + token)
        cl_token = ss.get_client_token(request)
        self.assertEqual(token, cl_token)

        self.assertTrue(ss.validate_request(cl_token, request))

        request2 = self.req_factory.get('/something', HTTP_AUTHORIZATION="Bearer ")
        cl_token2 = ''
        with self.assertRaises(ServiceTokenError) as e:
            cl_token2 = ss.get_client_token(request2)
        self.assertEqual(str(e.exception), "'Did not find any authentication token'")
        self.assertFalse(ss.validate_request(cl_token2, request2))
