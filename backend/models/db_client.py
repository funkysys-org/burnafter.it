import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from backend.config import Config
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_connection_pool: Optional[pool.SimpleConnectionPool] = None

def init_db():
    """Initialize database connection pool"""
    global _connection_pool

    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                host=Config.POSTGRES_HOST,
                port=Config.POSTGRES_PORT,
                database=Config.POSTGRES_DB,
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

def get_db_connection():
    """Get a connection from the pool"""
    if _connection_pool is None:
        init_db()
    return _connection_pool.getconn()

def return_db_connection(conn):
    """Return a connection to the pool"""
    if _connection_pool:
        _connection_pool.putconn(conn)

class DatabaseConnection:
    """Context manager for database connections"""

    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()

        if self.cursor:
            self.cursor.close()

        if self.conn:
            return_db_connection(self.conn)

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a query and return results"""
    with DatabaseConnection() as cursor:
        cursor.execute(query, params or ())

        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            return cursor.rowcount

def execute_many(query, params_list):
    """Execute a query with multiple parameter sets"""
    with DatabaseConnection() as cursor:
        cursor.executemany(query, params_list)
        return cursor.rowcount
