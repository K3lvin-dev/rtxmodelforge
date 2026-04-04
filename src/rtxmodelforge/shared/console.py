from __future__ import annotations
from typing import Final
from rich.console import Console

console: Final[Console] = Console(highlight=False)
error_console: Final[Console] = Console(stderr=True, style="bold red")
