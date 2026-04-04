from __future__ import annotations

from pathlib import Path
from typing import Annotated, Dict, List

import typer
from typer import Exit
from rich.markdown import Markdown

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.console import console, error_console


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
        from tensorrt_llm.llmapi import LLM, SamplingParams
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
        # Carrega o engine compilado
        llm = LLM(model=str(engine_path))
        tokenizer = AutoTokenizer.from_pretrained(meta.model_id)

        # Histórico de mensagens
        history: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        console.print(
            "\n[bold blue]Chat Iniciado![/bold blue] "
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

            # Aplica chat template
            prompt = tokenizer.apply_chat_template(
                history, tokenize=False, add_generation_prompt=True
            )

            # Inferência
            sampling_params = SamplingParams(max_tokens=max_tokens)

            console.print("\n[bold green]Assistente:[/bold green]", end=" ")

            with console.status("[dim]Gerando...[/dim]", spinner="dots"):
                outputs = llm.generate([prompt], sampling_params=sampling_params)
                response = outputs[0].outputs[0].text

            console.print(Markdown(response))
            console.print("")

            # Atualiza histórico
            history.append({"role": "assistant", "content": response})

        llm.shutdown()
        console.print("\n[bold green]✔ Sessão de chat encerrada.[/bold green]")

    except Exception as e:
        error_console.print(f"[bold red]✘ Falha na inferência:[/bold red] {e}")
        raise Exit(1) from None
