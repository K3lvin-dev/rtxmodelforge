from __future__ import annotations

import functools
import traceback
from typing import Callable, TypeVar

from typer import Exit

from rtxmodelforge.features.build.types import GatedModelError
from rtxmodelforge.shared import types as shared_types
from rtxmodelforge.shared.console import error_console

F = TypeVar("F", bound=Callable)


def handle_cli_errors(verbose: bool = False) -> Callable[[F], F]:
    """Decorator que captura exceções comuns de CLI e exibe mensagens formatadas.

    Args:
        verbose: Se True, exibe traceback completo para erros genéricos.

    Usage:
        @handle_cli_errors(verbose=True)
        def my_command():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except GatedModelError:
                # Extrai model_id dos args ou kwargs
                model_id = "modelo"
                if args and len(args) > 0 and isinstance(args[0], str):
                    model_id = args[0]
                elif "model_id" in kwargs:
                    model_id = kwargs["model_id"]

                error_console.print(
                    f"\n[bold red]✘ Acesso negado ao modelo '[cyan]{model_id}[/cyan]'.[/bold red]\n\n"
                    "  Este modelo requer autorização. Para resolver:\n\n"
                    f"  [bold]1.[/bold] Aceite os termos em: [cyan]https://huggingface.co/{model_id}[/cyan]\n"
                    "  [bold]2.[/bold] Gere um token em:    [cyan]https://huggingface.co/settings/tokens[/cyan]\n"
                    "  [bold]3.[/bold] Autentique-se com:   [cyan]rtxforge login[/cyan]\n"
                )
                raise Exit(1) from None
            except shared_types.UnsupportedGPUError as e:
                error_console.print(f"[bold red]✘ GPU não suportada:[/bold red] {e}")
                raise Exit(1) from None
            except shared_types.InsufficientVRAMError as e:
                error_console.print(f"[bold red]✘ VRAM insuficiente:[/bold red] {e}")
                raise Exit(1) from None
            except FileNotFoundError as e:
                error_console.print(f"[bold red]✘ Arquivo não encontrado:[/bold red] {e}")
                raise Exit(1) from None
            except PermissionError as e:
                error_console.print(f"[bold red]✘ Erro de permissão:[/bold red] {e}")
                raise Exit(1) from None
            except RuntimeError as e:
                error_console.print(f"[bold red]✘ Erro de runtime:[/bold red] {e}")
                if verbose:
                    traceback.print_exc()
                raise Exit(1) from None
            except Exception as e:
                error_console.print(f"[bold red]✘ Erro inesperado:[/bold red] {e}")
                if verbose:
                    traceback.print_exc()
                raise Exit(1) from None

        return wrapper  # type: ignore[return-value]

    return decorator
