from __future__ import annotations
from typing import Optional
import typer
from rtxmodelforge import __version__
from rtxmodelforge.features.doctor.command import doctor
from rtxmodelforge.features.login.command import login
from rtxmodelforge.features.engines.list_command import list_engines
from rtxmodelforge.features.engines.delete_command import delete
from rtxmodelforge.features.build.command import build
from rtxmodelforge.features.serve.command import serve
from rtxmodelforge.features.chat.command import chat

app = typer.Typer(
    name="rtxforge",
    help="CLI para orquestrar o pipeline TensorRT-LLM em GPUs RTX.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"rtxforge {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True, help="Exibe a versão e sai."
    ),
) -> None:
    pass

app.command()(build)
app.command()(serve)
app.command()(chat)
app.command()(login)
app.command()(doctor)
app.command(name="list")(list_engines)
app.command()(delete)

if __name__ == "__main__":
    app()
