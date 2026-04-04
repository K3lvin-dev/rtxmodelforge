from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated, Dict, List

import typer
from rich.markdown import Markdown
from typer import Exit

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.gpu_profiler import profile_gpu
from rtxmodelforge.shared.panels import runtime_dashboard
from rtxmodelforge.shared.runtime_planner import format_efficiency, plan_runtime


def chat(
    engine_path: Annotated[
        Path, typer.Argument(help="Caminho para o diretório do engine compilado.")
    ],
    system_prompt: Annotated[
        str, typer.Option("--system", help="Instrução inicial do sistema.")
    ] = "Você é um assistente prestativo e especializado em hardware NVIDIA.",
    max_tokens: Annotated[
        int, typer.Option("--max-tokens", help="Máximo de novos tokens por resposta.")
    ] = 512,
) -> None:
    """Inicia um chat interativo no terminal usando o engine compilado."""

    meta = store.load_metadata(engine_path)
    if not meta:
        error_console.print(
            f"[bold red]✘ Nenhum engine válido encontrado em:[/bold red] {engine_path}"
        )
        raise Exit(1)

    if meta.engine_mode != "chat":
        error_console.print(
            f"[bold yellow]⚠ Este engine foi compilado para modo '{meta.engine_mode}'.[/bold yellow]\n"
            "  Para chat, use um engine compilado com modo 'chat' (batch=1).\n"
            "  Dica: use o diretório com sufixo '-chat', ex: .../fp8-chat/"
        )
        raise Exit(1)

    try:
        from tensorrt_llm._tensorrt_engine import LLM  # pyright: ignore[reportMissingImports]
        from tensorrt_llm.llmapi import (
            KvCacheConfig,
            SamplingParams,
        )  # pyright: ignore[reportMissingImports]
        from transformers import AutoTokenizer
    except ImportError:
        error_console.print(
            "[bold red]✘ Dependências ausentes (tensorrt_llm ou transformers).[/bold red]"
        )
        raise Exit(1) from None

    console.print(
        f"\n[bold green]Carregando motor e tokenizer...[/bold green] [cyan]{meta.model_id}[/cyan]"
    )

    try:
        # Detectar GPU e calcular plano de runtime
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
        )

        # Exibir dashboard antes de carregar o engine
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

        tokenizer = AutoTokenizer.from_pretrained(meta.model_id)

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
