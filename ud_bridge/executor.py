"""
ud_bridge/executor.py
───────────────────
High-level executor that wraps UniBasic subroutine calls with:
  • Consistent argument packing / unpacking
  • Error propagation via UDError
  • Structured result parsing

All UniBasic programs in this project follow a 3-argument convention:

    SUBROUTINE <NAME>(INPUT.DATA, OUTPUT.DATA, STATUS)

    INPUT.DATA   = VM-separated input fields
    OUTPUT.DATA  = VM-separated output fields (populated by the program)
    STATUS       = "OK" on success, "ERROR:<message>" on failure

Value Mark (VM) = CHAR(253) is used as field delimiter within DynArrays.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import uopy
except ImportError:
    uopy = None  # Allow import without uopy installed (for unit-testing stubs)

from ud_bridge.connection import UDConnection, UDError

logger = logging.getLogger(__name__)

VM = chr(253)   # UD Value Mark — field separator inside DynArrays
FM = chr(254)   # UD Field Mark — record field separator (for reference)


def _pack_input(*fields: Any) -> str:
    """Join input fields with VM delimiter for passing into a UniBasic sub."""
    return VM.join(str(f) if f is not None else "" for f in fields)


def _unpack_output(output_str: str) -> list[str]:
    """Split VM-delimited output string into a list of field values."""
    return output_str.split(VM)


def _check_status(status: str, program_name: str) -> None:
    """Raise UDError if STATUS arg does not start with 'OK'."""
    if not status.upper().startswith("OK"):
        msg = status.replace("ERROR:", "", 1).strip() or "Unknown error"
        raise UDError(f"UniBasic {program_name} reported error: {msg}")


class UniBasicExecutor:
    """
    Executes cataloged UniBasic programs via an open UDConnection.

    Usage
    -----
        from ud_bridge.connection import get_connection
        from ud_bridge.executor import UniBasicExecutor

        with get_connection() as conn:
            exe = UniBasicExecutor(conn)
            result = exe.run("GET.ORDER.DETAILS", "ORD001")
    """

    def __init__(self, connection: UDConnection) -> None:
        self._conn = connection

    def run(
        self,
        program_name: str,
        *input_fields: Any,
    ) -> list[str]:
        """
        Call a UniBasic subroutine and return parsed output fields.

        Parameters
        ----------
        program_name : str
            Cataloged UniBasic program name (e.g. "GET.ORDER.DETAILS").
        *input_fields : Any
            Values to pack as VM-separated INPUT.DATA argument.

        Returns
        -------
        list[str]
            Parsed VM-separated fields from OUTPUT.DATA.

        Raises
        ------
        UDError
            If the STATUS argument indicates failure or UOPY raises.
        """
        input_data = _pack_input(*input_fields)
        output_data = ""   # UniBasic will populate this
        status = ""        # UniBasic will set "OK" or "ERROR:<msg>"

        logger.info("Calling UniBasic: %s  input=%r", program_name, input_data)

        if uopy is None:
            raise UDError("uopy package is not installed.")

        # Call the cataloged subroutine using uopy.Subroutine
        subr = uopy.Subroutine(program_name, 3, self._conn.session)
        subr.args[0] = input_data
        subr.args[1] = output_data
        subr.args[2] = status
        subr.call()

        # results[0] = input_data (unchanged)
        # results[1] = output_data (populated by UniBasic)
        # results[2] = status
        returned_output = str(subr.args[1])
        returned_status = str(subr.args[2])

        _check_status(returned_status, program_name)

        parsed = _unpack_output(returned_output)
        logger.debug(
            "UniBasic %s returned %d output fields", program_name, len(parsed)
        )
        return parsed
