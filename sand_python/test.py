from datetime import datetime, timedelta
import requests
import mock
import os
from werkzeug.contrib.cache import FileSystemCache, SimpleCache

from .sand_exceptions import SandError
from .sand_service import SandService
from .sand_client import SandClient

####   To run the tests use the following command
####   pytest --pyargs test.py

## Different type of mocked requests for external API calls via request

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

def mocked_requests_response1(*args, **kwargs):
    if args[0] == 'http://sand-py-test/warden/token/allowed':
        curr = datetime.now()
        dt = timedelta(seconds=3599)
        iat = curr.strftime("%Y-%m-%dT%H:%M:%SZ")
        exp_date = (curr + dt).strftime("%Y-%m-%dT%H:%M:%S.974664101Z")
        return MockResponse({"sub":"sand-development", "scopes":["some_sand"], "iss":"http://sand-py-test/token_verify", "aud":"sand-development", "iat":iat, "exp":exp_date, "ext":None, "allowed":True}, 200)
    elif args[0] == 'http://sand-py-test/oauth2/token':
        return MockResponse({"access_token":"some token", "expires_in":3599, "scope":"sand_scope", "token_type":"bearer"}, 200)
    else:
        return MockResponse(None, 404)

def mocked_requests_response2(*args, **kwargs):
    if args[0] == 'http://sand-py-test/warden/token/allowed':
        return MockResponse({"allowed":False}, 200)
    elif args[0] == 'http://sand-py-test/oauth2/token':
        return MockResponse({"access_token":"some token", "expires_in":3599, "scope":"sand_scope", "token_type":"bearer"}, 200)
    else:
        return MockResponse(None, 404)

def mocked_requests_response3(*args, **kwargs):
    if args[0] == 'http://sand-py-test/oauth2/token':
        return MockResponse({"error":"invalid_client", "error_description":"Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method)", "statusCode":401}, 401)
    else:
        return MockResponse(None, 404)

def mocked_requests_response4(*args, **kwargs):
    if args[0] == 'http://sand-py-test/oauth2/token':
        return MockResponse({"access_token":"some token", "expires_in":3599, "scope":"sand_scope", "token_type":"bearer"}, 200)
    elif args[0] == 'http://sand-py-test/warden/token/allowed':
        return MockResponse({"error":{"code":500,"message":"Request was denied by default: The request is not allowed"}}, 500)
    else:
        return MockResponse(None, 404)

def mocked_requests_response5(*args, **kwargs):
    if args[0].method == 'POST':
        return MockResponse({"success":"some response"}, 200)
    elif args[0].method == 'GET':
        return MockResponse({"success":"some response"}, 200)
    else:
        return MockResponse(None, 401)


sand_req_from_client = requests.Request('POST', 'http://some-digital-checks/', headers={'Authorization': 'Bearer token'})

ENV = 'TESTING'
TESTING = True
SAND_TOKEN_SITE = 'http://sand-py-test'
SAND_TOKEN_PATH = '/oauth2/token'
SAND_TOKEN_VERIFY_PATH = '/warden/token/allowed'
SAND_CLIENT_ID = 'token'
SAND_CLIENT_SECRET = 'secret'
RATELIMIT_ENABLED = True
WTF_CSRF_ENABLED = False
SEED = 0

SAND_TARGET_SCOPES = 'target_scope1,target_scope2'
SAND_SERVICE_SCOPES = 'service_scope1,service_scope2'
SAND_MAX_RETRIES = 3

SAND_CACHE_DIR = os.getcwd()+'/cache/'
if not os.path.isdir(SAND_CACHE_DIR):
    os.makedirs(os.path.dirname(SAND_CACHE_DIR))
SAND_CACHE = FileSystemCache(SAND_CACHE_DIR)


###### Test Sand Service (Incoming Requests)
###### This tests the authentication method by importing sand directly
# Test successful validation
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response1)
def test_sand_service(mock1):
    sand = SandService('http://sand-py-test', SAND_TOKEN_PATH, SAND_TOKEN_VERIFY_PATH, 'A', 'B', 'C', 'D', SAND_CACHE)
    is_valid = sand.validate_request(sand_req_from_client.headers)['allowed']
    assert is_valid is True
    # Also test cache
    sand = SandService('http://asdfghjkl', SAND_TOKEN_PATH, SAND_TOKEN_VERIFY_PATH, 'A', 'B', 'C', 'D', SAND_CACHE)
    is_valid = sand.validate_request(sand_req_from_client.headers)['allowed']
    # would've been False without cache
    assert is_valid is True
    # Clear cache
    sand.cache.clear()

# Test denied request after getting good service token
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response2)
def test_sand_service_request_denied(mock1):
    sand = SandService('http://sand-py-test', SAND_TOKEN_PATH, SAND_TOKEN_VERIFY_PATH, 'A', 'B', 'C', 'D', SAND_CACHE)
    is_valid = sand.validate_request(sand_req_from_client.headers)['allowed']
    assert is_valid is False
    # Clear cache
    sand.cache.clear()

