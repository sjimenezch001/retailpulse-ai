"""Bounded, non-extensible read-only Gold sessions; no public SQL tool."""
from contextlib import contextmanager
from pathlib import Path
from threading import Timer
from time import monotonic

import duckdb

from retailpulse.agent.errors import AgentError

CONNECTION_CONFIG = {"enable_external_access": "false", "threads": "1",
                     "memory_limit": "256MB", "max_temp_directory_size": "0B",
                     "autoload_known_extensions": "false", "autoinstall_known_extensions": "false",
                     "lock_configuration": "true"}


class _DeadlineConnection:
    def __init__(self, connection, seconds):
        self.connection, self.deadline = connection, monotonic() + seconds

    def execute(self, statement, parameters=None):
        remaining = self.deadline - monotonic()
        if remaining <= 0:
            raise AgentError("query_timeout", "The query exceeded its deadline. Narrow the requested scope.", "unavailable")
        timer = Timer(remaining, self.connection.interrupt)
        timer.daemon = True
        timer.start()
        try:
            return self.connection.execute(statement, parameters or [])
        finally:
            timer.cancel()
            timer.join()


@contextmanager
def gold_session(database: Path, timeout_seconds: float = 5.0):
    if not 0 < timeout_seconds <= 10:
        raise ValueError("Query deadline must be positive and at most ten seconds.")
    if not database.is_file():
        raise AgentError("missing_gold", "The local Gold snapshot is unavailable. Complete the data stages first.", "unavailable")
    connection = None
    try:
        connection = duckdb.connect(str(database), read_only=True, config=CONNECTION_CONFIG)
        yield _DeadlineConnection(connection, timeout_seconds)
    except duckdb.InterruptException as exc:
        raise AgentError("query_timeout", "The query exceeded its deadline. Narrow the requested scope.", "unavailable") from exc
    except duckdb.OutOfMemoryException as exc:
        raise AgentError("resource_limit", "The query exceeded its memory budget. Narrow the requested scope.", "unavailable") from exc
    except duckdb.Error as exc:
        raise AgentError("gold_contract", "The Gold snapshot could not satisfy the approved data contract.", "unavailable") from exc
    finally:
        if connection:
            connection.close()
