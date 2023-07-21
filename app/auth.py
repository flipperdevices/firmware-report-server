from functools import wraps

from flask import request


def validate_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]

        # todo: load token from .envs
        if not token or "*" != token:
            return {
                "status": "error",
                "details": "Invalid Authentication token!",
            }, 401
        return f(*args, **kwargs)

    return decorated
