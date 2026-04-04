from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich import box
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from rtxmodelforge.shared.types import StageResult


def header_panel(
    model_id: str,
    gpu: str,
    quantization: str,
    rationale: str,
    time_estimate: str = "10–30 minutos",
) -> Panel:
    content = (
        f"[bold blue]RTX Model Forge — Building Engine[/bold blue]\n"
        f"Modelo:      [cyan]{model_id}[/cyan]\n"
        f"GPU:         [cyan]{gpu}[/cyan]\n"
        f"Formato:     [green]{quantization}[/green] ← automático\n"
        f"Motivo:      {rationale}\n"
        f"Estimativa:  [yellow]{time_estimate}[/yellow]. Não feche o terminal."
    )
    return Panel(content, box=box.ROUNDED, expand=False)


def stage_table(stages: list[StageResult]) -> Table:
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
    table.add_column("Status", width=6, justify="center")
    table.add_column("Etapa", ratio=1)
    table.add_column("Duração", width=12, justify="right")

    for stage in stages:
        table.add_row(
            stage.status.value, stage.label, stage.duration_display if stage.status == "✔" else "—"
        )
    return table


def summary_panel(engine_path: Path, next_commands: list[str]) -> Panel:
    commands_text = "\n".join([f"  [cyan]$ {cmd}[/cyan]" for cmd in next_commands])
    content = (
        f"[bold green]✔ Engine compilado com sucesso![/bold green]\n\n"
        f"Local: [blue]{engine_path}[/blue]\n\n"
        f"Próximos passos:\n{commands_text}"
    )
    return Panel(content, style="bold green", box=box.ROUNDED, expand=False)
