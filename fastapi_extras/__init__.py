"""
Various FastAPI Extensions and Utilites
"""
from fastapi import FastAPI as BaseFastAPI
from fastapi.exceptions import RequestValidationError

from .handlers import pydantic_handler

#** Variables **#
__all__ = ['FastAPI']

#** Classes **#

class FastAPI(BaseFastAPI):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exception_handler(RequestValidationError)(pydantic_handler)
