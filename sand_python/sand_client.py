from .sand_service import SandService
import requests

class ApiRequest():
    def __init__(self, sand_token_url, sand_client_id, sand_client_secret, cache):
        self.sand_api = SandService(sand_token_url, sand_client_id, sand_client_secret, cache, {})

    def post(self, sand_options, request_url, request_headers=None, request_body=None):
        return get_response(sand_options, request_url, request_headers, request_body, "POST")

    def get(self, sand_options, request_url, request_headers=None):
        return get_response(sand_options, request_url, request_headers, request_body, "GET")

    def put(self, sand_options, request_url, request_headers=None, request_body=None):
        return get_response(sand_options, request_url, request_headers, request_body, "PUT")

    def delete(self, sand_options, request_url, request_headers=None):
        return get_response(sand_options, request_url, request_headers, request_body, "DELETE")

    def get_response(self, sand_options, request_url, request_headers=None, request_body=None, method="GET"):
        max_retries = sand_options["max_retries"]
        token = self.sand_api.get_sand_token(sand_options)
        request_headers = headers_hash(request_headers, token)
        ret_response = api_call(self, request_url, request_headers, request_body, method)
        if ret_response.status_code == 200:
            return ret_response
        else:
            # First time sleep, even if max_retries are 0,
            # we need to try once for handling of SAND token expiry
            time.sleep(1)
            if ret_response.status_code == 401:
                # Currently cached token is invalid, so delete it and get new token
                token = self.sand_api.get_sand_token(sand_options, True)
            for i in range(0, max_retries):
                try:
                    request_headers = headers_hash(request_headers, token)
                    ret_response = api_call(self, request_url, request_headers, request_body, method)
                    if ret_response.status_code == 200:
                        return ret_response
                    else:
                        raise Exception
                except:
                    # TODO go through and retry for max_retries
                    if i+1 < max_retries:
                        time.sleep((i+1)**2)

    def api_call(self, request_url, request_headers=None, request_body=None, method="GET"):
        if method == "GET":
            return requests.get(request_url, headers=request_headers)
        elif method == "POST":
            return requests.post(request_url, headers=request_headers, data=request_body)
        elif method == "PUT":
            return requests.put(request_url, headers=request_headers, data=request_body)
        elif method == "DELETE":
            return requests.delete(request_url, headers=request_headers)

    def headers_hash(request_headers, token):
         if request_headers == None:
             request_headers = {}
         request_headers['Authorization'] = 'Bearer ' + token
         return request_headers
