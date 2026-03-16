"""
ud_bridge/connection.py
─────────────────────
Thread-safe UOPY connection manager for UD.

Provides:
  • UDConnection  – low-level context manager wrapping uopy.Session
  • get_connection()   – factory that returns a ready-to-use connection
  • UDError       – unified exception for all UD problems

Usage
-----
    from ud.connection import get_connection

    with get_connection() as conn:
        file_handle = conn.open_file("ORDERS")
        record = conn.read_record(file_handle, "ORD001")
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

try:
    import uopy
except ImportError:
    uopy = None  # Allow import without uopy installed (for unit-testing stubs)

from config import ud_settings

logger = logging.getLogger(__name__)


class UDError(Exception):
    """Raised for any UD / UOPY operation failure."""


class UDConnection:
    """
    Wraps a uopy.Session and exposes helper methods.

    Intended to be used as a context manager:

        with UDConnection() as conn:
            fh = conn.open_file("ORDERS")
    """

    def __init__(self) -> None:
        self._session: uopy.Session | None = None
        self._cfg = ud_settings

    # ─── Context manager ─────────────────────────────────────────────────────

    def __enter__(self) -> "UDConnection":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.disconnect()

    # ─── Connection lifecycle ─────────────────────────────────────────────────

    def connect(self) -> None:
        """Open a UOPY session to the UD server."""
        if uopy is None:
            raise UDError(
                "uopy package is not installed. "
                "Run: pip install uopy"
            )
        try:
            logger.info(
                "Connecting to UD at %s account=%s service=%s",
                self._cfg.host, self._cfg.account, self._cfg.service,
            )
            self._session = uopy.connect(
                host=self._cfg.host,
                user=self._cfg.username,
                password=self._cfg.password,
                account=self._cfg.account,
                service=self._cfg.service,
            )
            logger.info("UD connection established.")
        except Exception as exc:
            raise UDError(f"Failed to connect to UD: {exc}") from exc

    def disconnect(self) -> None:
        """Close the UOPY session gracefully."""
        if self._session:
            try:
                self._session.close()
                logger.info("UD connection closed.")
            except Exception as exc:
                logger.warning("Error closing UD session: %s", exc)
            finally:
                self._session = None

    @property
    def session(self) -> "uopy.Session":
        if not self._session:
            raise UDError("Not connected. Call connect() first.")
        return self._session

    # ─── File operations ─────────────────────────────────────────────────────

    def open_file(self, file_name: str) -> "uopy.File":
        """Open a UD file and return its handle."""
        try:
            f = uopy.File(file_name, self._session)
            f.open()
            logger.debug("Opened UD file: %s", file_name)
            return f
        except Exception as exc:
            raise UDError(f"Cannot open file '{file_name}': {exc}") from exc

    def read_record(self, file_handle: "uopy.File", record_id: str) -> "uopy.DynArray":
        """Read a single record by ID from an open file handle."""
        try:
            record = uopy.DynArray(session=self._session)
            file_handle.read(record_id, record)
            logger.debug("Read record '%s'", record_id)
            return record
        except Exception as exc:
            raise UDError(
                f"Cannot read record '{record_id}': {exc}"
            ) from exc

    def write_record(
        self,
        file_handle: "uopy.File",
        record_id: str,
        record: "uopy.DynArray",
    ) -> None:
        """Write / update a record in an open file handle."""
        try:
            file_handle.write(record_id, record)
            logger.debug("Wrote record '%s'", record_id)
        except Exception as exc:
            raise UDError(
                f"Cannot write record '{record_id}': {exc}"
            ) from exc

    def select_records(
        self,
        file_name: str,
        select_criteria: str = "",
    ) -> list[str]:
        """
        Run a SELECT against a UD file and return a list of record IDs.

        Parameters
        ----------
        file_name : str
            The UD file to SELECT from.
        select_criteria : str
            Optional WITH / BY clause appended to SELECT.
        """
        try:
            cmd = f"SELECT {file_name}"
            if select_criteria:
                cmd += f" {select_criteria}"
            logger.debug("Running: %s", cmd)
            try:
                logger.info(
            "[Connection] select_records called for cmd=%s", cmd)
                select_list = uopy.SelectList(self._session)
            except AttributeError:
                select_list = uopy.Select(self._session)
            
    
            select_list.select(cmd)
            ids: list[str] = []
            while True:
                rec_id = select_list.next()
                if rec_id is None:
                    break
                ids.append(str(rec_id))
            logger.debug("SELECT returned %d records", len(ids))
            return ids
        except Exception as exc:
            raise UDError(
                f"SELECT on '{file_name}' failed: {exc}"
            ) from exc

    # ─── UniBasic execution ───────────────────────────────────────────────────

    def call_subroutine(
        self,
        program_name: str,
        *args: str,
    ) -> list[str]:
        """
        Call a cataloged UniBasic SUBROUTINE and return its arguments
        (in-place modified by the program) as a list of strings.

        Convention used by all UniBasic programs in this project:
          ARG(1)  = Input data (VM-delimited fields)
          ARG(2)  = Output data (VM-delimited fields)
          ARG(3)  = Status code: "OK" or "ERROR:<message>"
        """
        try:
            sub = uopy.Subroutine(program_name, len(args), self._session)
            for i, arg in enumerate(args):
                sub.args[i] = arg
            sub.call()
            results = [str(sub.args[i]) for i in range(len(args))]
            logger.debug(
                "Subroutine %s returned status: %s", program_name, results[-1]
            )
            return results
        except Exception as exc:
            raise UDError(
                f"Subroutine '{program_name}' failed: {exc}"
            ) from exc


# ─── Factory helper ──────────────────────────────────────────────────────────

@contextmanager
def get_connection() -> Generator[UDConnection, None, None]:
    """
    Convenience context manager that yields a connected UDConnection.

    Example
    -------
        with get_connection() as conn:
            ids = conn.select_records("ORDERS")
    """
    conn = UDConnection()
    conn.connect()
    try:
        yield conn
    finally:
        conn.disconnect()
