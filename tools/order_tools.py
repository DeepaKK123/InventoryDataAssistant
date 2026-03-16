"""
tools/order_tools.py
─────────────────────
Agent-facing tool functions for ORDERS data file operations.

Each function is decorated with @tool so the Microsoft Agent Framework
registers it as a callable capability.  All UD I/O is routed through
the UniBasicExecutor which calls cataloged UniBasic programs.

UniBasic programs used
----------------------
  GET.ORDER.DETAILS   – fetch one order record by ID
  PROCESS.ORDER       – create or update an order record
"""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

try:
    from agent_framework import tool
except ImportError:                   # Allow module import without the SDK installed
    def tool(**_):                    # Stub decorator for local testing
        def decorator(fn):
            return fn
        return decorator

from ud_bridge.connection import get_connection
from ud_bridge.executor import UniBasicExecutor
from config import ud_settings

logger = logging.getLogger(__name__)


# ─── Tool: Get Order Details ─────────────────────────────────────────────────

@tool(approval_mode="never_require")
def get_order_details(
    order_id: Annotated[
        str,
        Field(description="The unique Order ID to retrieve (e.g. 'ORD001')."),
    ],
) -> str:
    """
    Retrieve full details for a specific order from the UD ORDERS file.

    Returns a formatted string with:
      Order ID, Customer ID, Order Date, Status, Line Items, and Total Amount.
    """
    logger.info("[Tool] get_order_details called with order_id=%s", order_id)
    try:
        with get_connection() as conn:
            exe = UniBasicExecutor(conn)
            fields = exe.run(ud_settings.ub_get_order, order_id)
        # Expected output fields from GET.ORDER.DETAILS:
        # [0] ORDER.ID   [1] CUST.ID   [2] ORDER.DATE [4] ITEM.LIST 
        # [5] COLOR.LIST  [6] QTY.LIST  [7] PRICE.LIST  [8] TOTAL.AMT
        if len(fields) < 9:
            return f"Incomplete data returned for order '{order_id}'."

        order_id_out, cust_id, order_date, status = fields[0:4]
        items       = fields[4].split(chr(252))   # sub-value mark
        colors      = fields[5].split(chr(252))   
        quantities  = fields[6].split(chr(252))
        prices      = fields[7].split(chr(252))
        total_amt   = fields[8]

        lines = []
        for item, color, qty, price in zip(items, colors, quantities, prices):
            lines.append(f"  • {item} color={color} qty={qty}  unit_price=${price}")

        result = (
            f"Order ID    : {order_id_out}\n"
            f"Customer ID : {cust_id}\n"
            f"Order Date  : {order_date}\n"
            f"Status      : {status}\n"
            f"Line Items  :\n" + "\n".join(lines) + "\n"
            f"Total Amount: ${total_amt}"
        )
        logger.info("[Tool] get_order_details SUCCESS")
        return result

    except Exception as exc:
        logger.error("[Tool] get_order_details FAILED: %s", exc)
        return f"Error retrieving order '{order_id}': {exc}"


# ─── Tool: List Orders by Customer ───────────────────────────────────────────

@tool(approval_mode="never_require")
def list_orders_for_customer(
    customer_id: Annotated[
        str,
        Field(description="Customer ID whose orders should be listed."),
    ],
) -> str:
    """
    List all order IDs associated with a given customer.

    Uses a UD SELECT on the ORDERS file filtered by CUST.ID.
    """
    logger.info(
        "[Tool] list_orders_for_customer called for customer_id=%s", customer_id
    )
    try:
        with get_connection() as conn:
            ids = conn.select_records(
                "ORDERS", f"WITH CLIENT_NO = '{customer_id}'"
            )

        if not ids:
            return f"No orders found for customer '{customer_id}'."
        return (
            f"Orders for customer '{customer_id}' ({len(ids)} found):\n"
            + "\n".join(f"  • {oid}" for oid in ids)
        )
    except Exception as exc:
        logger.error("[Tool] list_orders_for_customer FAILED: %s", exc)
        return f"Error listing orders for customer '{customer_id}': {exc}"


# ─── Tool: Create / Update Order ─────────────────────────────────────────────

@tool(approval_mode="always_require")           # Requires human approval — mutates data
def process_order(
    order_id: Annotated[
        str,
        Field(description="Order ID to create or update (e.g. 'ORD099')."),
    ],
    customer_id: Annotated[
        str,
        Field(description="Customer ID placing the order."),
    ],
    item_ids: Annotated[
        str,
        Field(description="Comma-separated list of inventory item IDs (e.g. 'ITEM01,ITEM02')."),
    ],
    quantities: Annotated[
        str,
        Field(description="Comma-separated quantities matching item_ids (e.g. '2,5')."),
    ],
    action: Annotated[
        str,
        Field(description="'CREATE' to create a new order, 'UPDATE' to modify existing."),
    ] = "CREATE",
) -> str:
    """
    Create or update an order in the UD ORDERS file.

    Calls the PROCESS.ORDER UniBasic program which handles validation,
    inventory reservation, and record writing atomically.
    """
    logger.info(
        "[Tool] process_order called: action=%s order_id=%s customer_id=%s",
        action, order_id, customer_id,
    )
    try:
        with get_connection() as conn:
            exe = UniBasicExecutor(conn)
            fields = exe.run(
                ud_settings.ub_process_order,
                action,
                order_id,
                customer_id,
                item_ids,
                quantities,
            )

        # Expected output: [0] ORDER.ID  [1] STATUS.MSG  [2] TOTAL.AMT
        status_msg = fields[1] if len(fields) > 1 else "Processed"
        total_amt  = fields[2] if len(fields) > 2 else "N/A"

        result = (
            f"Order '{order_id}' {action}D successfully.\n"
            f"Status  : {status_msg}\n"
            f"Total   : ${total_amt}"
        )
        logger.info("[Tool] process_order SUCCESS")
        return result

    except Exception as exc:
        logger.error("[Tool] process_order FAILED: %s", exc)
        return f"Error processing order '{order_id}': {exc}"
