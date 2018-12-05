import datetime
import json
import re
import requests
import sys
import time

# Exception class for raising any SAND service errors
class ServiceTokenError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class ServiceTokenInvalid(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class SandService(object):
    def __init__(self, sand_token_url, sand_client_id, sand_client_secret, cache, service_opts):
        self.sand_token_url = sand_token_url
        self.sand_client_id = sand_client_id
        self.sand_client_secret = sand_client_secret
        self.sand_token_verify_url = service_opts.get("sand_token_verify_url", "")
        self.sand_service_resource = service_opts.get("sand_service_resource", "")
        self.sand_target_scopes = service_opts.get("sand_target_scopes","")
        self.sand_token_cache_key = 'SAND_TOKEN'
        self.cache = cache
        self.sand_token_cache_ttl = 3600

    def get_client_token(self, request):
        try:
            if request.META['HTTP_AUTHORIZATION'].lower().startswith('bearer'):
                pattern = re.compile('Bearer\s*', re.IGNORECASE)
                token = pattern.sub('', request.META['HTTP_AUTHORIZATION'])
                if token == "":
                    raise ServiceTokenError('Did not find any authentication token')
                return token
            else:
                raise ServiceTokenError('Did not find any authentication token')
        except KeyError:
            raise ServiceTokenError('Did not find any authentication token')

    def request_sand_token(self, scopes, max_retries):
        data = [('grant_type', 'client_credentials'), ('scope', scopes)]

        for i in range(0, max_retries):
            try:
                sand_resp = requests.post(self.sand_token_url, auth=(self.sand_client_id, self.sand_client_secret), data=data)
                if sand_resp.status_code != 200:
                    if sand_resp is None or sand_resp.json() is None:
                        error_desc = "No Response Received"
                    else:
                        error_desc = sand_resp.json().get("error_description", "No Response Received")
                    raise ServiceTokenError('Service not able to authenticate with SAND. SAND returned message - ' + error_desc)
                else:
                    data = sand_resp.json()
                    if 'access_token' not in data or data['access_token'] == "":
                        raise ServiceTokenError('Service not able to authenticate with SAND')
                    return data['access_token']
            except ServiceTokenError:
                if i+1 < max_retries:
                    time.sleep((i+1)**2)
        raise ServiceTokenError('Service not able to connect to SAND')

    def get_sand_token(self, options, cached_token_invalid = False):
        max_retries = options["max_retries"]
        if cached_token_invalid == True:
            token = None
            self.cache.delete('SAND_TOKEN', token)
        else:
            token = self.cache.get("SAND_TOKEN")

        if token == None:
            token = self.request_sand_token(options["scopes"], max_retries)
            self.cache.set('SAND_TOKEN', token, self.sand_token_cache_ttl)
        return token

    def get_cache_expiry_secs(self, date_time_str):
        datetime_obj = datetime.datetime.strptime(re.sub(r'.\d{2}Z$', '', date_time_str), "%Y-%m-%dT%H:%M:%S.%f")
        # SAND expiry date time is of format 2018-01-23T00:23:34.7624544Z
        timestamp = time.mktime(datetime_obj.timetuple())
        # Return minimum of self.sand_token_cache_ttl and the time to expire that SAND sent
        if timestamp - time.time() > self.sand_token_cache_ttl:
            return self.sand_token_cache_ttl
        else:
            return (timestamp - time.time())


    def validate_with_sand(self, client_token, service_token, request, options):
        max_retries = options["max_retries"]
        # Scopes should be array scopes: Array(options["scopes"])
        data = {
            "action":options["action"],
            "token": client_token,
            "resource": options["resource"],
            "scopes":options["scopes"],
            "context": options.get("context", "")
            }
        headers = {
            'Authorization': 'Bearer ' + service_token,
            }
        for i in range(0, max_retries):
            try:
                sand_resp = requests.post(
                    self.sand_token_verify_url,
                    headers=headers,
                    data=json.dumps(data)
                    )
                if sand_resp.status_code != 200:
                    if sand_resp is None or sand_resp.json() is None:
                        error_desc = "No Response Received"
                    else:
                        error_desc = sand_resp.json().get("error_description", "No Response Received")
                    raise ServiceTokenError('SAND server returned error - ' + error_desc)
                else:
                    ret_data = sand_resp.json()
                    # Cache the token to the miniumum of self.sand_token_cache_ttl or SAND returned expiry time
                    if ret_data['allowed'] == True:
                        self.cache.set(self.get_client_token_cache_key(client_token), ret_data, self.get_cache_expiry_secs(ret_data['exp']))
                    else:
                        self.cache.set(self.get_client_token_cache_key(client_token), ret_data, self.sand_token_cache_ttl)
                    # TODO: Return the entire data and not just allowd or not
                    return ret_data['allowed']
            except ServiceTokenError:
                if i+1 < max_retries:
                    time.sleep((i+1)**2)
        raise ServiceTokenError('Service not able to connect to SAND')


    def validate_request(self, client_token, request, options):
        max_retries = options["max_retries"]
        # Check if the client request and token are in cache
        get_ret_data = self.cache.get(self.get_client_token_cache_key(client_token))

        # If matches with cached key, clear to load the view
        if get_ret_data != None:
            return get_ret_data
        else:
            # To validate with SAND, first get our own token
            service_token = self.get_sand_token(options)

            # Validate the new client token with SAND
            try:
                sand_response = self.validate_with_sand(client_token, service_token, request, options)
            except ServiceTokenInvalid:
                get_sand_token(options, True)
                sand_response = self.validate_with_sand(client_token, service_token, request, options)
            return sand_response

    def get_client_token_cache_key(self, token):
        # The key is based on the remote ip
        return token + '_' + '_'.join(self.sand_target_scopes.split(' ')) + '_' + self.sand_service_resource

