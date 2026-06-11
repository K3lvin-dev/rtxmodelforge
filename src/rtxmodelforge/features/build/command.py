from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from typer import Exit

from rtxmodelforge.features.build import pipeline
from rtxmodelforge.features.build import types as build_types
from rtxmodelforge.features.build.downloader import fetch_params_billions
from rtxmodelforge.shared import config as shared_config
from rtxmodelforge.shared.build_planner import plan_build
from rtxmodelforge.shared.capabilities import select_acceleration_mode
from rtxmodelforge.shared.cli_decorators import handle_cli_errors
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.gpu_profiler import profile_gpu
from rtxmodelforge.shared.panels import header_panel, summary_panel


@handle_cli_errors(verbose=True)
def build(
    model_id: Annotated[
        str,
        typer.Argument(help="ID do modelo no HuggingFace (ex: meta-llama/Llama-3.1-8B).")
    ],
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Exibe logs detalhados durante a compilação.")
    ] = False,
) -> None:
    """Materializa cache otimizado para o melhor caminho de Tensor Cores da sua RTX."""

    console.print(f"[bold cyan]Iniciando processo de build para:[/bold cyan] {model_id}")

    gpu_profile = profile_gpu()
    if not gpu_profile:
        error_console.print("[bold red]✘ Nenhuma GPU NVIDIA compatível detectada.[/bold red]")
        raise Exit(1)

    if not gpu_profile.bandwidth_from_lookup:
        console.print(
            f"[yellow]⚠ GPU '{gpu_profile.name}' não está na tabela de bandwidth conhecidos. "
            f"Usando estimativa: {gpu_profile.memory_bandwidth_gbs:.0f} GB/s.[/yellow]"
        )

    settings = shared_config.get_settings()
    console.print("[dim]Buscando configuração do modelo...[/dim]")
    params_est = fetch_params_billions(model_id, settings.hf_token) or 8.0

    selection = select_acceleration_mode(gpu_profile, params_est)

    chat_plan, serve_plan = plan_build(
        profile=gpu_profile,
        params_b=params_est,
        quantization=selection.quantization,
    )

    console.print(
        header_panel(
            model_id=model_id,
            gpu=gpu_profile.name,
            architecture=gpu_profile.architecture.value,
            quantization=selection.effective_precision,
            rationale=selection.rationale,
            target_precision=selection.desired_precision,
            path_status=selection.acceleration_class.value,
            fallback_reason=selection.fallback_reason,
            chat_plan=chat_plan,
            serve_plan=serve_plan,
        )
    )

    if not typer.confirm("\nDeseja prosseguir com a compilação?", default=True):
        console.print("Operação cancelada pelo usuário.")
        raise Exit()

    build_conf = build_types.BuildConfig(
        model_id=model_id,
        weights_dir=Path("tmp"),  # pipeline ajustará isso
        gpu_info=gpu_profile,
        quantization=selection.quantization,
        quality_label=selection.quality_label,
        rationale=selection.rationale,
        params_billions=params_est,  # pipeline atualiza com valor exato no Stage 2
        verbose=verbose,
        target_precision=selection.desired_precision,
        effective_precision=selection.effective_precision,
        acceleration_class=selection.acceleration_class,
        target_architecture=selection.architecture,
        fallback_reason=selection.fallback_reason or "",
    )

    chat_engine_path, serve_engine_path = pipeline.run(build_conf)

    console.print(
        summary_panel(
            engine_paths=[chat_engine_path, serve_engine_path],
            next_commands=[
                f"rtxforge run {model_id}",
                f"rtxforge serve {model_id}",
            ],
        )
    )
