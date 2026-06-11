from __future__ import annotations

from typing import Annotated

import typer
from rich.live import Live
from rich.table import Table
from typer import Exit

from rtxmodelforge import __version__
from rtxmodelforge.features.doctor import checks
from rtxmodelforge.shared.capabilities import AccelerationClass, summarize_doctor
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.gpu_profiler import profile_gpu, read_gpu_metrics
from rtxmodelforge.shared.json_output import print_json


def doctor(
    json: Annotated[
        bool,
        typer.Option("--json", help="Saida em formato JSON em vez de tabela rich."),
    ] = False,
) -> None:
    """Verifica a saude do ambiente (GPU, Driver, CUDA)."""
    gpu_profile = profile_gpu()
    trtllm_res = checks.check_trtllm()
    cuda_res = checks.check_cuda_toolkit()
    summary = summarize_doctor(gpu_profile, trtllm_res.passed, cuda_res.passed)

    if json:
        gpu_data = None
        if gpu_profile:
            metrics = read_gpu_metrics()
            gpu_data = {
                "name": gpu_profile.name,
                "sm_version": gpu_profile.sm_version,
                "vram_total_gb": gpu_profile.vram_total_gb,
                "vram_free_gb": gpu_profile.vram_free_gb,
                "driver_version": gpu_profile.driver_version,
                "detected": True,
                "temperature": metrics["temperature"],
                "utilization": metrics["utilization"],
                "clock_core": metrics["clock_core"],
                "clock_mem": metrics["clock_mem"],
            }
        print_json(
            {
                "gpu": gpu_data,
                "version": __version__,
                "readiness": summary.readiness.value,
                "best_path": summary.best_path_label,
                "detail": summary.detail,
                "trtllm_installed": trtllm_res.passed,
                "cuda_ok": cuda_res.passed,
            }
        )
        if not gpu_profile or gpu_profile.sm_version < 80:
            raise Exit(1)
        return

    console.print("[bold blue]RTX Model Forge — Diagnostico do Sistema[/bold blue]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", width=6, justify="center")
    table.add_column("Verificacao", width=30)
    table.add_column("Detalhe", ratio=1)

    check_list = [
        lambda: checks.check_gpu(gpu_profile),
        lambda: checks.check_nvidia_driver(gpu_profile),
        checks.check_cuda_toolkit,
        lambda: checks.check_sm_support(gpu_profile),
        lambda: checks.check_tensor_core_modes(gpu_profile),
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

    style = {
        AccelerationClass.IDEAL: "bold green",
        AccelerationClass.PARTIAL: "bold yellow",
        AccelerationClass.FALLBACK: "bold red",
    }[summary.readiness]
    console.print(
        f"\n[{style}]Resultado:[/{style}] {summary.readiness.value} "
        f"· melhor caminho esperado: {summary.best_path_label}"
    )
    console.print(summary.detail)

    if has_failed:
        console.print(
            "\n[bold red]✘ Alguns checks criticos falharam.[/bold red] Verifique os detalhes acima."
        )
        raise Exit(1)
    else:
        console.print("\n[bold green]✔ Ambiente pronto para maxima aceleracao RTX.[/bold green]")
