from __future__ import annotations

from datetime import datetime
from typing import Final, Optional

from pydantic import BaseModel, ConfigDict, Field

from rtxmodelforge.shared.build_planner import EngineMode
from rtxmodelforge.shared.capabilities import AccelerationClass, GPUArchitecture
from rtxmodelforge.shared.types import QualityLabel, Quantization

CURRENT_SCHEMA_VERSION: Final[int] = 3


class EngineMetadata(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    schema_version: int = CURRENT_SCHEMA_VERSION
    model_id: str
    gpu_model: str
    sm_version: int
    quantization: Quantization
    quality_label: QualityLabel
    quantization_rationale: str
    trtllm_version: str
    built_at: datetime = Field(default_factory=datetime.now)
    engine_path: str
    params_billions: float
    vram_used_gb: float
    engine_size_gb: float
    architecture: str  # Ex: "llama", "qwen2"
    max_seq_len: int = 4096
    # campos adicionados em schema v2
    engine_mode: EngineMode = EngineMode.CHAT
    max_batch_size: int = 1
    build_plan_summary: str = ""  # resumo legivel do BuildPlan para display
    target_precision: str = ""
    effective_precision: str = ""
    acceleration_class: Optional[AccelerationClass] = None
    target_architecture: Optional[GPUArchitecture] = None
    fallback_reason: str = ""
