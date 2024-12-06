"""
FastAPI Simple Synchronous Getters
"""
import inspect
import logging
import functools
from typing import Any, Awaitable, Callable, Generator, Optional, Type, TypeVar

from fastapi import Form, HTTPException, Query
from fastapi.requests import Request
from fastapi.datastructures import FormData
from fastapi.exceptions import RequestValidationError

from pyderive.extensions.serde import to_dict
from pyderive.abc import has_default
from pyderive.dataclasses import MISSING, FIELD_ATTR
from pyderive.extensions.validate import BaseModel, FieldValidationError

#** Variables **#
__all__ = [
    'body',
    'json',
    'form',

    'as_query',
    'as_form',
    'as_opt_session',
    'as_session'
]

#: getters logging instance
logger = logging.getLogger('fastapi.getters')

#: generic typehint for model object
Model = TypeVar('Model', bound=BaseModel)

#: generic typehint for async callable
AsyncCallback = Callable[..., Awaitable[Model]]

#** Functions **#

@functools.lru_cache(maxsize=None)
def _model_depends(attr: Callable, model: Type[Model]) -> AsyncCallback[Model]:
    """generate base-model form converter for specific attribute"""
    # dynamically generate parameters which add Form(...) wrapper around value
    parameters = []
    for f in getattr(model, FIELD_ATTR):
        default  = None if f.default is MISSING else f.default
        required = not has_default(f)
        parameters.append(
             inspect.Parameter(
                 f.name,
                 inspect.Parameter.POSITIONAL_ONLY,
                 default=attr(...) if required else attr(default),
                 annotation=f.anno,
             )
         )
    # generate dynamic function to apply new signature parameters
    async def func(**data) -> Model:
        try:
            return model(**data)
        except FieldValidationError as err:
            raise RequestValidationError(errors=err.errors())
    signature = inspect.signature(func).replace(parameters=parameters)
    setattr(func, '__signature__', signature)
    return func

async def body(req: Request) -> bytes:
    """
    retrieve body from http-request
    """
    return await req.body()

async def json(req: Request) -> Any:
    """
    retrieve json decoded body from http-request
    """
    return await req.json()

async def form(req: Request) -> FormData:
    """
    retrieve form-data from http-request
    """
    return await req.form()

def as_query(model: Type[Model]) -> AsyncCallback[Model]:
    """
    generate dynamic depends function to parse query as pydantic model
    """
    return _model_depends(Query, model)

def as_form(model: Type[Model]) -> AsyncCallback[Model]:
    """
    generate dynamic depends function to parse form as pydantic model
    """
    return _model_depends(Form, model)

def as_opt_session(
    model:    Type[Model],
    key:      Optional[str] = None,
    **kwargs: Any,
) -> Callable[[Request], Generator[Optional[Model], None, None]]:
    """
    generate dynamic depends function to parse session-data as structured model

    :param model:  model to parse from session object
    :param key:    optional key for placement of model object in session
    :param kwargs: additional arguments to pass during session parsing
    :return:       depends-function to retrieve model value
    """
    def func(req: Request) -> Generator[Optional[Model], None, None]:
        # retrieve session object from request scope
        session = req.session
        if key is not None:
            session = session.get(key, {})
        # supply session model to function
        try:
            value = model.parse_obj(session, **kwargs)
            yield value
        except FieldValidationError as e:
            logger.debug(f'{model.__name__} validation failed: {e.errors()}')
            yield None
            return
        # re-validate and pass model back to storage after completion
        value.validate()
        if key is not None:
            req.scope.setdefault('session', {})
            req.scope['session'][key] = to_dict(value)
        else:
            req.scope['session'] = to_dict(value)
    return func

def as_session(
    model:    Type[Model],
    status:   int           = 403,
    key:      Optional[str] = None,
    **kwargs: Any,
) -> Callable[[Request], Generator[Model, None, None]]:
    """
    generate dynamic depends function to parse session-data as pydantic model

    :param model:  model to parse from session object
    :param status: status to raise on parsing failure
    :param key:    optional key for placement of model object in session
    :param kwargs: additional arguments to pass during session parsing
    :return:       depends-function to retrieve model value
    """
    inner_func = as_opt_session(model, key, **kwargs)
    def func(req: Request) -> Generator[Model, None, None]:
        for result in inner_func(req):
            if result is None:
                raise HTTPException(status, 'invalid session state')
            yield result
    return func
