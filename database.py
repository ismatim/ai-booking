"""SQLite database client initialization (Async Singleton Manager)."""

import os
import aiosqlite
from typing import Optional
from utils.logger import get_logger
from functools import lru_cache

logger = get_logger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


class Database:
    _instance: Optional["Database"] = None
    _connection: Optional[aiosqlite.Connection] = None
    _DB_PATH = "app.db"

    def __new__(cls):
        """Guarantee that a single, shared instance of the Database class is sustained.

        Implements a strict Singleton pattern to avoid redundant resource allocation
        and conflicting file handles on the local SQLite file.

        Returns:
            Database: The shared singleton instance managing database context state.
        """
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    async def get_connection(self) -> aiosqlite.Connection:
        """Retrieve the single, persistent asynchronous connection to the SQLite database.

        Lazily initializes the connection if it does not already exist and binds
        the `aiosqlite.Row` row factory to allow dictionary-like row querying.

        Returns:
            aiosqlite.Connection: An active, thread-safe asynchronous SQLite connection hook.
        """
        if self._connection is None:
            self._connection = await aiosqlite.connect(self._DB_PATH)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def close(self):
        """Close the global persistent database connection safely.

        Designed to be executed during application shutdown events or teardown lifecycles
        to prevent database corruption or unhandled dangling context blocks.
        """
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def init_db(self) -> None:
        """Read the schema template blueprint and build out missing tables on the connection.

        Validates the existence of the source SQL template and passes the file contents
        directly into the SQLite compilation engine to prepare system structures.

        Raises:
            FileNotFoundError: If the foundational `schema.sql` template cannot be found at
                the specified filesystem path.
            Exception: If the SQL script compilation fails due to parsing or constraint errors.
        """
        if not os.path.exists(_SCHEMA_PATH):
            raise FileNotFoundError(
                f"Database schema template missing at: {_SCHEMA_PATH}"
            )

        with open(_SCHEMA_PATH, "r") as f:
            schema_script = f.read()

        conn = await self.get_connection()
        try:
            # executescript executes multiple SQL statements separated by semicolons
            await conn.executescript(schema_script)
            await conn.commit()
            logger.info("Database schema verified and synced successfully.")
        except Exception as e:
            logger.error(f"Failed to compile structural schema: {e}")
            raise


@lru_cache()
def get_db() -> Database:
    """Provide a clean interface to fetch the active Database singleton engine instance.

    Ideal for dependency injection frameworks, service layer utilities, or
    routing controllers.

    Returns:
        Database: The initialized instance managing the underlying SQLite connection pool.

    Examples:
        >>> # Basic integration context inside an asynchronous route handler
        >>> async def read_bookings():
        ...     db = get_db()
        ...     conn = await db.get_connection()
        ...     async with conn.execute("SELECT * FROM bookings") as cursor:
        ...         return await cursor.fetchall()
    """
    return Database()
