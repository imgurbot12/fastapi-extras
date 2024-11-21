"""
FastAPI Starlette-Style Session-Management Middleware
"""
import random
import string
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Callable, Literal, Optional, Tuple

from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response
from starlette.background import BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

#** Variables **#
__all__ = ['Store', 'SessionMiddleware']

#: allowed configurations for samesite cookie setting
SameSite = Literal['lax', 'strict', 'none']

#** Functions **#

def new_id() -> str:
    """generate unique session-id for session"""
    content = string.ascii_letters + string.digits
    return ''.join(random.choices(content, k=32))

#** Classes **#

class Store(ABC):
    """
    Session DataStore Backend Interface Definition
    """
    background_task: Optional[Callable] = None

    @abstractmethod
    async def has(self, key: str) -> bool:
        """
        check if storage instance contains session-id key

        :param key: unique session-id key
        :return:    true if session record exists
        """
        raise NotImplementedError()

    @abstractmethod
    async def get(self, key: str) -> Optional[dict]:
        """
        retrieve session record if exists

        :param key: unique session-id key
        :return:    session record (if found)
        """
        raise NotImplementedError()

    @abstractmethod
    async def set(self,
        key:  str,
        data: Optional[dict]      = None,
        expr: Optional[timedelta] = None
    ):
        """
        set new session record with unique session-id key

        :param key:  unique session-id key
        :param data: data to save into session record
        :param expr: expiration of record (if any)
        """
        raise NotImplementedError()

    @abstractmethod
    async def delete(self, key: str):
        """
        delete a record associated with a given session-id if it exists

        :param key: unique session-id key
        """
        raise NotImplementedError()

class SessionMiddleware(BaseHTTPMiddleware):
    """
    Alternative and Better Session Middleware for Starletee and FastAPI
    """
    __slots__ = ('path', 'store', 'expiration', 'cookie', 'cookie_kw')

    def __init__(self,
        app:        ASGIApp,
        cookie:     str                 = 'SESSION',
        path:       str                 = '/',
        max_age:    timedelta           = timedelta(days=14),
        same_site:  SameSite            = 'strict',
        http_only:  bool                = True,
        secure:     bool                = False,
        domain:     Optional[str]       = None,
        store:      Optional[Store]     = None,
        expiration: Optional[timedelta] = timedelta(minutes=5),
    ):
        """
        :param app:        asgi app that gets passed for middleware
        :param cookie:     cookie name to assign for session-id
        :param path:       path that cookie is allowed to use
        :param max_age:     max-age to allow cookie to live (client-side)
        :param same_site:  handling of same-site tracking (lax/strict/none)
        :param http_only:  only allow passing in http-requests (no javascript)
        :param secure:     only allow over https
        :param doman:      only allow for the specified domain
        :param store:      backend datastore for session
        :param expiration: inactivity expiration for server-side session data
        """
        super().__init__(app)
        self.path       = path
        self.store      = store or MemStore()
        self.expiration = expiration
        self.cookie     = cookie
        self.cookie_kw  = dict(
            path=path,
            max_age=int(max_age.total_seconds()),
            samesite=same_site,
            httponly=http_only,
            domain=domain,
            secure=secure,
        )

    async def get(self, sess_id: Optional[str] = None) -> Tuple[str, dict]:
        """
        retrieve session-data using the given session-id
        """
        sid  = sess_id or new_id()
        data = (await self.store.get(sess_id)) if sess_id else None
        return (sid, data or {})

    async def dispatch(self,
        request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        middleware handler for session-management
        """
        # skip processing if path is not is not in uri prefix
        if not request.url.path.startswith(self.path):
            return await call_next(request)
        # lookup session-id if exists and assign session
        sess_id   = request.cookies.get(self.cookie)
        sid, data = await self.get(sess_id)
        request.scope['session'] = data
        # pass to other middleware to generate response
        res = await call_next(request)
        # save session-data into store
        await self.store.set(sid, data, self.expiration)
        # apply new cookie if session was missing
        if sess_id is None:
            res.set_cookie(self.cookie, sid, **self.cookie_kw) #type: ignore
        # apply background task if store has one
        if self.store.background_task:
            tasks          = [res.background] if res.background else []
            res.background = BackgroundTasks(tasks)
            res.background.add_task(self.store.background_task)
        return res

#** Imports **#
from .memory import MemStore
