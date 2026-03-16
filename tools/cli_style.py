"""
CLI styling helper. Provides simple helper functions
for printing user/assistant messages and prompts in a plain way.
"""
from __future__ import annotations

from typing import Optional


class _PlainFallback:
    def input(self, prompt: str = "") -> str:
        return input(prompt)

    def print(self, *args, **kwargs) -> None:
        print(*args)


console = _PlainFallback()

def header() -> None:
    console.print("UD AI Agent - Connected to: Orders · Customers · Inventory")

def input_prompt(prompt: Optional[str] = None) -> str:
    prompt_text = "\nYou: " if prompt is None else prompt
    return console.input(prompt_text)

def print_user(message: str) -> None:
    console.print("User:", message)

def print_agent(message: str) -> None:
    console.print("Assistant:", message)

def print_info(message: str) -> None:
    console.print(message)

def print_error(message: str) -> None:
    console.print("Error:", message)
