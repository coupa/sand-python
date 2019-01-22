"""sand_service.py holds sand authentication code both acting as client or service

    get_token(): For incoming requests and outgoing, get a service token
    validate_request(request): Validate incoming request against sand auth allowed server, request needs to have auth token
"""

import json
import re
import requests
from dateutil import parser
from sand_exceptions import SandError

class SandService():
    """
    Sand Authentication
    """

    def __init__(self, sand_token_site, sand_client_id, sand_client_secret, sand_target_scopes, sand_service_scopes, sand_cache):
        if sand_token_site is None:
            raise SandError('sand_token_site value required')
        if sand_client_id is None:
            raise SandError('sand_client_error value required')
        if sand_client_secret is None:
            raise SandError('sand_client_secret value required')
        self.sand_token_site = sand_token_site
        self.sand_client_id = sand_client_id
        self.sand_client_secret = sand_client_secret
        self.sand_token_url = sand_token_site+'/oauth2/token'
        self.sand_token_verify_url = sand_token_site+'/warden/token/allowed'
        self.sand_target_scopes = sand_target_scopes
        self.sand_service_scopes = sand_service_scopes
        self.sand_service_resource = 'coupa:service:'+sand_client_id if sand_client_id else None
        self.cache = sand_cache


    def get_token(self, sand_type='service'):
        """
        Requests a new service token for itself based on type of request. Either acting as a client or service
        """
        if sand_type == 'service':
            scope = self.__service_scope()
        else:
            scope = self.__client_scope()
        service_token = self.cache.get('SERVICE_TOKEN'+'_'+scope)
        if service_token is None:
            data = [('grant_type', 'client_credentials'), ('scope', scope)]
            try:
                sand_resp = requests.post(self.sand_token_url, auth=(self.sand_client_id, self.sand_client_secret), data=data)
                if sand_resp.status_code != 200:
                    # Unable to get token from SAND so responding with the whole json respone for not being a 200 OK
                    # It's the job of the client to retry when making a request and it fails so no retries here
                    raise SandError('Service not able to authenticate with SAND: ' + sand_resp.json()['error_description'], 401)
                else:
                    data = sand_resp.json()
                    if 'access_token' not in data or data['access_token'] == "":
                        raise SandError('Service not able to authenticate with SAND', 401)
                    self.cache.set('SERVICE_TOKEN'+'_'+scope, data['access_token'], data['expires_in'])
                    return data['access_token']
            except requests.ConnectionError:
                # Sand is down, respond with 502 so client does not retry
                raise SandError('Failed to connect to SAND', 502)
        else:
            return service_token


    def validate_request(self, request, opts=None):
        """
        Validates incoming requests with their client_token
        """
        client_token = self.__get_client_token(request)
        # Check if the client request and token are in cache
        get_ret_data = self.cache.get(self.__get_client_token_cache_key(client_token))
        # If matches with cached key, clear to load the view
        if get_ret_data is not None:
            return get_ret_data
        # To validate with SAND, first get our own token
        try:
            service_token = self.get_token()
        except SandError:
            raise SandError('Service not able to authenticate with SAND', 502)
        # Validate the new client token with SAND
        return self.__validate_with_sand(client_token, service_token, opts)


    def __get_client_token(self, request):
        try:
            if request.headers['Authorization'].lower().startswith('bearer'):
                pattern = re.compile('Bearer *', re.IGNORECASE)
                token = pattern.sub('', request.headers['Authorization'])
                if token == "":
                    raise SandError('Did not find any authentication token', 401)
                return token
            raise SandError('Did not find any authentication token', 401)
        except KeyError:
            raise SandError('Did not find any authentication token', 401)


    def __validate_with_sand(self, client_token, service_token, opts=None):
        scopes = self.sand_target_scopes.split(',') if opts is None else opts.split(',')
        data = {
            "action": "any",
            "context": {},
            "token": client_token,
            "resource": self.sand_service_resource,
            "scopes": scopes
        }
        headers = {
            'Authorization': 'Bearer ' + service_token,
        }
        try:
            sand_resp = requests.post(self.sand_token_verify_url, headers=headers, data=json.dumps(data))
            if sand_resp.status_code != 200:
                # Unable to authenticate against sand
                raise SandError('SAND server returned an error: ' + sand_resp.json()['error']['message'], 502)
            else:
                ret_data = sand_resp.json()
                self.cache.set(self.__get_client_token_cache_key(client_token), ret_data, self.__get_cache_expiry_secs(ret_data))
                return ret_data
        except requests.ConnectionError:
            # Sand is down, respond with 502 so client does not retry
            raise SandError('Failed to connect to SAND', 502)


    def __get_cache_expiry_secs(self, data):
        # Use a parser to auto parse date and time coming in
        # SAND expiry date time is of format "2016-09-06T08:32:59.71-07:00"
        if data['allowed'] is True:
            exp_time = int((parser.parse(data['exp']) - parser.parse(data['iat'])).total_seconds())
            return exp_time
        return 0


    def __client_scope(self):
        return self.sand_target_scopes

    def __service_scope(self):
        return self.sand_service_scopes

    def __get_client_token_cache_key(self, token):
        return token + ','.join(self.__client_scope())
