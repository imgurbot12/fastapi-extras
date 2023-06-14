"""
FastAPI Simple Synchronous Getters
"""
import inspect
import functools
from typing import Any, Callable, Type

from fastapi import Depends, Form, HTTPException, Query
from fastapi.requests import Request
from fastapi.datastructures import FormData
from fastapi.exceptions import RequestValidationError

from pydantic import BaseModel, ValidationError

#** Variables **#
__all__ = ['body', 'json', 'form', 'as_query', 'as_form', 'as_session']

#** Functions **#

def _depends(func: Callable):
    """decorator to add depends wrapper around function"""
    @functools.wraps(func)
    def wrapper():
        return Depends(func)
    return wrapper

def _pydantic_depends(attr: Callable, model: Type[BaseModel]):
    """generate pydantic form converter for specific attribute"""
    # dynamically generate parameters which add Form(...) wrapper around value
    parameters = []
    for field in model.__fields__.values():
        parameters.append(
             inspect.Parameter(
                 field.alias,
                 inspect.Parameter.POSITIONAL_ONLY,
                 default=attr(...) if field.required else attr(field.default),
                 annotation=field.outer_type_,
             )
         )
    # generate dynamic function to apply new signature parameters
    async def func(**data) -> model:
        try:
            return model(**data)
        except ValidationError as err:
            raise RequestValidationError(errors=err.raw_errors)
    func.__signature__ = inspect.signature(func).replace(parameters=parameters)
    # return depends function to parse form as the model
    return Depends(func)

@_depends
async def body(req: Request) -> bytes:
    """
    retrieve body from http-request
    """
    return await req.body()

@_depends
async def json(req: Request) -> Any:
    """
    retrieve json decoded body from http-request
    """
    return await req.json()

@_depends
async def form(req: Request) -> FormData:
    """
    retrieve form-data from http-request
    """
    return await req.form()

def as_query(model: Type[BaseModel]):
    """
    generate dynamic depends function to parse query as pydantic model
    """
    return _pydantic_depends(Query, model)

def as_form(model: Type[BaseModel]):
    """
    generate dynamic depends function to parse form as pydantic model
    """
    return _pydantic_depends(Form, model)

def as_session(model: Type[BaseModel], status: int = 401):
    """
    generate dynamic depends function to parse session-data as pydantic model
    """
    async def func(req: Request) -> model:
        try:
            session = req.scope.get('session', {})
            return model(**session)
        except ValidationError:
            raise HTTPException(status, 'invalid session state')
    return Depends(func)

