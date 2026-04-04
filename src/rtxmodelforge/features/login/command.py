from __future__ import annotations
from typing import Annotated
import typer
from typer import Exit
import httpx
from rtxmodelforge.shared import config
from rtxmodelforge.shared.console import console, error_console

def login(
    token: Annotated[
        str, 
        typer.Option(
            "--token", 
            prompt="Informe seu HuggingFace Token (pressione Ctrl+C para cancelar)", 
            hide_input=True,
            help="HuggingFace API Token (exibe apenas os 4 primeiros caracteres)."
        )
    ]
) -> None:
    """Autentica no HuggingFace e salva o token localmente."""
    try:
        console.print("[cyan]Verificando token no HuggingFace...[/cyan]")
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://huggingface.co/api/whoami",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                name = user_data.get("name", "Usuário")
                config.save_hf_token(token)
                console.print(f"\n[bold green]✔ Autenticado como: {name}[/bold green]")
            elif response.status_code == 401:
                error_console.print(
                    "\n[bold red]✘ Token inválido.[/bold red] "
                    "Verifique suas configurações no HuggingFace."
                )
                raise Exit(1) from None
            else:
                error_console.print(f"\n[bold red]✘ Erro na API ({response.status_code}).[/bold red]")
                raise Exit(1) from None
                
    except httpx.RequestError as e:
        error_console.print(f"\n[bold red]✘ Erro de conexão:[/bold red] {e}")
        raise Exit(1) from None
