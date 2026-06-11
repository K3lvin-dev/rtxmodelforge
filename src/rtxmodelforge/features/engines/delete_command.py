from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from typer import Exit

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.json_output import print_json


def delete(
    engine_path: Annotated[Path, typer.Argument(help="Caminho para o diretorio do engine.")],
    json: Annotated[
        bool,
        typer.Option("--json", help="Saida em formato JSON."),
    ] = False,
) -> None:
    """Remove um engine compilado do disco."""
    meta = store.load_metadata(engine_path)
    if not meta:
        if json:
            print_json({"ok": False, "error": f"Nenhum engine valido em: {engine_path}"})
            raise Exit(1)
        error_console.print(
            f"[bold red]M Nenhum engine valido encontrado em:[/bold red] {engine_path}"
        )
        raise Exit(1)

    if json:
        try:
            store.delete_engine(engine_path)
            print_json({"ok": True, "output": f"Engine {meta.model_id} removido."})
        except Exception as e:
            print_json({"ok": False, "error": str(e)})
            raise Exit(1)
        return

    console.print("\n[bold yellow]Atencao:[/bold yellow] Voce esta prestes a remover o engine:")
    console.print(f"  Modelo:  [cyan]{meta.model_id}[/cyan]")
    console.print(f"  Formato: [green]{meta.quantization}[/green]")
    console.print(f"  Local:   {engine_path}\n")

    if typer.confirm("Tem certeza que deseja excluir?", default=False):
        try:
            store.delete_engine(engine_path)
            console.print("[bold green]Engine removido com sucesso.[/bold green]")
        except Exception as e:
            error_console.print(f"[bold red]Falha ao remover engine:[/bold red] {e}")
            raise Exit(1) from None
    else:
        console.print("Operacao cancelada.")
