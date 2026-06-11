from __future__ import annotations

from typing import Optional

from rtxmodelforge.shared.gpu_profiler import GPUProfile, profile_gpu


def detect_gpu() -> Optional[GPUProfile]:
    """Retorna o perfil canônico da GPU detectada."""
    return profile_gpu()
