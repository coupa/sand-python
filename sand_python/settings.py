import sys
import os.path
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings as django_settings
from django.core.cache import cache


class SandServiceSettings(object):
    def __init__(self):
        user_settings = getattr(django_settings, 'SAND_SERVICE', None)
        self.__settings = dict(
            SAND_CLIENT_ID = 'coupa-development',
            SAND_CLIENT_SECRET = '',
            SAND_TOKEN_URL = 'https://sand-dev.io.coupadev.com/oauth2/token',
            SAND_TOKEN_VERIFY_URL = 'https://sand-dev.io.coupadev.com/warden/token/allowed',
            SAND_SERVICE_SCOPES = "hydra coupa",
            SAND_TARGET_SCOPES = "coupa",
            SAND_SERVICE_RESOURCE = '',
            CACHE = None,
            SAND_TOKEN_CACHE_TTL = 3600
        )

        try:
            self.__settings.update(user_settings)
            if "CACHE" not in user_settings or user_settings["CACHE"] == None:
                self.__settings["CACHE"] = cache
        except TypeError:
            pass

    def __getattr__(self, name):
        return self.__settings.get(name)

sys.modules[__name__] = SandServiceSettings()