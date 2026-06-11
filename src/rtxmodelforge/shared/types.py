from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Final, Optional

if TYPE_CHECKING:
    from rtxmodelforge.shared.gpu_profiler import GPUProfile

    GPUInfo = Optional[GPUProfile]
else:
    # Em runtime, usamos Any para evitar circular import
    # (gpu_profiler → capabilities → types)
    GPUInfo = Any


class Quantization(str, Enum):
    FP8 = "fp8"
    INT8 = "int8"
    INT4_AWQ = "int4_awq"
    FP4 = "fp4"


class QualityLabel(str, Enum):
    MAX_QUALITY = "max-quality"
    BALANCED = "balanced"
    MAX_SPEED = "max-speed"


QUANT_DISPLAY: Final[dict[Quantization, str]] = {
    Quantization.FP8: "FP8",
    Quantization.INT8: "INT8",
    Quantization.INT4_AWQ: "INT4 AWQ",
    Quantization.FP4: "FP4",
}


class StageStatus(str, Enum):
    PENDING = "—"
    RUNNING = "⠸"
    DONE = "✔"
    FAILED = "✘"


@dataclass
class StageResult:
    label: str
    status: StageStatus = StageStatus.PENDING
    duration_s: float = 0.0

    @property
    def duration_display(self) -> str:
        minutes, seconds = divmod(int(self.duration_s), 60)
        return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"


class UnsupportedGPUError(Exception):
    """Levantado quando a GPU não é suportada pelo TensorRT-LLM (SM < 80)."""

    pass


class InsufficientVRAMError(Exception):
    """Levantado quando nenhuma quantização cabe na VRAM disponível."""

    pass


def recommend_quantization(
    gpu: GPUInfo, params_billions: float
) -> tuple[Quantization, QualityLabel, str]:
    from rtxmodelforge.shared.capabilities import select_acceleration_mode

    if gpu is None:
        raise UnsupportedGPUError("Nenhuma GPU NVIDIA compatível detectada.")

    selection = select_acceleration_mode(gpu, params_billions)
    return selection.quantization, selection.quality_label, selection.rationale
