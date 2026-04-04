from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Final

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
    Quantization.FP8: "FP8 (Alta Qualidade/Velocidade)",
    Quantization.INT8: "INT8 (Equilibrado)",
    Quantization.INT4_AWQ: "INT4 AWQ (Alta Compressão)",
    Quantization.FP4: "FP4 (Máxima Velocidade - Blackwell)",
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

@dataclass(frozen=True)
class GPUInfo:
    name: str
    sm_version: int
    vram_total_gb: float
    vram_free_gb: float
    driver_version: str

class UnsupportedGPUError(Exception):
    """Levantado quando a GPU não é suportada pelo TensorRT-LLM (SM < 80)."""
    pass

class InsufficientVRAMError(Exception):
    """Levantado quando nenhuma quantização cabe na VRAM disponível."""
    pass

def vram_needed_gb(params_billions: float, quant: Quantization) -> float:
    """Estima a VRAM necessária: params * bytes_per_param * 1.3 (overhead)."""
    bytes_per_param = 1.0 if quant in (Quantization.FP8, Quantization.INT8) else 0.5
    return params_billions * bytes_per_param * 1.3

def recommend_quantization(gpu: GPUInfo, params_billions: float) -> tuple[Quantization, QualityLabel, str]:
    """
    Recomenda a melhor quantização baseada na SM version e VRAM livre.
    Implementa a cascata: Ampere -> INT8/INT4, Ada/Blackwell -> FP8/FP4.
    """
    if gpu.sm_version < 80:
        raise UnsupportedGPUError(
            f"GPU {gpu.name} (SM{gpu.sm_version}) não suportada. TensorRT-LLM requer SM80+ (Ampere+)."
        )

    # Blackwell (RTX 50) - SM >= 100
    if gpu.sm_version >= 100:
        if gpu.vram_free_gb >= vram_needed_gb(params_billions, Quantization.FP8):
            return Quantization.FP8, QualityLabel.MAX_QUALITY, "5ª geração Tensor Cores — máximo custo-benefício"
        if gpu.vram_free_gb >= vram_needed_gb(params_billions, Quantization.FP4):
            return Quantization.FP4, QualityLabel.MAX_SPEED, "NVFP4 nativo Blackwell — 2× FP8 throughput"

    # Ada Lovelace (RTX 40) - SM 89
    elif gpu.sm_version == 89:
        if gpu.vram_free_gb >= vram_needed_gb(params_billions, Quantization.FP8):
            return Quantization.FP8, QualityLabel.MAX_QUALITY, "4ª geração Tensor Cores — 2× INT8, ~99% qualidade"
        if gpu.vram_free_gb >= vram_needed_gb(params_billions, Quantization.INT8):
            return Quantization.INT8, QualityLabel.BALANCED, "FP8 não cabe na VRAM disponível"
        if gpu.vram_free_gb >= vram_needed_gb(params_billions, Quantization.INT4_AWQ):
            return Quantization.INT4_AWQ, QualityLabel.MAX_SPEED, "VRAM muito limitada, usando INT4 AWQ"

    # Ampere (RTX 30) - SM 80-88
    else:
        if gpu.vram_free_gb >= vram_needed_gb(params_billions, Quantization.INT8):
            return Quantization.INT8, QualityLabel.MAX_QUALITY, "Tensor Cores Ampere — melhor custo-benefício"
        if gpu.vram_free_gb >= vram_needed_gb(params_billions, Quantization.INT4_AWQ):
            return Quantization.INT4_AWQ, QualityLabel.MAX_SPEED, "VRAM insuficiente para INT8"

    raise InsufficientVRAMError(
        f"Modelo {params_billions:.1f}B params não cabe na {gpu.name} ({gpu.vram_free_gb:.1f}GB livres). "
        "Considere um modelo menor."
    )
