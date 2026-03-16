# UD Inventory Data AI Agent Workflow
## Microsoft Agent Framework + UOPY + UD Integration

### Project Structure
InventoryDataAnalyst/
├── README.md
├── requirements.txt
├── .env.example
├── main_agent.py                          # Entry point & agent orchestration
├── config/
│   ├── __init__.py
│   └── settings.py                  # Environment & connection config
├── ud_bridge/
│   ├── __init__.py
│   ├── connection.py                # UOPY connection manager
│   └── executor.py                  # UniBasic program executor
├── tools/
│   ├── __init__.py
│   ├── order_tools.py               # ORDERS file operations
│   ├── customer_tools.py            # CUSTOMER file operations
│   └── inventory_tools.py           # INVENTORY file operations
└── unibasic_programs/
    ├── GET.ORDER.DETAILS.B          # UniBasic: fetch order by ID
    ├── GET.CUSTOMER.INFO.B          # UniBasic: fetch customer record
    ├── CHECK.INVENTORY.B            # UniBasic: check stock levels
    ├── PROCESS.ORDER.B              # UniBasic: create/update order
    └── UPDATE.INVENTORY.B           # UniBasic: adjust inventory qty

### Setup
1. Copy `.env.example` to `.env` and fill in your values
2. Install dependencies: `pip install -r requirements.txt`
3. Catalog UniBasic programs in your UD account
4. Run: `python main_agent.py`
