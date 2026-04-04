from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Annotated
import typer
from typer import Exit
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.features.engines import store

def serve(
    engine_path: Annotated[
        Path, 
        typer.Argument(help="Caminho para o diretório do engine compilado.")
    ],
    port: Annotated[int, typer.Option("--port", help="Porta para o servidor REST.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Host para o servidor REST.")] = "127.0.0.1",
) -> None:
    """Sobe um servidor REST compatível com OpenAI usando o engine compilado."""
    
    meta = store.load_metadata(engine_path)
    if not meta:
        error_console.print(f"[bold red]✘ Nenhum engine válido em:[/bold red] {engine_path}")
        raise Exit(1) from None
        
    console.print(f"\n[bold blue]Iniciando Servidor de Inferência[/bold blue]")
    console.print(f"  Modelo:    [cyan]{meta.model_id}[/cyan]")
    console.print(f"  GPU:       [cyan]{meta.gpu_model}[/cyan]")
    console.print(f"  Formato:   [green]{meta.quantization.upper()}[/green]")
    console.print(f"  Endereço:  [bold underline]http://{host}:{port}/v1/...[/bold underline]\n")
    
    if host == "0.0.0.0":
        console.print("[yellow]⚠ Aviso: O servidor estará exposto na rede local.[/yellow]")
        if not typer.confirm("Deseja continuar?", default=False):
            raise Exit() from None

    cmd = [
        "trtllm-serve",
        "serve",
        str(engine_path),
        "--tokenizer", meta.model_id,
        "--host", host,
        "--port", str(port)
    ]
    
    try:
        console.print("[dim]Pressione Ctrl+C para encerrar o servidor.[/dim]\n")
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[bold green]✔ Servidor encerrado pelo usuário.[/bold green]")
    except subprocess.CalledProcessError as e:
        error_console.print(f"[bold red]✘ Falha ao iniciar trtllm-serve:[/bold red] {e}")
        raise Exit(1) from None
    except FileNotFoundError:
        error_console.print("[bold red]✘ Comando 'trtllm-serve' não encontrado.[/bold red]")
        raise Exit(1) from None
