from .sand_service import SandService
import requests


class ApiRequest():
    def post(self, request_url, request_headers=None, request_body=None):
        sand_api = SandService()
        if request_headers != None:
            request_headers['Authorization'] = 'Bearer ' + sand_api.get_service_token()
        else:
            request_headers = {
                'Authorization': 'Bearer ' + sand_api.get_service_token(),
            }
        return requests.post(request_url, headers=request_headers, data=request_body)

    def get(self, request_url, request_headers=None):
        sand_api = SandService()
        if request_headers != None:
            request_headers['Authorization'] = 'Bearer ' + sand_api.get_service_token()
        else:
            request_headers = {
                'Authorization': 'Bearer ' + sand_api.get_service_token(),
            }
        return requests.get(request_url, headers=request_headers)
