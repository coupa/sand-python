import time
import requests
from .sand_service import SandService
from .sand_exceptions import SandError

class SandClient():


    def __retry(func):
        def sand_request(self, method, request_url, request_headers=None, request_body=None, max_retries=1):
            is_retry = False
            if not max_retries >= 1:
                max_retries = 1
            for i in range(0, max_retries):
                try:
                    resp = func(self, method, request_url, request_headers, request_body, is_retry=is_retry)
                    if resp.status_code == 401:
                        is_retry = True
                        time.sleep((i+1)**2)
                        continue
                except requests.ConnectionError:
                    if i == (max_retries - 1):
                        raise SandError("External Service Down", 502)
                    continue
                break
            return resp
        return sand_request

    def __build_header(self, sand_token, request_headers=None):
        #sand_api = current_app.sand_service

        if request_headers is not None:
            request_headers['Authorization'] = 'Bearer ' + sand_token
        else:
            request_headers = {
                'Authorization': 'Bearer ' + sand_token,
            }
        return request_headers

    @__retry
    def request(self, method, request_url, sand_api, request_headers=None, request_body=None, is_retry=False):
        if is_retry == True:
            sand_api.clear_token_from_cache()
        my_sand_token = sand_api.get_token()
        req = requests.Request(method, request_url, headers=self.__build_header(my_sand_token, request_headers), data=request_body).prepare()
        session = requests.Session()
        return session.send(req)
