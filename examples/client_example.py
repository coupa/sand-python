import sand_python
from sand_python.sand_exceptions import SandError
from sand_python.sand_service import SandService
from sand_python.sand_client import SandRequest


SAND_TOKEN_SITE = 'http://sand-url'
SAND_CLIENT_ID = 'client-id'
SAND_CLIENT_SECRET = 'client-secret'
SAND_TARGET_SCOPES = 'target_scope'
SAND_SERVICE_SCOPES = 'service_scope'
SAND_MAX_RETRIES = 3
SAND_CACHE = CACHE

app_sand_service = SandService(SAND_TOKEN_SITE,
                               SAND_CLIENT_ID,
                               SAND_CLIENT_SECRET,
                               SAND_TARGET_SCOPES,
                               SAND_SERVICE_SCOPES,
                               SAND_CACHE)

sand_req = SandRequest()
resp = sand_req.request('POST', 'http://some-microservice/', app_sand_service, request_body={"something":"something"})
