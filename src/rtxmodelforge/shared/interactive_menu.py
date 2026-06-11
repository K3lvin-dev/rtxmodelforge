from __future__ import annotations

from pathlib import Path
from typing import Optional

import questionary
import typer

from rtxmodelforge.features.build.command import build as build_cmd
from rtxmodelforge.features.chat.command import chat as chat_cmd
from rtxmodelforge.features.doctor.command import doctor as doctor_cmd
from rtxmodelforge.features.engines import store
from rtxmodelforge.features.engines.delete_command import delete as delete_cmd
from rtxmodelforge.features.engines.list_command import list_engines as list_engines_cmd
from rtxmodelforge.features.login.command import login as login_cmd
from rtxmodelforge.features.run.command import run as run_cmd
from rtxmodelforge.features.serve.command import serve as serve_cmd
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.splash import render_splash

# Usa questionary.Choice para separar label exibida do valor canônico retornado.
_MENU_CHOICES = [
    questionary.Choice("Prepare  — preparar cache otimizado", value="Prepare"),
    questionary.Choice("Serve    — iniciar servidor de inferência", value="Serve"),
    questionary.Choice("Run      — conversar por model_id", value="Run"),
    questionary.Choice("Chat     — conversar com um modelo",   value="Chat"),
    questionary.Choice("Login    — autenticar no HuggingFace", value="Login"),
    questionary.Choice("List     — listar engines compilados", value="List"),
    questionary.Choice("Delete   — remover um engine",         value="Delete"),
    questionary.Choice("Doctor   — verificar ambiente",        value="Doctor"),
    questionary.Choice("Sair",                                 value="Sair"),
]


def _select_engine_path(prompt: str) -> Optional[Path]:
    """Mostra engines disponíveis como lista ou pede caminho manual."""
    engines = store.list_engines()
    if engines:
        choices = [str(path) for path, _ in engines] + ["Digitar caminho manualmente"]
        selected = questionary.select(prompt, choices=choices).ask()
        if selected is None:
            return None
        if selected == "Digitar caminho manualmente":
            selected = questionary.text("Caminho do engine:").ask()
        return Path(selected) if selected else None
    else:
        result = questionary.text(prompt).ask()
        return Path(result) if result else None


def run_interactive_menu() -> None:
    """Exibe splash screen + menu interativo. Despacha para o comando selecionado."""
    console.print(render_splash())
    console.print()

    # questionary.Choice retorna value (string canônica), não o título exibido.
    choice = questionary.select(
        "O que você quer fazer?",
        choices=_MENU_CHOICES,
    ).ask()

    if choice is None:
        return  # Ctrl+C

    if choice in {"Prepare", "Build"}:
        model_id = questionary.text("ID do modelo no HuggingFace (ex: meta-llama/Llama-3.1-8B):").ask()
        if model_id:
            build_cmd(model_id=model_id, verbose=False)

    elif choice == "Serve":
        if store.list_engines():
            engine_path = _select_engine_path("Selecione o engine para servir:")
            if engine_path:
                serve_cmd(engine_path=engine_path)
        else:
            model_id = questionary.text("ID do modelo para servir:").ask()
            if model_id:
                serve_cmd(model_id=model_id)

    elif choice == "Run":
        model_id = questionary.text("ID do modelo para chat local:").ask()
        if model_id:
            run_cmd(model_id=model_id)

    elif choice == "Chat":
        engine_path = _select_engine_path("Selecione o engine para chat:")
        if engine_path:
            chat_cmd(engine_path=engine_path)

    elif choice == "Login":
        token = questionary.password("HuggingFace Token:").ask()
        if token:
            login_cmd(token=token)

    elif choice == "List":
        list_engines_cmd()

    elif choice == "Delete":
        engine_path = _select_engine_path("Selecione o engine para remover:")
        if engine_path:
            delete_cmd(engine_path=engine_path)

    elif choice == "Doctor":
        doctor_cmd()

    elif choice == "Sair":
        raise typer.Exit()
