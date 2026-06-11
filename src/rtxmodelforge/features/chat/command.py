from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from rtxmodelforge.shared.workflow import _chat_with_engine


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
    _chat_with_engine(engine_path, system_prompt, max_tokens)