from __future__ import annotations

from typing import Any

from rich import box
from rich.panel import Panel

from rtxmodelforge import __version__
from rtxmodelforge.features.engines.store import list_engines
from rtxmodelforge.shared.gpu_profiler import profile_gpu


def build_splash_data() -> dict[str, Any]:
    """Coleta dados dinâmicos para o splash (GPU, engines). Nunca levanta exceção."""
    try:
        gpu = profile_gpu()
        gpu_name = gpu.name if gpu else None
        vram_gb = gpu.vram_total_gb if gpu else None
    except Exception:
        gpu_name = None
        vram_gb = None

    try:
        engine_count = len(list_engines())
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
