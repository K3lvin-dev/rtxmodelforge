from __future__ import annotations

from typing import Any

from rich import box
from rich.panel import Panel

from rtxmodelforge import __version__
from rtxmodelforge.shared.gpu_profiler import profile_gpu


def build_splash_data() -> dict[str, Any]:
    """Coleta dados dinâmicos para o splash (GPU, engines). Nunca levanta exceção.

    Usa profile_gpu() cacheado (Phase 1) e count rápido de diretórios de engine
    em vez de list_engines() completo para evitar I/O desnecessário no startup.
    """
    try:
        gpu = profile_gpu()
        gpu_name = gpu.name if gpu else None
        vram_gb = gpu.vram_total_gb if gpu else None
    except Exception:
        gpu_name = None
        vram_gb = None

    try:
        from rtxmodelforge.shared import config as shared_config
        settings = shared_config.get_settings()
        # Contagem rápida: conta diretórios de engine (cada engine tem engine.json)
        # sem fazer parse de todos os metadados — muito mais rápido que list_engines()
        engine_count = sum(
            1 for _ in settings.engines_dir.rglob("engine.json")
            if _.is_file()
        )
    except Exception:
        engine_count = 0

    return {"gpu_name": gpu_name, "vram_gb": vram_gb, "engine_count": engine_count}


def render_splash() -> Panel:
    """Renderiza o splash screen como Rich Panel."""
    data = build_splash_data()

    if data["gpu_name"] and data["vram_gb"] is not None:
        gpu_line = f"  GPU:      {data['gpu_name']}  ·  {data['vram_gb']:.0f} GB VRAM"
    else:
        gpu_line = "  GPU:      nao detectada"

    engine_word = "compilado" if data["engine_count"] == 1 else "compilados"
    engines_line = f"  Engines:  {data['engine_count']} {engine_word}"

    content = (
        f"[bold blue]RTX Model Forge[/bold blue]  [dim]v{__version__}[/dim]\n"
        f"  [dim]Compile e rode LLMs otimizados com TensorRT[/dim]\n"
        f"\n"
        f"{gpu_line}\n"
        f"{engines_line}"
    )

    return Panel(content, box=box.ROUNDED, expand=False)
