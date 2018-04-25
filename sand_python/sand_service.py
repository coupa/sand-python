import datetime
import json
import re
import requests
import sys
import time

from . import settings

# Setting max_retries not in config. If you want more, talk to platform team to know the consequences
max_retries = 3


# Exception class for raising any SAND service errors
class ServiceTokenError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class SandService(object):

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

    def get_service_token(self):
        service_token = settings.CACHE.get('SERVICE_TOKEN')
        if service_token == None:
            data = [('grant_type', 'client_credentials'), ('scope', settings.SAND_SERVICE_SCOPES)]
            for i in range(0, max_retries):
                try:
                    sand_resp = requests.post(settings.SAND_TOKEN_URL, auth=(settings.SAND_CLIENT_ID, settings.SAND_CLIENT_SECRET), data=data)
                    if sand_resp.status_code != 200:
                        print "middleware::get_service_token::", sand_resp.json()["error_description"]
                        raise ServiceTokenError('Service not able to authenticate with SAND')
                    else:
                        data = sand_resp.json()
                        if 'access_token' not in data or data['access_token'] == "":
                            raise ServiceTokenError('Service not able to authenticate with SAND')
                        settings.CACHE.set('SERVICE_TOKEN', data['access_token'], settings.SAND_TOKEN_CACHE_TTL)
                        return data['access_token']
                except:
                    print "middleware::get_service_token::", sys.exc_info()[0], sys.exc_info()[1]
                    if i+1 < max_retries:
                        time.sleep((i+1)**2)
            raise ServiceTokenError('Service not able to connect to SAND')
        else:
            return service_token

    def get_cache_expiry_secs(self, date_time_str):
        datetime_obj = datetime.datetime.strptime(re.sub(r'.\d{2}Z$', '', date_time_str), "%Y-%m-%dT%H:%M:%S.%f")
        # SAND expiry date time is of format 2018-01-23T00:23:34.7624544Z
        timestamp = time.mktime(datetime_obj.timetuple())
        # Return minimum of settings.SAND_TOKEN_CACHE_TTL and the time to expire that SAND sent
        if timestamp - time.time() > settings.SAND_TOKEN_CACHE_TTL:
            return settings.SAND_TOKEN_CACHE_TTL
        else:
            timestamp - time.time()


    def validate_with_sand(self, client_token, service_token, request):
        data = {
            "action":"any",
            "token": client_token,
            "resource":settings.SAND_SERVICE_RESOURCE,
            "scopes":[settings.SAND_TARGET_SCOPES]
            }
        headers = {
            'Authorization': 'Bearer ' + service_token,
            }
        sand_resp = requests.post(
            settings.SAND_TOKEN_VERIFY_URL,
            headers=headers,
            data=json.dumps(data)
            )
        if sand_resp.status_code != 200:
            print "middleware::validate_with_sand::", sand_resp.json()["error_description"]
            raise ServiceTokenError('SAND server returned error.')
        else:
            ret_data = sand_resp.json()
            # Cache the token to the miniumum of settings.SAND_TOKEN_CACHE_TTL or SAND returned expiry time
            if ret_data['allowed'] == True:
                settings.CACHE.set(self.get_client_token_cache_key(client_token), ret_data, self.get_cache_expiry_secs(ret_data['exp']))
            else:
                settings.CACHE.set(self.get_client_token_cache_key(client_token), ret_data, settings.SAND_TOKEN_CACHE_TTL)
            return ret_data['allowed']


    def validate_request(self, client_token, request):
        # Check if the client request and token are in cache
        get_ret_data = settings.CACHE.get(self.get_client_token_cache_key(client_token))

        # If matches with cached key, clear to load the view
        if get_ret_data != None:
            print 'middleware::validate_request: found cached key and returning the cached response'
            return get_ret_data['allowed']
        else:
            print 'middleware::validate_request: did not find cached key'
            # To validate with SAND, first get our own token
            service_token = self.get_service_token()

            # Validate the new client token with SAND
            return self.validate_with_sand(client_token, service_token, request)
                

    def get_client_token_cache_key(self, token):
        # The key is based on the remote ip
        return token + ','.join(settings.SAND_TARGET_SCOPES.split(' '))

