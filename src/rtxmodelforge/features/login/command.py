from __future__ import annotations

from typing import Annotated

import httpx
import typer
from typer import Exit

from rtxmodelforge.shared import config
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.json_output import print_json


def login(
    token: Annotated[
        str,
        typer.Option(
            "--token",
            prompt="Informe seu HuggingFace Token (pressione Ctrl+C para cancelar)",
            hide_input=True,
            help="HuggingFace API Token (exibe apenas os 4 primeiros caracteres).",
        ),
    ],
    json: Annotated[
        bool,
        typer.Option("--json", help="Saida em formato JSON."),
    ] = False,
) -> None:
    """Autentica no HuggingFace e salva o token localmente."""
    try:
        if not json:
            console.print("[cyan]Verificando token no HuggingFace...[/cyan]")

        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://huggingface.co/api/whoami-v2", headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                user_data = response.json()
                name = user_data.get("name", "Usuario")
                config.save_hf_token(token)
                if json:
                    print_json({"ok": True, "output": f"Autenticado como: {name}"})
                else:
                    console.print(f"\n[bold green]✔ Autenticado como: {name}[/bold green]")
            elif response.status_code == 401:
                if json:
                    print_json({"ok": False, "error": "Token invalido."})
                else:
                    error_console.print(
                        "\n[bold red]✘ Token invalido.[/bold red] "
                        "Verifique suas configuracoes no HuggingFace."
                    )
                raise Exit(1) from None
            else:
                if json:
                    print_json({"ok": False, "error": f"Erro na API ({response.status_code})."})
                else:
                    error_console.print(
                        f"\n[bold red]✘ Erro na API ({response.status_code}).[/bold red]"
                    )
                raise Exit(1) from None

    except httpx.RequestError as e:
        if json:
            print_json({"ok": False, "error": f"Erro de conexao: {e}"})
            raise Exit(1)
        error_console.print(f"\n[bold red]✘ Erro de conexao:[/bold red] {e}")
        raise Exit(1) from None
