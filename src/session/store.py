"""
FastAPI Session Store Backend Implementations
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, Callable, Optional

#** Variables **#
__all__ = ['Store', 'MemStore']

#** Classes **#

class Store(ABC):
    background_task: Optional[Callable] = None

    @abstractmethod
    async def has(self, key: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def get(self, key: str) -> Optional[dict]:
        raise NotImplementedError()

    @abstractmethod
    async def set(self,
        key:  str,
        data: Optional[dict]      = None, 
        expr: Optional[timedelta] = None
    ):
        raise NotImplementedError()

    @abstractmethod
    async def delete(self, key: str):
        raise NotImplementedError()

@dataclass
class MemRecord:
    __slots__ = ('data', 'expiration')
    data:       dict
    expiration: Optional[datetime]

class MemStore(Store):
    __slots__ = ('store', )

    def __init__(self):
        self.store: Dict[str, MemRecord] = {}

    async def has(self, key: str) -> bool:
        return key in self.store

    async def get(self, key: str) -> Optional[dict]:
        now    = datetime.now()
        record = self.store.get(key)
        if not record:
            return
        if record.expiration and record.expiration <= now:
            del self.store[key]
            return
        return record.data

    async def set(self, 
        key:  str, 
        data: Optional[dict]      = None,
        expr: Optional[timedelta] = None,
    ):
        rexpr  = (datetime.now() + expr) if expr else None
        record = self.store.get(key)
        if not record:
            record = MemRecord(data or {}, rexpr)
            self.store[key] = record
            return
        record.data       = data or {}
        record.expiration = rexpr

    async def delete(self, session_id: str):
        if session_id in self.store:
            del self.store[session_id]

    async def background_task(self):
        now = datetime.now()
        for key in list(self.store.keys()):
            record = self.store[key]
            if record.expiration and record.expiration <= now:
                del self.store[key]

