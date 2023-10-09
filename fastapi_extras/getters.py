"""
FastAPI Simple Synchronous Getters
"""
import inspect
import functools
from typing import Any, Callable, Generator, Type, TypeVar

from fastapi import Depends, Form, HTTPException, Query
from fastapi.requests import Request
from fastapi.datastructures import FormData
from fastapi.exceptions import RequestValidationError

from pyderive.extensions.serde import to_dict
from pyderive.dataclasses import MISSING, FIELD_ATTR
from pyderive.extensions.validate import BaseModel, FieldValidationError

#** Variables **#
__all__ = ['body', 'json', 'form', 'as_query', 'as_form', 'as_session']

#: generic typehint for model object
Model = TypeVar('Model', bound=BaseModel)

#** Functions **#

def _depends(func: Callable):
    """decorator to add depends wrapper around function"""
    @functools.wraps(func)
    def wrapper():
        return Depends(func)
    return wrapper

@functools.lru_cache(maxsize=None)
def _model_depends(attr: Callable, model: Type[BaseModel]):
    """generate base-model form converter for specific attribute"""
    # dynamically generate parameters which add Form(...) wrapper around value
    parameters = []
    for f in getattr(model, FIELD_ATTR):
        default  = None if f.default is MISSING else f.default
        required = not default \
            or not (None if f.default_factory is MISSING else f.default_factory)
        parameters.append(
             inspect.Parameter(
                 f.name,
                 inspect.Parameter.POSITIONAL_ONLY,
                 default=attr(...) if required else attr(default),
                 annotation=f.anno,
             )
         )
    # generate dynamic function to apply new signature parameters
    async def func(**data) -> model:
        try:
            return model(**data)
        except FieldValidationError as err:
            raise RequestValidationError(errors=err.errors())
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

def as_query(model: Type[Model]) -> Model:
    """
    generate dynamic depends function to parse query as pydantic model
    """
    return _model_depends(Query, model)

def as_form(model: Type[Model]) -> Model:
    """
    generate dynamic depends function to parse form as pydantic model
    """
    return _model_depends(Form, model)

def as_session(model: Type[Model], status: int = 401):
    """
    generate dynamic depends function to parse session-data as pydantic model
    """
    def func(req: Request) -> Generator[Model, None, None]:
        # supply session model to function
        try:
            session = req.scope.get('session', {})
            value   = model(**session)
            yield value
        except FieldValidationError:
            raise HTTPException(status, 'invalid session state')
        # re-validate and pass model back to storage after completion
        value.validate()
        req.scope['session'] = to_dict(value)
    return Depends(func)
