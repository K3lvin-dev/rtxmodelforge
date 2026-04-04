from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from rtxmodelforge.shared.types import GPUInfo, Quantization, QualityLabel

@dataclass
class BuildConfig:
    model_id: str
    weights_dir: Path
    gpu_info: GPUInfo
    quantization: Quantization
    quality_label: QualityLabel
    rationale: str
    params_billions: float
    verbose: bool = False

class CompilationError(Exception):
    """Levantado quando o build do engine no TensorRT-LLM falha."""
    pass

class GatedModelError(Exception):
    """Levantado quando o modelo exige acesso autenticado via token."""
    pass
