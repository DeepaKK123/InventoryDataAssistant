"""
config/settings.py
──────────────────
Centralised configuration loaded from environment variables / .env file.
All other modules import from here — no raw os.getenv calls elsewhere.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AzureSettings:
    """Azure AI / Microsoft Foundry connection settings."""
    project_endpoint: str
    model_deployment_name: str

    @classmethod
    def from_env(cls) -> "AzureSettings":
        endpoint = os.getenv("PROJECT_ENDPOINT", "")
        model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
        if not endpoint:
            raise EnvironmentError(
                "PROJECT_ENDPOINT is not set. "
                "Copy .env.example to .env and fill in your Azure values."
            )
        return cls(project_endpoint=endpoint, model_deployment_name=model)


@dataclass(frozen=True)
class UDSettings:
    """UD server connection settings."""
    host: str
   # port: int
    username: str
    password: str
    account: str
    service: str

    # Cataloged UniBasic program names
    ub_get_order: str
    ub_get_customer: str
    ub_check_inventory: str
    ub_process_order: str
    ub_update_inventory: str

    @classmethod
    def from_env(cls) -> "UDSettings":
        return cls(
            host=os.getenv("UD_HOST", ""),
            username=os.getenv("UD_USERNAME", ""),
            password=os.getenv("UD_PASSWORD", ""),
            account=os.getenv("UD_ACCOUNT", ""),
            service="",
            ub_get_order=os.getenv("UB_GET_ORDER", "GET.ORDER.DETAILS"),
            ub_get_customer=os.getenv("UB_GET_CUSTOMER", "GET.CUSTOMER.INFO"),
            ub_check_inventory=os.getenv("UB_CHECK_INVENTORY", "CHECK.INVENTORY"),
            ub_process_order=os.getenv("UB_PROCESS_ORDER", "PROCESS.ORDER"),
            ub_update_inventory=os.getenv("UB_UPDATE_INVENTORY", "UPDATE.INVENTORY"),
        )


# Singleton instances — import these in other modules
azure_settings = AzureSettings.from_env()
ud_settings = UDSettings.from_env()

# Internal helper for cases where both settings objects are needed
_settings = {"azure": azure_settings, "ud": ud_settings}
