"""
tools/__init__.py
──────────────────
Exports all agent tool functions so main.py can import them from one place.
"""

from .order_tools import (
    get_order_details,
    list_orders_for_customer,
    process_order,
)
from .customer_tools import (
    get_customer_info,
    search_customers,
    get_customer_order_summary,
)
from .inventory_tools import (
    check_inventory,
    list_low_stock_items,
    update_inventory,
    check_inventory_for_order,
)

# Convenience list — pass directly to Agent(tools=ALL_TOOLS)
ALL_TOOLS = [
    get_order_details,
    list_orders_for_customer,
    process_order,
    get_customer_info,
    search_customers,
    get_customer_order_summary,
    check_inventory,
    list_low_stock_items,
    update_inventory,
    check_inventory_for_order,
]

__all__ = [
    "ALL_TOOLS",
    "get_order_details",
    "list_orders_for_customer",
    "process_order",
    "get_customer_info",
    "search_customers",
    "get_customer_order_summary",
    "check_inventory",
    "list_low_stock_items",
    "update_inventory",
    "check_inventory_for_order",
]
