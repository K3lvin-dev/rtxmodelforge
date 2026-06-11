from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

from rich.markdown import Markdown
from typer import Exit

from rtxmodelforge.features.build import pipeline
from rtxmodelforge.features.build import types as build_types
from rtxmodelforge.features.build.downloader import fetch_params_billions
from rtxmodelforge.features.engines import store
from rtxmodelforge.features.engines.types import EngineMetadata
from rtxmodelforge.shared import config as shared_config
from rtxmodelforge.shared.capabilities import AccelerationSelection, select_acceleration_mode
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.gpu_profiler import GPUProfile, profile_gpu
from rtxmodelforge.shared.panels import runtime_dashboard
from rtxmodelforge.shared.runtime_planner import format_efficiency, plan_runtime
from rtxmodelforge.shared.tokenizer_cache import get_tokenizer


def prepare_model(
    model_id: str, verbose: bool = False
) -> tuple[Path, Path, GPUProfile, AccelerationSelection]:
    gpu_profile = profile_gpu()
    if not gpu_profile:
        error_console.print("[bold red]✘ Nenhuma GPU NVIDIA compatível detectada.[/bold red]")
        raise Exit(1)

    settings = shared_config.get_settings()
    params_est = fetch_params_billions(model_id, settings.hf_token) or 8.0
    selection = select_acceleration_mode(gpu_profile, params_est)

    chat_engine_dir = store.get_engine_dir(model_id, selection.quantization, "chat")
    serve_engine_dir = store.get_engine_dir(model_id, selection.quantization, "serve")

    if _is_engine_optimal(store.load_metadata(chat_engine_dir), selection) and _is_engine_optimal(
        store.load_metadata(serve_engine_dir), selection
    ):
        console.print(
            f"[green]Usando cache otimizado existente:[/green] "
            f"{selection.tensor_core_path_label} em {selection.architecture_label}."
        )
        return chat_engine_dir, serve_engine_dir, gpu_profile, selection

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
    chat_path, serve_path = pipeline.run(build_conf)
    return chat_path, serve_path, gpu_profile, selection


def _is_engine_optimal(
    metadata: Optional[EngineMetadata], selection: AccelerationSelection
) -> bool:
    if metadata is None:
        return False
    return (
        metadata.quantization.lower() == selection.quantization.value
        and metadata.target_architecture == selection.architecture.value
        and metadata.target_precision == selection.desired_precision
        and metadata.effective_precision == selection.effective_precision
        and metadata.acceleration_class == selection.acceleration_class.value
        and (metadata.fallback_reason or "") == (selection.fallback_reason or "")
    )


def _chat_with_engine(engine_path: Path, system_prompt: str, max_tokens: int) -> None:
    """Executa loop de chat interativo com o engine compilado."""
    meta = store.load_metadata(engine_path)
    if not meta:
        error_console.print(
            f"[bold red]✘ Nenhum engine válido encontrado em:[/bold red] {engine_path}"
        )
        raise Exit(1)

    if meta.engine_mode != "chat":
        error_console.print(
            f"[bold yellow]⚠ Este engine foi compilado para modo '{meta.engine_mode}'.[/bold yellow]\n"
            " Para chat, use um engine compilado com modo 'chat' (batch=1).\n"
            " Dica: use o diretório com sufixo '-chat', ex: .../fp8-chat/"
        )
        raise Exit(1)

    try:
        from tensorrt_llm._tensorrt_engine import LLM  # pyright: ignore[reportMissingImports]
        from tensorrt_llm.llmapi import (  # pyright: ignore[reportMissingImports]
            KvCacheConfig,
            SamplingParams,
        )
    except ImportError:
        error_console.print(
            "[bold red]✘ Dependências ausentes (tensorrt_llm ou transformers).[/bold red]"
        )
        raise Exit(1) from None

    console.print(
        f"\n[bold green]Carregando motor e tokenizer...[/bold green] [cyan]{meta.model_id}[/cyan]"
    )

    try:
        gpu_profile = profile_gpu()
        if gpu_profile is None:
            error_console.print("[bold red]✘ GPU não detectada.[/bold red]")
            raise Exit(1)

        runtime_plan = plan_runtime(
            profile=gpu_profile,
            model_id=meta.model_id,
            quantization_str=meta.quantization.lower(),
            params_b=meta.params_billions,
            engine_mode=meta.engine_mode,
            max_batch_size=meta.max_batch_size,
            engine_size_gb=meta.engine_size_gb,
            architecture_label=meta.target_architecture or gpu_profile.architecture.value,
            acceleration_class=meta.acceleration_class or "modo acelerado parcial",
            tensor_core_path_label=meta.effective_precision or meta.quantization.upper(),
            fallback_reason=meta.fallback_reason or None,
        )

        console.print(runtime_dashboard(runtime_plan))

        if runtime_plan.vram_warning:
            console.print(f"[bold yellow]⚠ Aviso:[/bold yellow] {runtime_plan.vram_warning}\n")

        with console.status("[dim]Carregando engine...[/dim]", spinner="dots"):
            llm = LLM(
                model=str(engine_path),
                kv_cache_config=KvCacheConfig(
                    max_attention_window=[runtime_plan.max_attention_window]
                ),
            )

        tokenizer = get_tokenizer(meta.model_id)

        history: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        console.print(
            f"\n[bold blue]Chat Iniciado![/bold blue] "
            f"[dim]({meta.model_id} · {meta.quantization.upper()} · "
            f"janela {runtime_plan.max_attention_window} tokens)[/dim]\n"
            "Digite [bold magenta]/exit[/bold magenta] para sair "
            "ou [bold magenta]/clear[/bold magenta] para reiniciar.\n"
        )

        while True:
            user_input = console.input("[bold cyan]Você:[/bold cyan] ").strip()

            if not user_input:
                continue
            if user_input.lower() == "/exit":
                break
            if user_input.lower() == "/clear":
                history = [{"role": "system", "content": system_prompt}]
                console.clear()
                console.print("[bold blue]Histórico limpo.[/bold blue]\n")
                continue

            history.append({"role": "user", "content": user_input})

            prompt = tokenizer.apply_chat_template(
                history, tokenize=False, add_generation_prompt=True
            )

            sampling_params = SamplingParams(max_tokens=max_tokens)

            console.print("\n[bold green]Assistente:[/bold green]")

            with console.status("[dim]Gerando...[/dim]", spinner="dots"):
                t0 = time.perf_counter()
                outputs = llm.generate([prompt], sampling_params=sampling_params)
                elapsed = time.perf_counter() - t0

            response = outputs[0].outputs[0].text
            n_tokens = len(tokenizer.encode(response, add_special_tokens=False))
            tps = n_tokens / elapsed if elapsed > 0 else 0

            efficiency = format_efficiency(tps, runtime_plan.theoretical_max_tps)
            efficiency_str = f" · {efficiency}" if efficiency else ""

            console.print(Markdown(response))
            console.print(
                f"[dim]⚡ {tps:.1f} tok/s{efficiency_str} · {n_tokens} tokens · {elapsed:.2f}s[/dim]\n"
            )

            history.append({"role": "assistant", "content": response})

        llm.shutdown()
        console.print("\n[bold green]✔ Sessão de chat encerrada.[/bold green]")

    except Exception as e:
        error_console.print(f"[bold red]✘ Falha na inferência:[/bold red] {e}")
        raise Exit(1) from None
