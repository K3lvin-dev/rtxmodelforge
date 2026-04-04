from __future__ import annotations

import typer
from rich.live import Live
from rich.table import Table

from rtxmodelforge.features.doctor import checks
from rtxmodelforge.shared.console import console


def doctor() -> None:
    """Verifica a saúde do ambiente (GPU, Driver, CUDA)."""
    console.print("[bold blue]RTX Model Forge — Diagnóstico do Sistema[/bold blue]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", width=6, justify="center")
    table.add_column("Verificação", width=30)
    table.add_column("Detalhe", ratio=1)

    check_list = [
        checks.check_gpu,
        checks.check_nvidia_driver,
        checks.check_cuda_toolkit,
        checks.check_sm_support,
        checks.check_libopenmpi,
        checks.check_trtllm,
        checks.check_hf_token,
    ]

    has_failed = False

    with Live(table, refresh_per_second=4):
        for check_fn in check_list:
            res = check_fn()

            icon = (
                "[green]✔[/green]"
                if res.passed
                else ("[red]✘[/red]" if res.blocking else "[yellow]⚠[/yellow]")
            )
            table.add_row(icon, res.label, res.detail)

            if not res.passed and res.blocking:
                has_failed = True

    if has_failed:
        console.print(
            "\n[bold red]✘ Alguns checks críticos falharam.[/bold red] Verifique os detalhes acima."
        )
        raise typer.Exit(1)
    else:
        console.print("\n[bold green]✔ Ambiente pronto para uso![/bold green]")
