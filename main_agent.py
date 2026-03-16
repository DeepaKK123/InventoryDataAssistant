"""
main_agent.py
────────
Entry point for the  AI Agent.

Builds and runs a Microsoft Agent Framework agent that:
  • Understands natural-language requests about Orders, Customers, Inventory
  • Calls the appropriate tool functions
  • Executes cataloged UniBasic programs on the UD server
  • Streams responses back to the console in real time

Usage
-----
    python main_agent.py
    python main.py --prompt "Show me order ORD001"   # non-interactive mode
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys


try:
    from agent_framework import Agent
    from agent_framework.azure import AzureOpenAIResponsesClient
    from azure.identity import AzureCliCredential
except ImportError as exc:
    print(
        f"[ERROR] Missing dependency: {exc}\n"
        "Run:  pip install -r requirements.txt\n"
        "and:  az login   (to authenticate with Azure)"
    )
    sys.exit(1)

from config import azure_settings
from tools import ALL_TOOLS

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[logging.FileHandler("logs/uopy.log", mode="a")],
)
logger = logging.getLogger(__name__)

# ─── Agent Instructions ───────────────────────────────────────────────────────

from pathlib import Path

def _load_agent_instructions() -> str:
        path = Path(__file__).parent / "config" / "agent_instructions.md"
        try:
                return path.read_text(encoding="utf-8")
        except Exception as exc:
                logger.error("Failed to load agent instructions from %s: %s", path, exc)
                return ""

AGENT_INSTRUCTIONS = _load_agent_instructions()

# ─── Build & run agent ────────────────────────────────────────────────────────

async def run_agent(user_prompt: str) -> None:
    """Create the agent, send one prompt, print the response."""
    credential = AzureCliCredential()

    async with (
        Agent(
            client=AzureOpenAIResponsesClient(
                credential=credential,
                deployment_name=azure_settings.model_deployment_name,
                project_endpoint=azure_settings.project_endpoint,
            ),
            instructions=AGENT_INSTRUCTIONS,
            tools=ALL_TOOLS,
        ) as agent,
    ):
        print(f"User: {user_prompt}")

        try:
            response = await agent.run([user_prompt])
            print("Agent Response")
        except Exception as exc:
            print(f"Agent error: {exc}")
            logger.exception("Agent run failed")


# ─── Interactive REPL ─────────────────────────────────────────────────────────

async def interactive_loop() -> None:
    """
    Run an interactive chat loop.  Type 'exit' or press Ctrl-C to quit.
    Each turn creates a fresh agent invocation (stateless between turns).
    """
    width = 80
    border = "+" + "-" * (width - 2) + "+"
    print(border)
    print("|" + "Hello! I'm your Inventory Data Assistant integrated with Unidata Demo account.".center(width - 2) + "|")
    print("|" + "I can help you with orders, customers, and inventory queries.".center(width - 2) + "|")
    print("|" + "Type 'exit' to quit.".center(width - 2) + "|")
    print(border)

    credential = AzureCliCredential()

    async with (
        Agent(
            client=AzureOpenAIResponsesClient(
                credential=credential,
                deployment_name=azure_settings.model_deployment_name,
                project_endpoint=azure_settings.project_endpoint,
            ),
            instructions=AGENT_INSTRUCTIONS,
            tools=ALL_TOOLS,
        ) as agent,
    ):
        conversation_history: list[str] = []

        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "bye"}:
                print("Goodbye.")
                break

            # Append new message to history for multi-turn context
            conversation_history.append(user_input)

            try:
                response = await agent.run(conversation_history.copy())
                conversation_history.append(f"Assistant: {response}")
                print()
                print(response)
            except Exception as exc:
                print(f"Error: {exc}")
                logger.exception("Agent run failed during interactive loop")


# ─── CLI entry point ──────────────────────────────────────────────────────────

def main_agent() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory Data AI Agent — Microsoft Agent Framework + UOPY"
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        default=None,
        help="Run a single non-interactive prompt and exit.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set log verbosity (default: INFO).",
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    if args.prompt:
        asyncio.run(run_agent(args.prompt))
    else:
        asyncio.run(interactive_loop())


if __name__ == "__main__":
    main_agent()
