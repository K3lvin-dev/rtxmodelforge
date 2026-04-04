from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

CURRENT_SCHEMA_VERSION: Final[int] = 2


class EngineMetadata(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    schema_version: int = CURRENT_SCHEMA_VERSION
    model_id: str
    gpu_model: str
    sm_version: int
    quantization: str  # "fp8" | "int8" | "int4_awq" | "fp4"
    quality_label: str  # "max-quality" | "balanced" | "max-speed"
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
    engine_mode: str = "chat"  # "chat" | "serve"
    max_batch_size: int = 1
    build_plan_summary: str = ""  # resumo legivel do BuildPlan para display
