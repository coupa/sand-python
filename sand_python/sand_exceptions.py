
"""exceptions.py holds exceptions used throughout the api
"""

import inspect
import json

# Exception class for raising any SAND service errors
class SandError(Exception):
    def __init__(self, value, code=502):
        self.value = value
        self.code = code

    def get(self):
        return self.value
