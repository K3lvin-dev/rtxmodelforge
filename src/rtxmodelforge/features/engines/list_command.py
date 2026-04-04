from __future__ import annotations

from rich.table import Table

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.console import console


def list_engines() -> None:
    """Lista todos os engines compilados e seus detalhes."""
    engines = store.list_engines()

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
