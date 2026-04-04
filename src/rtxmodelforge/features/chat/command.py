from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated, Dict, List

import typer
from rich.markdown import Markdown
from typer import Exit

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.console import console, error_console

# Janelas tentadas em ordem decrescente até uma caber na VRAM disponível.
# Cada valor deve ser múltiplo de tokens_per_block (32) para usar blocos inteiros.
_ATTENTION_WINDOW_CANDIDATES = [1440, 960, 768, 512, 256]


def _load_llm(LLM: type, engine_path: str, KvCacheConfig: type) -> tuple:
    """Tenta carregar o engine com janelas de atenção progressivamente menores."""
    last_err: Exception = RuntimeError("Nenhuma janela de atenção foi tentada.")
    for window in _ATTENTION_WINDOW_CANDIDATES:
        try:
            llm = LLM(
                model=engine_path,
                kv_cache_config=KvCacheConfig(max_attention_window=[window]),
            )
            return llm, window
        except RuntimeError as e:
            if "KV cache" in str(e) or "Executor worker" in str(e) or "window" in str(e).lower():
                last_err = e
                continue
            raise
    raise last_err


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
        with console.status("[dim]Carregando engine...[/dim]", spinner="dots"):
            llm, window = _load_llm(LLM, str(engine_path), KvCacheConfig)
        tokenizer = AutoTokenizer.from_pretrained(meta.model_id)

        history: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        console.print(
            f"\n[bold blue]Chat Iniciado![/bold blue] "
            f"[dim]({meta.model_id} · {meta.quantization.upper()} · "
            f"contexto {window} tokens)[/dim]\n"
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

            console.print(Markdown(response))
            console.print(f"[dim]⚡ {tps:.1f} tok/s · {n_tokens} tokens · {elapsed:.2f}s[/dim]\n")

            history.append({"role": "assistant", "content": response})

        llm.shutdown()
        console.print("\n[bold green]✔ Sessão de chat encerrada.[/bold green]")

    except Exception as e:
        error_console.print(f"[bold red]✘ Falha na inferência:[/bold red] {e}")
        raise Exit(1) from None
