from __future__ import annotations

from typing import Annotated

import typer
from typer import Exit

from rtxmodelforge.shared.cli_decorators import handle_cli_errors
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.json_output import print_json
from rtxmodelforge.shared.workflow import _chat_with_engine, prepare_model


@handle_cli_errors(verbose=False)
def run(
    model_id: Annotated[
        str,
        typer.Argument(help="ID do modelo no HuggingFace (ex: meta-llama/Llama-3.1-8B)."),
    ],
    system_prompt: Annotated[
        str, typer.Option("--system", help="Instrucao inicial do sistema.")
    ] = "Voce e um assistente prestativo e especializado em hardware NVIDIA.",
    max_tokens: Annotated[
        int, typer.Option("--max-tokens", help="Maximo de novos tokens por resposta.")
    ] = 512,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Exibe logs detalhados na preparacao.")
    ] = False,
    json: Annotated[
        bool,
        typer.Option("--json", help="Saida em formato JSON."),
    ] = False,
) -> None:
    """Prepara automaticamente o melhor artefato para Tensor Cores e abre chat local."""
    try:
        chat_engine, _serve_engine, _gpu, selection = prepare_model(model_id, verbose=verbose)
        if json:
            print_json({
                "ok": True,
                "output": f"Engine {model_id} pronto em {chat_engine}",
                "model_id": model_id,
                "quantization": selection.quantization.value,
                "engine_path": str(chat_engine),
            })
            return
        console.print(
            f"[bold green]Modo acelerado escolhido para sua RTX:[/bold green] "
            f"{selection.tensor_core_path_label} ({selection.acceleration_class.value})"
        )
        _chat_with_engine(chat_engine, system_prompt, max_tokens)
    except Exception as e:
        if json:
            print_json({"ok": False, "error": str(e)})
            raise Exit(1)
        raise
