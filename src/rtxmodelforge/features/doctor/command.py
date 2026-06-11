from __future__ import annotations

from rich.live import Live
from rich.table import Table
from typer import Exit

from rtxmodelforge.features.doctor import checks
from rtxmodelforge.shared.capabilities import AccelerationClass, summarize_doctor
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.gpu_profiler import profile_gpu


def doctor() -> None:
    """Verifica a saúde do ambiente (GPU, Driver, CUDA)."""
    console.print("[bold blue]RTX Model Forge — Diagnóstico do Sistema[/bold blue]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", width=6, justify="center")
    table.add_column("Verificação", width=30)
    table.add_column("Detalhe", ratio=1)

    # Profile GPU uma vez e passa para todos os checks que precisam
    gpu_profile = profile_gpu()

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

    trtllm_res = checks.check_trtllm()
    cuda_res = checks.check_cuda_toolkit()
    summary = summarize_doctor(gpu_profile, trtllm_res.passed, cuda_res.passed)

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
            "\n[bold red]✘ Alguns checks críticos falharam.[/bold red] Verifique os detalhes acima."
        )
        raise Exit(1)
    else:
        console.print("\n[bold green]✔ Ambiente pronto para máxima aceleração RTX.[/bold green]")
