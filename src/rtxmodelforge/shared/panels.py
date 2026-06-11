from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rich import box
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from rtxmodelforge.shared.build_planner import BuildPlan
    from rtxmodelforge.shared.runtime_planner import RuntimePlan
    from rtxmodelforge.shared.types import StageResult


def header_panel(
    model_id: str,
    gpu: str,
    architecture: str,
    quantization: str,
    rationale: str,
    target_precision: str,
    path_status: str,
    fallback_reason: Optional[str] = None,
    time_estimate: str = "20–60 minutos (2 engines)",
    chat_plan: Optional["BuildPlan"] = None,
    serve_plan: Optional["BuildPlan"] = None,
) -> Panel:
    content = (
        f"[bold blue]RTX Model Forge — Building Engines[/bold blue]\n"
        f"Modelo:      [cyan]{model_id}[/cyan]\n"
        f"GPU:         [cyan]{gpu}[/cyan]\n"
        f"Arquitetura: [cyan]{architecture}[/cyan]\n"
        f"Modo RTX:    [green]{quantization}[/green] (alvo {target_precision})\n"
        f"Status:      [bold]{path_status}[/bold]\n"
        f"Motivo:      {rationale}\n"
        f"Estimativa:  [yellow]{time_estimate}[/yellow]. Não feche o terminal."
    )

    if fallback_reason:
        content += f"\nFallback:    {fallback_reason}"

    if chat_plan and serve_plan:
        content += (
            f"\n\n[bold]Planos calculados:[/bold]\n"
            f"  [cyan]Chat[/cyan]:  batch={chat_plan.max_batch_size} "
            f"seq={chat_plan.max_seq_len} "
            f"kv≈{chat_plan.kv_cache_gb:.1f}GB "
            f"~[green]{chat_plan.theoretical_max_tps:.0f}[/green] tok/s teórico\n"
            f"  [cyan]Serve[/cyan]: batch={serve_plan.max_batch_size} "
            f"seq={serve_plan.max_seq_len} "
            f"kv≈{serve_plan.kv_cache_gb:.1f}GB "
            f"~[green]{serve_plan.theoretical_max_tps:.0f}[/green] tok/s teórico"
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


def summary_panel(engine_paths: list[Path], next_commands: list[str]) -> Panel:
    paths_text = "\n".join([f"  [blue]{p}[/blue]" for p in engine_paths])
    commands_text = "\n".join([f"  [cyan]$ {cmd}[/cyan]" for cmd in next_commands])
    content = (
        f"[bold green]✔ Cache Tensor Core preparado com sucesso![/bold green]\n\n"
        f"Locais:\n{paths_text}\n\n"
        f"Próximos passos:\n{commands_text}"
    )
    return Panel(content, style="bold green", box=box.ROUNDED, expand=False)


def runtime_dashboard(plan: "RuntimePlan") -> Panel:
    """Exibe painel de dashboard no startup do chat/serve com info de VRAM e performance."""
    vram_pct = (
        (plan.vram_total_gb - plan.vram_free_gb) / plan.vram_total_gb * 100
        if plan.vram_total_gb > 0
        else 0
    )
    vram_used_gb = plan.vram_total_gb - plan.vram_free_gb

    content_lines = [
        "[bold blue]RTX Model Forge · Runtime Dashboard[/bold blue]",
        f"  GPU:        [cyan]{plan.gpu_name}[/cyan]",
        f"  Arquitet.:  [cyan]{plan.architecture_label}[/cyan]",
        f"  VRAM:       [yellow]{vram_used_gb:.1f}[/yellow] / {plan.vram_total_gb:.1f} GB "
        f"({vram_pct:.0f}% alocada)",
        f"  Engine:     [cyan]{plan.model_id}[/cyan] · [green]{plan.quantization}[/green] · "
        f"modo [bold]{plan.mode.value}[/bold]",
        f"  Modo RTX:   {plan.acceleration_class} · {plan.tensor_core_path_label}",
        f"  KV Cache:   {plan.max_attention_window} tokens · {plan.kv_cache_gb:.1f} GB",
        f"  Janela:     {plan.max_attention_window} tokens",
        f"  Batch:      {plan.max_batch_size}",
        f"  Max teór.:  ~[green]{plan.theoretical_max_tps:.0f}[/green] tok/s",
    ]

    if plan.fallback_reason:
        content_lines.append(f"  Fallback:   {plan.fallback_reason}")

    if plan.vram_warning:
        content_lines.append("")
        content_lines.append(f"  [bold yellow]⚠[/bold yellow] {plan.vram_warning}")

    content = "\n".join(content_lines)
    return Panel(content, box=box.ROUNDED, expand=False)