# Also test denied request after getting good service token but for invalid request
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response4)
def test_sand_service_request_denied_2(mock1):
    try:
        sand = SandService('http://sand-py-test', SAND_TOKEN_PATH, SAND_TOKEN_VERIFY_PATH, 'A', 'B', 'C', 'D', SAND_CACHE)
        sand.validate_request(sand_req_from_client.headers)['allowed']
    except SandError as e:
        assert "SAND server returned an error" in e.get()
    else:
        assert True is False
    # Clear cache
    sand.cache.clear()

# Failed to connect to Sand due to invalid url
def test_sand_service_invalid_url():
    try:
        sand = SandService('http://sdfghjkl', SAND_TOKEN_PATH, SAND_TOKEN_VERIFY_PATH, 'A', 'B', 'C', 'D', SAND_CACHE)
        sand.validate_request(sand_req_from_client.headers)
    except SandError as e:
        assert "Service not able to authenticate" in e.get()
    else:
        assert True is False
    # Clear cache
    sand.cache.clear()

# Test failed to get service token from sand due to authentication issue
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response3)
def test_sand_service_cannot_get_token(mock1):
    try:
        sand = SandService('http://sand-py-test', SAND_TOKEN_PATH, SAND_TOKEN_VERIFY_PATH, 'A', 'B', 'C', 'D', SAND_CACHE)
        sand.validate_request(sand_req_from_client.headers)
    except SandError as e:
        assert "Service not able to authenticate with SAND" in e.get()
    else:
        assert True is False
    # Clear cache
    sand.cache.clear()

###### Test Sand Request (Outgoing Requests)
app_sand_service = SandService(SAND_TOKEN_SITE,
                               SAND_TOKEN_PATH,
                               SAND_TOKEN_VERIFY_PATH,
                               SAND_CLIENT_ID,
                               SAND_CLIENT_SECRET,
                               SAND_TARGET_SCOPES,
                               SAND_SERVICE_SCOPES,
                               SAND_CACHE)

# Test Sand Client with external service down
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response1)
def test_sand_request_external_service_down(mock1):
    #create_global_sand(client)
    sand_req = SandClient()
    try:
        sand_req.request('POST', 'http://some-something/', app_sand_service, request_body={"something":"something"})
    except SandError as e: 
        assert 'External Service Down' in e.get()
    else:
        assert True is False

# Test Sand Client successfully
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response1)
@mock.patch('sand_python.sand_client.requests.Session.send', side_effect=mocked_requests_response5)
def test_sand_request(mock1, mock2):
    #create_global_sand(client)
    sand_req = SandClient()
    resp = sand_req.request('POST', 'http://some-something/', app_sand_service, request_body={"something":"something"})
    assert resp.status_code is 200

# Test Sand Client with retries
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response1)
@mock.patch('sand_python.sand_client.requests.Session.send', side_effect=mocked_requests_response5)
def test_sand_request_retries(mock1, mock2):
    #create_global_sand(client)
    sand_req = SandClient()
    start_time = datetime.utcnow()
    # This should stall the test for a bit because of retrying with sleeps inbetween
    sand_req.request('PUT', 'http://some-something/', app_sand_service, max_retries=3)
    total_time = (datetime.utcnow() - start_time).total_seconds()
    assert total_time > 5

# Test Sand Client with timeout
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response1)
def test_sand_request_timeout(mock1):
    sand_req = SandClient()
    start_time = datetime.utcnow()
    try:
        # TO-DO: figure out how to mock timeouts with the requests library
        sand_req.request('GET', 'http://www.mocky.io/v2/5db23ffa3500006500f54f12?mocky-delay=20000ms', app_sand_service, timeout=10.0)
    except SandError: 
        total_time = (datetime.utcnow() - start_time).total_seconds()
    else:
        assert True is False
    assert total_time > 9 and total_time < 12

# Test Positional Arguments
@mock.patch('sand_python.sand_service.requests.post', side_effect=mocked_requests_response1)
@mock.patch('sand_python.sand_client.requests.Session.send', side_effect=mocked_requests_response5)
def test_sand_request_arguments(mock1, mock2):
    sand_req = SandClient()
    headers = {"Ocr-Type": 'enhanced', "Content-Type": 'application/json', 'X-DES-Client': 'FDS', 'X-Coupa-Instance': 'test', 'X-Correlation-Id': '12345'}
    try:
        sand_req.request('GET', 'http://some-something/', sand_api=app_sand_service, request_headers=headers)
        sand_req.request(sand_api=app_sand_service, request_headers=headers, method='POST', timeout=10, request_url='http://some-something/')
    except:
        assert True is False
