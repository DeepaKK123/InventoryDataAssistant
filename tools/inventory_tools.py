"""
tools/inventory_tools.py
─────────────────────────
Agent-facing tool functions for INVENTORY data file operations.

UniBasic programs used
----------------------
  CHECK.INVENTORY    – read stock level and product info for an item
  UPDATE.INVENTORY   – adjust quantity on-hand (increase or decrease)
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


# ─── Tool: Check Inventory ───────────────────────────────────────────────────

@tool(approval_mode="never_require")
def check_inventory(
    item_id: Annotated[
        str,
        Field(description="Inventory Item ID to check (e.g. 'ITEM001')."),
    ],
) -> str:
    """
    Retrieve stock level and product details for an inventory item.

    Returns: Item ID, Description, Category, Unit Price,
             Quantity On-Hand, Reorder Point, and Supplier.
    """
    logger.info("[Tool] check_inventory called for item_id=%s", item_id)
    try:
        with get_connection() as conn:
            exe = UniBasicExecutor(conn)
            fields = exe.run(ud_settings.ub_check_inventory, item_id)

        # Expected output from CHECK.INVENTORY:
        # [0] ITEM.ID     [1] DESCRIPTION   [2] CATEGORY    [3] UNIT.PRICE
        # [4] QTY.ON.HAND [5] REORDER.PT    [6] SUPPLIER    [7] WAREHOUSE.LOC
        if len(fields) < 8:
            return f"Incomplete inventory data for item '{item_id}'."

        (item_id_out, description, category, unit_price,
         qty_on_hand, reorder_pt, supplier, warehouse_loc) = fields[0:8]

        # Highlight low stock
        try:
            qty_int = int(qty_on_hand)
            rpt_int = int(reorder_pt)
            stock_status = "⚠ LOW STOCK" if qty_int <= rpt_int else "In Stock"
        except ValueError:
            stock_status = "Unknown"

        result = (
            f"Item ID       : {item_id_out}\n"
            f"Description   : {description}\n"
            f"Category      : {category}\n"
            f"Unit Price    : ${unit_price}\n"
            f"Qty On Hand   : {qty_on_hand}  [{stock_status}]\n"
            f"Reorder Point : {reorder_pt}\n"
            f"Supplier      : {supplier}\n"
            f"Warehouse Loc : {warehouse_loc}"
        )
        logger.info("[Tool] check_inventory SUCCESS")
        return result

    except Exception as exc:
        logger.error("[Tool] check_inventory FAILED: %s", exc)
        return f"Error checking inventory for item '{item_id}': {exc}"


# ─── Tool: List Low Stock Items ──────────────────────────────────────────────

@tool(approval_mode="never_require")
def list_low_stock_items(
    category: Annotated[
        str,
        Field(
            description=(
                "Optional category filter (e.g. 'ELECTRONICS'). "
                "Pass empty string '' for all categories."
            )
        ),
    ] = "",
) -> str:
    """
    List all inventory items where Quantity On-Hand is at or below the
    Reorder Point.  Optionally filter by product category.
    """
    logger.info(
        "[Tool] list_low_stock_items called. category filter='%s'", category
    )
    try:
        criteria = "WITH QTY.ON.HAND <= REORDER.PT"
        if category.strip():
            criteria += f" AND WITH CATEGORY = '{category.upper().strip()}'"

        with get_connection() as conn:
            ids = conn.select_records("INVENTORY", criteria)
            if not ids:
                cat_msg = f" in category '{category}'" if category else ""
                return f"No low-stock items found{cat_msg}."

            inv_file = conn.open_file("INVENTORY")
            rows: list[str] = []
            for iid in ids:
                rec = conn.read_record(inv_file, iid)
                f = str(rec).split(chr(254))
                desc    = f[1] if len(f) > 1 else "?"
                qty     = f[4] if len(f) > 4 else "?"
                reorder = f[5] if len(f) > 5 else "?"
                rows.append(f"  • {iid}  {desc}  qty={qty}  reorder_pt={reorder}")

        cat_header = f" [{category.upper()}]" if category else ""
        return (
            f"Low-Stock Items{cat_header} ({len(ids)} found):\n"
            + "\n".join(rows)
        )
    except Exception as exc:
        logger.error("[Tool] list_low_stock_items FAILED: %s", exc)
        return f"Error listing low-stock items: {exc}"


# ─── Tool: Update Inventory Quantity ─────────────────────────────────────────

@tool(approval_mode="always_require")           # Mutates data — requires human approval
def update_inventory(
    item_id: Annotated[
        str,
        Field(description="Item ID whose quantity should be adjusted."),
    ],
    adjustment: Annotated[
        int,
        Field(
            description=(
                "Signed integer adjustment: positive to add stock, "
                "negative to remove (e.g. -10 to reduce by 10 units)."
            )
        ),
    ],
    reason: Annotated[
        str,
        Field(
            description=(
                "Reason code for the adjustment. "
                "E.g. 'RECEIPT', 'SALE', 'DAMAGE', 'RETURN', 'STOCKTAKE'."
            )
        ),
    ],
) -> str:
    """
    Adjust the Quantity On-Hand for an inventory item.

    Calls the UPDATE.INVENTORY UniBasic subroutine which records the
    adjustment in the audit trail and recalculates stock status.
    """
    logger.info(
        "[Tool] update_inventory: item=%s adjustment=%d reason=%s",
        item_id, adjustment, reason,
    )
    try:
        with get_connection() as conn:
            exe = UniBasicExecutor(conn)
            fields = exe.run(
                ud_settings.ub_update_inventory,
                item_id,
                str(adjustment),
                reason.upper().strip(),
            )

        # Expected output from UPDATE.INVENTORY:
        # [0] ITEM.ID  [1] OLD.QTY  [2] NEW.QTY  [3] STATUS.MSG
        if len(fields) < 4:
            return f"Update completed for item '{item_id}' (no detail returned)."

        item_id_out, old_qty, new_qty, status_msg = fields[0:4]
        direction = "▲ increased" if adjustment >= 0 else "▼ decreased"

        result = (
            f"Inventory Updated:\n"
            f"  Item ID    : {item_id_out}\n"
            f"  Qty Before : {old_qty}\n"
            f"  Adjustment : {adjustment:+d}  ({direction})\n"
            f"  Qty After  : {new_qty}\n"
            f"  Reason     : {reason.upper()}\n"
            f"  Message    : {status_msg}"
        )
        logger.info("[Tool] update_inventory SUCCESS")
        return result

    except Exception as exc:
        logger.error("[Tool] update_inventory FAILED: %s", exc)
        return f"Error updating inventory for item '{item_id}': {exc}"


# ─── Tool: Check Multiple Items ──────────────────────────────────────────────

@tool(approval_mode="never_require")
def check_inventory_for_order(
    item_ids: Annotated[
        str,
        Field(
            description=(
                "Comma-separated list of Item IDs to check availability for "
                "(e.g. 'ITEM001,ITEM002,ITEM003')."
            )
        ),
    ],
    quantities: Annotated[
        str,
        Field(
            description=(
                "Comma-separated requested quantities matching item_ids "
                "(e.g. '2,5,1')."
            )
        ),
    ],
) -> str:
    """
    Check whether sufficient stock exists for all items in a potential order.

    Returns per-item availability and an overall fulfilment verdict.
    """
    items   = [i.strip() for i in item_ids.split(",") if i.strip()]
    qtys    = [q.strip() for q in quantities.split(",") if q.strip()]

    if len(items) != len(qtys):
        return "Mismatch: item_ids and quantities must have the same count."

    logger.info("[Tool] check_inventory_for_order: %s items", len(items))
    rows: list[str] = []
    can_fulfil = True

    try:
        with get_connection() as conn:
            exe = UniBasicExecutor(conn)
            for item_id, requested_str in zip(items, qtys):
                fields = exe.run(ud_settings.ub_check_inventory, item_id)
                qty_on_hand = fields[4] if len(fields) > 4 else "0"
                description = fields[1] if len(fields) > 1 else item_id

                try:
                    available = int(qty_on_hand)
                    requested = int(requested_str)
                    ok = available >= requested
                except ValueError:
                    available, requested, ok = 0, 0, False

                status_icon = "✓" if ok else "✗"
                if not ok:
                    can_fulfil = False
                rows.append(
                    f"  {status_icon} {item_id} ({description})  "
                    f"requested={requested}  available={available}"
                )

        verdict = "✓ ORDER CAN BE FULFILLED" if can_fulfil else "✗ ORDER CANNOT BE FULFILLED — insufficient stock"
        return "Availability Check:\n" + "\n".join(rows) + f"\n\nVerdict: {verdict}"

    except Exception as exc:
        logger.error("[Tool] check_inventory_for_order FAILED: %s", exc)
        return f"Error checking inventory availability: {exc}"
