"""
FileSystem Based Storage for Session Data
"""
import os
import pickle
import struct
from io import BytesIO
from datetime import datetime, timedelta
from typing import Any, BinaryIO, NamedTuple, Optional, Dict

from . import Store

#** Variables **#
__all__ = ['FileStore', 'SerialConverter']

#** Classes **#

class IOWrapper:
    """
    Custom IO Wrapper Converting BinaryIO to StringIO
    """
    __slots__ = ('io', 'encoding')

    def __init__(self, io: BinaryIO, encoding: str = 'utf-8'):
        self.io       = io
        self.encoding = encoding

    def read(self, size: int = -1) -> str:
        return self.io.read(size).decode(self.encoding)

    def write(self, data: str) -> int:
        return self.io.write(data.encode(self.encoding))

    def flush(self):
        self.io.flush()

class SerialConverter:
    """
    Convert String Based Serializer to Bytes Based Serializer
    """
    __slots__ = ('_load', '_dump')

    def __init__(self, serializer: Any):
        assert hasattr(serializer, 'load') and hasattr(serializer, 'dump')
        load_attr = 'safe_load' if hasattr(serializer, 'safe_load') else 'load'
        dump_attr = 'safe_dump' if hasattr(serializer, 'safe_dump') else 'dump'
        self._load = getattr(serializer, load_attr)
        self._dump = getattr(serializer, dump_attr)

    def load(self, f: BinaryIO) -> Any:
        return self._load(IOWrapper(f))

    def dump(self, obj: Any, f: BinaryIO):
        return self._dump(obj, IOWrapper(f))

class FileRecord(NamedTuple):
    """
    Intermediate Record Definition for File Storage
    """
    data:       dict
    expiration: Optional[datetime] = None

class FileStore(Store):
    """
    File Based Temporary Storage for HTTP Session Data
    """
    __slots__ = ('index', 'storage_dir', 'serializer')

    index:       Dict[str, Optional[datetime]]
    storage_dir: str
    serializer:  Any

    def __init__(self,
        storage_dir: str = '/tmp/fastapi/',
        serializer:  Any = pickle,
    ):
        """
        :param storage_dir: storage directory hosting session files
        :param serializer:  python serializer object (eg: pickle/json/etc...)
        """
        assert hasattr(serializer, 'load') and hasattr(serializer, 'dump')
        os.makedirs(storage_dir, exist_ok=True)
        self.index       = {}
        self.storage_dir = storage_dir
        self.serializer  = serializer
        self._load_index()
        # auto-wrap serializer if it only accepts strings
        try:
            io = BytesIO()
            serializer.dump({}, io)
        except TypeError as e:
            if 'bytes-like' not in str(e):
                raise e
            self.serializer = SerialConverter(serializer)

    def _pack(self, path: str, record: FileRecord):
        """pack custom session record into session file"""
        expr = int(record.expiration.timestamp()) if record.expiration else -1
        with open(path, 'wb') as f:
            f.write(struct.pack('l', expr))
            self.serializer.dump(record.data, f)

    def _unpack(self, path: str) -> FileRecord:
        """unpack custom session record from session file"""
        with open(path, 'rb') as f:
            (expr, ) = struct.unpack('l', f.read(8))
            data     = self.serializer.load(f)
            rexpr    = datetime.fromtimestamp(expr) if expr >= 0 else None
            return FileRecord(data, rexpr)

    def _load_index(self):
        """load and index existing and valid session-files on startup"""
        now = datetime.now()
        for key in os.listdir(self.storage_dir):
            path = os.path.join(self.storage_dir, key)
            try:
                record = self._unpack(path)
            except Exception:
                os.remove(path)
                continue
            if record.expiration and record.expiration <= now:
                os.remove(path)
                continue
            self.index[key] = record.expiration

    async def has(self, key: str) -> bool:
        return key in self.index

    async def get(self, key: str) -> Optional[dict]:
        # skip if key is not in memory index
        if key not in self.index:
            return
        # check if file is missing even if index exists
        path = os.path.join(self.storage_dir, key)
        if not os.path.exists(path):
            del self.index[key]
            return
        # read record and check expiration, update index, and return
        record = self._unpack(path)
        now    = datetime.now()
        if record.expiration and record.expiration <= now:
            os.remove(path)
            del self.index[key]
            return
        self.index[key] = record.expiration
        return record.data

    async def set(self,
        key:  str,
        data: Optional[dict]      = None,
        expr: Optional[timedelta] = None,
    ):
        path   = os.path.join(self.storage_dir, key)
        rexpr  = (datetime.now() + expr) if expr else None
        record = FileRecord(data or {}, rexpr)
        self._pack(path, record)
        self.index[key] = rexpr

    async def delete(self, key: str):
        if key in self.index:
            os.remove(os.path.join(self.storage_dir, key))
            del self.index[key]

    async def background_task(self):
        now = datetime.now()
        for key in list(self.index.keys()):
            expiration = self.index[key]
            if expiration and expiration <= now:
                os.remove(os.path.join(self.storage_dir, key))
                del self.index[key]
