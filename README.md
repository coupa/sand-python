# sand-python
A Python client library of SAND for Django based applications

A client who wants to communicate with a service, it will request a token from the OAuth2 server and use this token to make an API call to the service.

When a service receives a request with an OAuth bearer token, it verifies the token with the OAuth2 server to see if the token is allowed to access this service. The service acts like an OAuth2 Resource Server that verifies the token.

## Features

* The authentication is done using the "client credentials" grant type in OAuth2.
* The tokens are cached on both the client and the service sides. The cache store is configurable to use a cache store like Django's cache.

## Instructions

### For Micro Service

```
pip install -e https://github.com/coupa/sand-python

In settings.py of the Django App:

INSTALLED_APPS = (
    ...
    ...
    'sand_python'
)

MIDDLEWARE_CLASSES = (
    ...
    ...
    'sand_python.middleware.SandMiddleware'
)

SAND_SERVICE = {
    "SAND_CLIENT_ID": ''
    "SAND_CLIENT_SECRET": ''
    "SAND_TOKEN_URL": ''
    "SAND_TOKEN_VERIFY_URL": ''
    "SAND_SERVICE_SCOPES": "",
    "SAND_TARGET_SCOPES": "",
    "SAND_SERVICE_RESOURCE": '',
    "SAND_TOKEN_CACHE_TTL": 3600,
}
```

### For a Django based app as a Client

```
In settings.py of the Django App:

SAND_SERVICE = {
    "SAND_CLIENT_ID": '',
    "SAND_CLIENT_SECRET": '', 
    "SAND_TOKEN_URL": '', 
    "SAND_TOKEN_VERIFY_URL": '', 
    "SAND_SERVICE_SCOPES": "",
    "SAND_TARGET_SCOPES": "",
    "SAND_SERVICE_RESOURCE": '',
    "SAND_TOKEN_CACHE_TTL": 3600,
}

from sand_python.sand_client import ApiRequest
API_REQUEST = ApiRequest()
```

In the application for making a post request to a Micro Service:

```
settings.API_REQUEST.post('<API URL>', request_headers={}, request_body="")
```
