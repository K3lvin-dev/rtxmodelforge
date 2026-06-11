from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.json_output import print_json


def list_engines(
    json: Annotated[
        bool,
        typer.Option("--json", help="Saida em formato JSON em vez de tabela rich."),
    ] = False,
) -> None:
    """Lista todos os engines compilados e seus detalhes."""
    engines = store.list_engines()

    if json:
        items = []
        for _path, meta in engines:
            items.append(
                {
                    "model_id": meta.model_id,
                    "gpu_model": meta.gpu_model,
                    "quantization": meta.quantization,
                    "quality_label": meta.quality_label,
                    "engine_mode": meta.engine_mode,
                    "max_batch_size": meta.max_batch_size,
                    "max_seq_len": meta.max_seq_len,
                    "vram_used_gb": meta.vram_used_gb,
                    "engine_size_gb": meta.engine_size_gb,
                    "built_at": meta.built_at.isoformat(),
                    "architecture": meta.architecture,
                    "sm_version": meta.sm_version,
                    "engine_path": str(meta.engine_path),
                }
            )
        print_json({"engines": items, "count": len(items)})
        return

    if not engines:
        console.print("[yellow]Nenhum engine encontrado em ~/.rtxmodelforge/engines/[/yellow]")
        console.print("Tente compilar um com: [cyan]rtxforge build <model_id>[/cyan]")
        return

    console.print(f"[bold blue]Motores Compilados ({len(engines)})[/bold blue]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Modelo", ratio=1)
    table.add_column("Modo", width=8)
    table.add_column("GPU", width=20)
    table.add_column("Formato", width=10)
    table.add_column("Batch", width=7, justify="right")
    table.add_column("Seq Len", width=9, justify="right")
    table.add_column("VRAM", width=10, justify="right")
    table.add_column("Compilado em", width=18)

    for _path, meta in engines:
        mode = getattr(meta, "engine_mode", "—")
        batch = str(getattr(meta, "max_batch_size", "—"))
        seq_len = str(getattr(meta, "max_seq_len", "—"))
        mode_color = "cyan" if mode == "chat" else "yellow"
        table.add_row(
            meta.model_id,
            f"[{mode_color}]{mode}[/{mode_color}]",
            meta.gpu_model,
            meta.quantization.upper(),
            batch,
            seq_len,
            f"{meta.vram_used_gb:.1f}GB",
            meta.built_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
