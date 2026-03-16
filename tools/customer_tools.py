"""
tools/customer_tools.py
────────────────────────
Agent-facing tool functions for CUSTOMER data file operations.

UniBasic programs used
----------------------
  GET.CUSTOMER.INFO  – fetch one customer record by ID
"""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

try:
    from agent_framework import tool
except ImportError:
    def tool(**_):
        def decorator(fn):
            return fn
        return decorator

from ud_bridge.connection import get_connection
from ud_bridge.executor import UniBasicExecutor
from config import ud_settings

logger = logging.getLogger(__name__)


# ─── Tool: Get Customer Info ─────────────────────────────────────────────────

@tool(approval_mode="never_require")
def get_customer_info(
    customer_id: Annotated[
        str,
        Field(description="The unique Customer ID to look up (e.g. 'CUST001')."),
    ],
) -> str:
    """
    Retrieve full profile for a customer from the UD CUSTOMER file.

    Returns: Customer ID, Name, Contact Email, Phone, Billing Address,
             Credit Limit, and Account Status.
    """
    logger.info("[Tool] get_customer_info called for customer_id=%s", customer_id)
    try:
        with get_connection() as conn:
            exe = UniBasicExecutor(conn)
            fields = exe.run(ud_settings.ub_get_customer, customer_id)

        # Expected output from GET.CUSTOMER.INFO:
        # [0] CUST.ID   [1] FNAME       [2] LNMAE       [3] COMPANY
        # [4] ADDRESS   [5] CITY       [6] STATE        [7] ZIP
        # [8] COUNTRY   [9] PHONE.NUM [10] PHONE_TYPE       
        if len(fields) < 11:
            return f"Incomplete data returned for customer '{customer_id}'."

        (
            cust_id,
            fname,
            lname,
            company,
            address,
            city,
            state,
            zip_code,
            country,
            phone,
            phone_type,
        ) = fields[0:11]

        result = (
            f"Customer ID     : {cust_id}\n"
            f"Name            : {fname} {lname}\n"
            f"Phone           : {phone}\n"
            f"Address         : {address}, {city}, {state} {zip_code}\n"
            f"Country         : {country}\n"
            f"Phone Type      : {phone_type}\n"
        )
        logger.info("[Tool] get_customer_info SUCCESS")
        return result

    except Exception as exc:
        logger.error("[Tool] get_customer_info FAILED: %s", exc)
        return f"Error retrieving customer '{customer_id}': {exc}"


# ─── Tool: Search Customers ──────────────────────────────────────────────────

@tool(approval_mode="never_require")
def search_customers(
    search_field: Annotated[
        str,
        Field(
            description=(
                "Field to search on. Allowed values: "
                "'NAME', 'EMAIL', 'PHONE', 'CITY', 'STATE'."
            )
        ),
    ],
    search_value: Annotated[
        str,
        Field(description="Value to match against the selected field."),
    ],
) -> str:
    """
    Search the CUSTOMER file for records matching a field/value pair.

    Returns a list of matching Customer IDs and names.
    """
    allowed_fields = {"ID","LNAME", "PHONE_NUM", "CITY", "STATE"}
    sf = search_field.upper().strip()
    if sf not in allowed_fields:
        return (
            f"Invalid search field '{search_field}'. "
            f"Allowed: {', '.join(sorted(allowed_fields))}."
        )

    logger.info(
        "[Tool] search_customers called: field=%s value=%s", sf, search_value
    )
    try:
        with get_connection() as conn:
            ids = conn.select_records(
                "CUSTOMER", f"WITH {sf} LIKE '{search_value}...'"
            )
            if not ids:
                return f"No customers found where {sf} matches '{search_value}'."

            # Read name for each ID (open file once, loop over ids)
            file_handle = conn.open_file("CUSTOMER")
            rows: list[str] = []
            for cid in ids:
                rec = conn.read_record(file_handle, cid)
                name = str(rec).split(chr(254))[1] if rec else "Unknown"  # field 1
                rows.append(f"  • {cid}  {name}")

        return (
            f"Found {len(ids)} customer(s) where {sf} ~ '{search_value}':\n"
            + "\n".join(rows)
        )
    except Exception as exc:
        logger.error("[Tool] search_customers FAILED: %s", exc)
        return f"Error searching customers: {exc}"


# ─── Tool: Get Customer Order Summary ────────────────────────────────────────

@tool(approval_mode="never_require")
def get_customer_order_summary(
    customer_id: Annotated[
        str,
        Field(description="Customer ID to summarise order history for."),
    ],
) -> str:
    """
    Return a high-level order summary for a customer:
    total orders, total spend, open vs completed orders.

    Reads from both the CUSTOMER and ORDERS files.
    """
    logger.info(
        "[Tool] get_customer_order_summary called for customer_id=%s", customer_id
    )
    try:
        with get_connection() as conn:
            order_ids = conn.select_records(
                "ORDERS", f"WITH CLIENT_NO = '{customer_id}'"
            )
            if not order_ids:
                return f"Customer '{customer_id}' has no orders on record."

            orders_file = conn.open_file("ORDERS")
            total_spend = 0.0
            open_count = 0
            closed_count = 0

            for oid in order_ids:
                rec = conn.read_record(orders_file, oid)
                fields = str(rec).split(chr(254))
                # Assume field layout: [0]=ORD_ID [1]=CUST_ID [2]=DATE
                #                      [3]=STATUS [4..]=items  [-1]=TOTAL
                status = fields[3] if len(fields) > 3 else ""
                total_str = fields[-1] if fields else "0"
                try:
                    total_spend += float(total_str)
                except ValueError:
                    pass
                if status.upper() in ("OPEN", "PENDING", "PROCESSING"):
                    open_count += 1
                else:
                    closed_count += 1

        return (
            f"Order Summary for Customer '{customer_id}':\n"
            f"  Total Orders   : {len(order_ids)}\n"
            f"  Open / Pending : {open_count}\n"
            f"  Closed         : {closed_count}\n"
            f"  Total Spend    : ${total_spend:,.2f}"
        )
    except Exception as exc:
        logger.error("[Tool] get_customer_order_summary FAILED: %s", exc)
        return f"Error generating order summary for customer '{customer_id}': {exc}"
