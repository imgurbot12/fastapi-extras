"""
Custom FastAPI Exception Handlers
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

#** Variables **#
__all__ = ['pydantic_handler']

#** Functions **#

def pydantic_handler(_: Request, err: RequestValidationError):
    """restructure fastapi pydantic validation errors"""
    errors = {}
    for error in err.errors():
        error.pop('type', None)
        error.pop('url', None)
        # generate key and add message to error-dict
        path = list(error.pop('loc', ()))
        if path and path[0] == 'body':
            path.pop(0)
        key = '->'.join(path)
        errors[key] = [error.pop('msg')]
    return JSONResponse({
        'errors':  errors,
        'message': 'The given data was invalid',
    }, status_code=400)
