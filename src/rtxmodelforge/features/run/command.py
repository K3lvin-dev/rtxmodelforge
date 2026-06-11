from __future__ import annotations

from typing import Annotated

import typer

from rtxmodelforge.shared.cli_decorators import handle_cli_errors
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.workflow import _chat_with_engine, prepare_model


@handle_cli_errors(verbose=False)
def run(
    model_id: Annotated[
        str,
        typer.Argument(help="ID do modelo no HuggingFace (ex: meta-llama/Llama-3.1-8B)."),
    ],
    system_prompt: Annotated[
        str, typer.Option("--system", help="Instrução inicial do sistema.")
    ] = "Você é um assistente prestativo e especializado em hardware NVIDIA.",
    max_tokens: Annotated[
        int, typer.Option("--max-tokens", help="Máximo de novos tokens por resposta.")
    ] = 512,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Exibe logs detalhados na preparação.")
    ] = False,
) -> None:
    """Prepara automaticamente o melhor artefato para Tensor Cores e abre chat local."""
    chat_engine, _serve_engine, _gpu, selection = prepare_model(model_id, verbose=verbose)
    console.print(
        f"[bold green]Modo acelerado escolhido para sua RTX:[/bold green] "
        f"{selection.tensor_core_path_label} ({selection.acceleration_class.value})"
    )
    _chat_with_engine(chat_engine, system_prompt, max_tokens)
