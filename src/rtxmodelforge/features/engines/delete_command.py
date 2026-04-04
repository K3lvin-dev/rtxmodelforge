from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from typer import Exit

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.console import console, error_console


def delete(
    engine_path: Annotated[Path, typer.Argument(help="Caminho para o diretório do engine.")],
) -> None:
    """Remove um engine compilado do disco."""
    meta = store.load_metadata(engine_path)
    if not meta:
        error_console.print(
            f"[bold red]✘ Nenhum engine válido encontrado em:[/bold red] {engine_path}"
        )
        raise Exit(1)

    console.print("\n[bold yellow]⚠ Atenção:[/bold yellow] Você está prestes a remover o engine:")
    console.print(f"  Modelo:  [cyan]{meta.model_id}[/cyan]")
    console.print(f"  Formato: [green]{meta.quantization}[/green]")
    console.print(f"  Local:   {engine_path}\n")

    if typer.confirm("Tem certeza que deseja excluir?", default=False):
        try:
            store.delete_engine(engine_path)
            console.print("[bold green]✔ Engine removido com sucesso.[/bold green]")
        except Exception as e:
            error_console.print(f"[bold red]✘ Falha ao remover engine:[/bold red] {e}")
            raise Exit(1) from None
    else:
        console.print("Operação cancelada.")
