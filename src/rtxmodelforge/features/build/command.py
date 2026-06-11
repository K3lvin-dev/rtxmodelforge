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
from rtxmodelforge.shared.json_output import print_json
from rtxmodelforge.shared.panels import header_panel, summary_panel


@handle_cli_errors(verbose=True)
def build(
    model_id: Annotated[
        str,
        typer.Argument(help="ID do modelo no HuggingFace (ex: meta-llama/Llama-3.1-8B).")
    ],
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Exibe logs detalhados durante a compilacao.")
    ] = False,
    json: Annotated[
        bool,
        typer.Option("--json", help="Saida em formato JSON."),
    ] = False,
) -> None:
    """Compila dois engines TensorRT-LLM otimizados (chat + serve) para sua GPU RTX."""

    gpu_profile = profile_gpu()
    if not gpu_profile:
        if json:
            print_json({"ok": False, "error": "Nenhuma GPU NVIDIA compativel detectada."})
            raise Exit(1)
        error_console.print("[bold red]✘ Nenhuma GPU NVIDIA compativel detectada.[/bold red]")
        raise Exit(1)

    settings = shared_config.get_settings()
    params_est = fetch_params_billions(model_id, settings.hf_token) or 8.0
    selection = select_acceleration_mode(gpu_profile, params_est)
    chat_plan, serve_plan = plan_build(
        profile=gpu_profile,
        params_b=params_est,
        quantization=selection.quantization,
    )

    if json:
        build_conf = build_types.BuildConfig(
            model_id=model_id,
            weights_dir=Path("tmp"),
            gpu_info=gpu_profile,
            quantization=selection.quantization,
            quality_label=selection.quality_label,
            rationale=selection.rationale,
            params_billions=params_est,
            verbose=verbose,
            target_precision=selection.desired_precision,
            effective_precision=selection.effective_precision,
            acceleration_class=selection.acceleration_class,
            target_architecture=selection.architecture,
            fallback_reason=selection.fallback_reason or "",
        )
        try:
            chat_engine_path, serve_engine_path = pipeline.run(build_conf)
            print_json({
                "ok": True,
                "output": f"Build concluido: chat={chat_engine_path}, serve={serve_engine_path}",
                "model_id": model_id,
                "quantization": selection.quantization.value,
                "chat_engine_path": str(chat_engine_path),
                "serve_engine_path": str(serve_engine_path),
            })
        except Exception as e:
            print_json({"ok": False, "error": str(e)})
            raise Exit(1)
        return

    console.print(f"[bold cyan]Iniciando processo de build para:[/bold cyan] {model_id}")

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

    if not typer.confirm("\nDeseja prosseguir com a compilacao?", default=True):
        console.print("Operacao cancelada pelo usuario.")
        raise Exit()

    build_conf = build_types.BuildConfig(
        model_id=model_id,
        weights_dir=Path("tmp"),  # pipeline ajustara isso
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
