"""
Simple Non-Async SqlAlchemy wrapper for more convienient DB object
"""
from typing import Optional, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, Row

#** Variables **#
__all__ = ['Database', 'Row']

#** Classes **#

class Database:
    """
    simple sqlalchemy database wrapper
    """

    def __init__(self, uri: str, pool_recycle: int = 1800, **kwargs):
        self.uri:    str              = uri
        self.engine: Optional[Engine] = None
        self.kwargs                   = {'pool_recycle': pool_recycle, **kwargs}
    
    def _conn(self) -> Connection:
        if not self.engine:
            raise ConnectionError('Database connection is closed')
        return self.engine.connect()
    
    def _exec(self, sql: str, values: dict):
        with self._conn() as conn:
            return conn.exec_driver_sql(sql, **values)
    
    def __enter__(self) -> 'Database':
        if not self.engine:
            self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    def connect(self):
        """
        start database engine and build connection pool
        """
        self.engine = create_engine(self.uri, **self.kwargs)

    def disconnect(self):
        """
        close all open connections with database
        """
        if not self.engine:
            raise ConnectionError('database is not connected')
        self.engine.dispose()

    def execute(self, sql: str, values: Optional[dict] = None):
        """
        execute the given sql against db and return

        :param sql:    raw sql to excute in db
        :param values: python values to map into sql query
        """
        with self._conn() as conn:
            conn.execute(text(sql), values)
    
    def execute_many(self, sql: str, values: List[dict] = []):
        """
        execute the given sql against db multiple times with set of values

        :param sql:    raw sql to execute in db
        :param values: list of value objects to execute in db
        """
        def operation(conn):
            for value_set in values:
                conn.execute(text(sql), value_set)
        with self._conn() as conn:
            conn.transaction(operation)

    def fetch_one(self, sql: str, values: Optional[dict] = None) -> Optional[Row]:
        """
        fetch a single row from the sql-result or return none

        :param sql:    raw sql to execute in db
        :param values: python values to map into sql query
        :return:       query result record or none
        """
        with self._conn() as conn:
            result = conn.execute(text(sql), values)
            return result.fetchone()

    def fetch_all(self, sql: str, values: Optional[dict] = None) -> List[Row]:
        """
        fetch all rows found from a sql-result

        :param sql:    raw sql to execute in db
        :param values: python values to map into sql query
        :return:       collected sql results
        """
        with self._conn() as conn:
            result = conn.execute(text(sql), values)
            return result.fetchall()
