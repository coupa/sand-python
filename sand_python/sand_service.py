"""sand_service.py holds sand authentication code both acting as client or service

    get_token(): For incoming requests and outgoing, get a service token
    validate_request(request): Validate incoming request against sand auth allowed server, request needs to have auth token
"""

import json
import re
import requests
from dateutil import parser
from .sand_exceptions import SandError


class SandService:
    """
    Sand Authentication
        sand_target_scopes and sand_scope are strings of space delimited list of scopes like "scope1 scope2"
    """

    def __init__(self, sand_token_site, sand_token_path, sand_token_verify_path, sand_client_id, sand_client_secret,
                 sand_target_scopes, sand_scope, sand_cache, cache_root=''):
        if sand_token_site is None:
            raise SandError('sand_token_site value required')
        if sand_client_id is None:
            raise SandError('sand_client_error value required')
        if sand_client_secret is None:
            raise SandError('sand_client_secret value required')
        self.sand_token_site = sand_token_site
        self.sand_client_id = sand_client_id
        self.sand_client_secret = sand_client_secret
        self.sand_token_path = sand_token_path
        self.sand_token_verify_path = sand_token_verify_path
        self.sand_token_url = sand_token_site + sand_token_path
        self.sand_token_verify_url = sand_token_site + sand_token_verify_path
        # SAND expects scopes as one string with space as delimiter like "scope1 scope2"
        self.sand_target_scopes = sand_target_scopes
        self.sand_scope = sand_scope
        self.sand_service_resource = 'coupa:service:' + sand_client_id
        self.cache = sand_cache
        self.cache_root = cache_root

    def get_token(self):
        """
        Requests a new service token for itself based on type of request. Either acting as a client or service
        """
        # The following is the token of the client/service that is connecting to SAND
        token_cache_key = self.__get_my_token_cache_key(self.__get_self_sand_scope())
        service_token = self.cache.get(token_cache_key)
        if service_token is None:
            data = [('grant_type', 'client_credentials'), ('scope', self.__get_self_sand_scope())]
            try:
                sand_resp = requests.post(self.sand_token_url, auth=(self.sand_client_id, self.sand_client_secret),
                                          data=data)
                if sand_resp.status_code != 200:
                    # Unable to get token from SAND so responding with the whole json respone for not being a 200 OK
                    # It's the job of the client to retry when making a request and it fails so no retries here
                    raise SandError(
                        'Service not able to authenticate with SAND: ' + sand_resp.json()['error_description'], 401)
                else:
                    data = sand_resp.json()
                    if 'access_token' not in data or data['access_token'] == "":
                        raise SandError('Service not able to authenticate with SAND', 401)
                    self.cache.set(token_cache_key, data['access_token'], data['expires_in'])
                    return data['access_token']
            except requests.ConnectionError:
                # Sand is down, respond with 502 so client does not retry
                raise SandError('Failed to connect to SAND', 502)
        else:
            return service_token

    # With the addition of request_headers, as Django and Flask
    # have different formats for headers, we don't need request as param
    def validate_request(self, request_headers, opts={}):
        """
        Validates incoming requests with their client_token
        """
        scopes = opts.get("scopes", self.sand_target_scopes.split(' '))
        client_token = self.__extract_client_token(request_headers)
        # Check if the client request and token are in cache
        get_ret_data = self.cache.get(self.__get_client_token_cache_key(client_token, scopes))
        # If matches with cached key, clear to load the view
        if get_ret_data is not None:
            return get_ret_data
        # To validate with SAND, first get our own token
        try:
            service_token = self.get_token()
        except SandError:
            raise SandError('Service not able to authenticate with SAND', 502)
        # Validate the new client token with SAND
        validation_resp = self.__validate_with_sand(client_token, service_token, scopes, opts)
        self.cache.set(self.__get_client_token_cache_key(client_token, scopes), validation_resp,
                       self.__get_cache_expiry_secs(validation_resp))
        return validation_resp

    def __extract_client_token(self, request_headers):
        try:
            if request_headers['Authorization'].lower().startswith('bearer'):
                pattern = re.compile('Bearer *', re.IGNORECASE)
                token = pattern.sub('', request_headers['Authorization'])
                if token == "":
                    raise SandError('Failed to extract token from the request', 401)
                return token
            raise SandError('Did not find any authentication token', 401)
        except KeyError:
            raise SandError('Did not find any authentication token', 401)

    def __validate_with_sand(self, client_token, service_token, scopes, opts={}):
        data = {
            "action": "any",
            "context": opts.get("context", {}),
            "token": client_token,
            "resource": opts.get("resource", self.sand_service_resource),
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

    def __get_client_token_cache_key(self, token, scopes):
        return self.__get_token_cache_key(token, '_'.join(sorted(scopes)), self.sand_service_resource, 'client_tokens')

    # Clears token of code using this lib
    def clear_token_from_cache(self, scope=None):
        if scope is None:
            scope = self.__get_self_sand_scope()
        self.cache.delete(self.__get_my_token_cache_key(scope))
        return True

    def __get_my_token_cache_key(self, scope):
        # Service's own SAND token does not depend on resource or action
        return self.__get_token_cache_key('SERVICE_TOKEN', '_'.join(sorted(scope.split(" "))))

    def __get_self_sand_scope(self):
        return self.sand_scope

    # cache_type is the sub-dir under root to separate service tokens and client tokens
    def __get_token_cache_key(self, cache_key, scope, resource=None, action=None, cache_type=None):
        ckey = self.cache_root
        if cache_type is not None:
            ckey += '/' + cache_type
        ckey += '/' + cache_key
        ckey += '/' + scope
        if resource is not None:
            ckey += '/' + resource
        if action is not None:
            ckey += '/' + action
        return ckey
