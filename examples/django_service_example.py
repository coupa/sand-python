import sand_python
from sand_python.sand_exceptions import SandError
from sand_python.sand_service import SandService

class SandMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request):
        sand = SandService('http://sand-py-test', sand_client_id, sand_client_secret, sand_target_scopes, sand_service_scopes, django_cache)
        is_valid = sand.validate_request(request)['allowed']
        if is_valid != True:
            return JsonResponse({"Message": 'Request not permitted'}, status=401)
        else:
            return None


