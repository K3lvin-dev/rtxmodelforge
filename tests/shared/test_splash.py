from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rich.panel import Panel

from rtxmodelforge.shared.splash import build_splash_data, render_splash


class TestBuildSplashData:
    def test_with_gpu_detected(self):
        mock_gpu = MagicMock()
        mock_gpu.name = "NVIDIA GeForce RTX 4090"
        mock_gpu.vram_total_gb = 24.0

        with (
            patch("rtxmodelforge.shared.splash.profile_gpu", return_value=mock_gpu),
            patch("rtxmodelforge.shared.splash.list_engines", return_value=[("p1", None), ("p2", None)]),
        ):
            data = build_splash_data()

        assert data["gpu_name"] == "NVIDIA GeForce RTX 4090"
        assert data["vram_gb"] == 24.0
        assert data["engine_count"] == 2

    def test_without_gpu(self):
        with (
            patch("rtxmodelforge.shared.splash.profile_gpu", return_value=None),
            patch("rtxmodelforge.shared.splash.list_engines", return_value=[]),
        ):
            data = build_splash_data()

        assert data["gpu_name"] is None
        assert data["engine_count"] == 0

    def test_gpu_error_falls_back_to_none(self):
        with (
            patch("rtxmodelforge.shared.splash.profile_gpu", side_effect=Exception("nvml error")),
            patch("rtxmodelforge.shared.splash.list_engines", return_value=[]),
        ):
            data = build_splash_data()

        assert data["gpu_name"] is None


class TestRenderSplash:
    def test_returns_panel(self):
        mock_gpu = MagicMock()
        mock_gpu.name = "RTX 3090"
        mock_gpu.vram_total_gb = 24.0

        with (
            patch("rtxmodelforge.shared.splash.profile_gpu", return_value=mock_gpu),
            patch("rtxmodelforge.shared.splash.list_engines", return_value=[]),
        ):
            panel = render_splash()

        assert isinstance(panel, Panel)

    def test_no_gpu_does_not_raise(self):
        with (
            patch("rtxmodelforge.shared.splash.profile_gpu", return_value=None),
            patch("rtxmodelforge.shared.splash.list_engines", return_value=[]),
        ):
            panel = render_splash()  # should not raise

        assert isinstance(panel, Panel)
