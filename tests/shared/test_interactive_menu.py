from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import typer

from rtxmodelforge.shared.interactive_menu import run_interactive_menu


class TestRunInteractiveMenu:
    def _mock_engine(self, path_str: str, model_id: str) -> tuple:
        meta = MagicMock()
        meta.model_id = model_id
        return (Path(path_str), meta)

    def test_list_dispatches_list_engines(self):
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
            patch("rtxmodelforge.shared.interactive_menu.list_engines_cmd") as mock_list,
        ):
            mock_q.select.return_value.ask.return_value = "List"
            run_interactive_menu()

        mock_list.assert_called_once()

    def test_doctor_dispatches_doctor(self):
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
            patch("rtxmodelforge.shared.interactive_menu.doctor_cmd") as mock_doctor,
        ):
            mock_q.select.return_value.ask.return_value = "Doctor"
            run_interactive_menu()

        mock_doctor.assert_called_once()

    def test_sair_raises_exit(self):
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
        ):
            mock_q.select.return_value.ask.return_value = "Sair"
            with pytest.raises(typer.Exit):
                run_interactive_menu()

    def test_build_collects_model_id_and_dispatches(self):
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
            patch("rtxmodelforge.shared.interactive_menu.build_cmd") as mock_build,
        ):
            mock_q.select.return_value.ask.return_value = "Build"
            mock_q.text.return_value.ask.return_value = "meta-llama/Llama-3.1-8B"
            run_interactive_menu()

        mock_build.assert_called_once_with(model_id="meta-llama/Llama-3.1-8B", verbose=False)

    def test_login_collects_token_and_dispatches(self):
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
            patch("rtxmodelforge.shared.interactive_menu.login_cmd") as mock_login,
        ):
            mock_q.select.return_value.ask.return_value = "Login"
            mock_q.password.return_value.ask.return_value = "hf_abc123"
            run_interactive_menu()

        mock_login.assert_called_once_with(token="hf_abc123")

    def test_serve_with_engines_shows_select(self):
        fake_engines = [
            (Path("/engines/llama/fp8-serve"), MagicMock(model_id="meta-llama/Llama")),
        ]
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
            patch("rtxmodelforge.shared.interactive_menu.store") as mock_store,
            patch("rtxmodelforge.shared.interactive_menu.serve_cmd") as mock_serve,
        ):
            mock_store.list_engines.return_value = fake_engines
            # questionary.Choice retorna value canônico: primeiro "Serve", depois o path do engine
            mock_q.select.return_value.ask.side_effect = [
                "Serve",
                "/engines/llama/fp8-serve",
            ]
            run_interactive_menu()

        mock_serve.assert_called_once_with(engine_path=Path("/engines/llama/fp8-serve"))

    def test_chat_with_no_engines_falls_back_to_text(self):
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
            patch("rtxmodelforge.shared.interactive_menu.store") as mock_store,
            patch("rtxmodelforge.shared.interactive_menu.chat_cmd") as mock_chat,
        ):
            mock_store.list_engines.return_value = []
            mock_q.select.return_value.ask.return_value = "Chat"
            mock_q.text.return_value.ask.return_value = "/my/engine/path"
            run_interactive_menu()

        mock_chat.assert_called_once_with(engine_path=Path("/my/engine/path"))

    def test_none_answer_aborts_without_crash(self):
        """Usuário pressiona Ctrl+C em questionary retorna None — não deve crashar."""
        with (
            patch("rtxmodelforge.shared.interactive_menu.render_splash"),
            patch("rtxmodelforge.shared.interactive_menu.console"),
            patch("rtxmodelforge.shared.interactive_menu.questionary") as mock_q,
        ):
            mock_q.select.return_value.ask.return_value = None
            # should not raise
            run_interactive_menu()
