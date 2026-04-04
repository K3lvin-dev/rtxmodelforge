from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rtxmodelforge.shared.build_planner import EngineMode
from rtxmodelforge.shared.gpu_profiler import GPUProfile
from rtxmodelforge.shared.types import QualityLabel, Quantization


@dataclass
class BuildConfig:
    model_id: str
    weights_dir: Path
    gpu_info: GPUProfile
    quantization: Quantization
    quality_label: QualityLabel
    rationale: str
    params_billions: float
    verbose: bool = False
    engine_mode: EngineMode = EngineMode.CHAT
    max_batch_size: int = 1
    max_seq_len: int = 4096
    enable_chunked_context: bool = True


class CompilationError(Exception):
    """Levantado quando o build do engine no TensorRT-LLM falha."""

    pass


class GatedModelError(Exception):
    """Levantado quando o modelo exige acesso autenticado via token."""

    pass
