from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rtxmodelforge.shared.build_planner import (
    EngineMode,
    ModelArchParams,
    _bytes_per_model_param,
    _kv_cache_gb_per_token,
    _snap_to_multiple,
)
from rtxmodelforge.shared.gpu_profiler import GPUProfile, theoretical_max_tps
from rtxmodelforge.shared.types import Quantization

# Se outro app esta usando mais que este threshold de VRAM, emite aviso
_VRAM_RESERVED_WARNING_GB: float = 0.5

# Tokens por bloco do KV cache — max_attention_window deve ser multiplo disso
_KV_TOKENS_PER_BLOCK: int = 32

# Minimo seguro de janela de atencao
_MIN_ATTENTION_WINDOW: int = 512


@dataclass
class RuntimePlan:
    """Plano de runtime calculado no startup baseado na VRAM disponivel no momento."""

    max_attention_window: int
    vram_budget_gb: float  # VRAM disponivel para KV cache
    theoretical_max_tps: float  # tok/s teorico do hardware para este modelo
    vram_warning: Optional[str]  # aviso se outros apps estao usando VRAM
    mode: EngineMode
    max_batch_size: int
    vram_total_gb: float
    vram_free_gb: float
    vram_reserved_gb: float
    gpu_name: str
    model_id: str
    quantization: str
    kv_cache_gb: float  # VRAM estimada para KV com janela calculada
    kv_cache_fraction: float = field(
        default=0.9
    )  # fracao da VRAM livre para KV cache (trtllm-serve)


def plan_runtime(
    profile: GPUProfile,
    model_id: str,
    quantization_str: str,
    params_b: float,
    engine_mode: str,
    max_batch_size: int,
    engine_size_gb: float,
    arch: Optional[ModelArchParams] = None,
) -> RuntimePlan:
    """
    Calcula o plano de runtime baseado na VRAM disponivel no momento do startup.

    Args:
        profile: Perfil GPU atual (VRAM lida agora)
        model_id: ID do modelo (para display)
        quantization_str: String da quantizacao (ex: "fp8")
        params_b: Tamanho do modelo em bilhoes de params
        engine_mode: "chat" ou "serve"
        max_batch_size: max_batch_size com que o engine foi compilado
        engine_size_gb: Tamanho do engine em disco (proxy para VRAM do engine)
        arch: Parametros de arquitetura do modelo (opcional)

    Returns:
        RuntimePlan com janela de atencao e metricas
    """
    try:
        quant = Quantization(quantization_str)
    except ValueError:
        quant = Quantization.FP8

    bytes_per_param = _bytes_per_model_param(quant)

    # VRAM disponivel para KV cache = livre agora - overhead TRT-LLM runtime
    # O engine ja esta carregado (ou prestes a ser), entao free_gb reflete isso
    overhead_gb = 0.3  # buffers de ativacao e workspace runtime
    available_for_kv = max(0.2, profile.vram_free_gb - engine_size_gb - overhead_gb)

    # Fallback de arquitetura
    if arch is None:
        from rtxmodelforge.shared.build_planner import _default_arch_for_params

        arch = _default_arch_for_params(params_b)

    kv_per_token_gb = _kv_cache_gb_per_token(arch, quant)
    if kv_per_token_gb <= 0:
        kv_per_token_gb = 1e-5

    # Janela de atencao: tokens que cabem na VRAM disponivel (por sequencia)
    # Para batch=1: todos os tokens sao de uma sequencia
    # Para batch>1: divisao igual entre sequencias
    tokens_per_seq = int(available_for_kv / (kv_per_token_gb * max_batch_size))

    # Limita pelo max do modelo
    tokens_per_seq = min(tokens_per_seq, arch.max_position_embeddings)

    # Snap para multiplo de _KV_TOKENS_PER_BLOCK
    attention_window = _snap_to_multiple(tokens_per_seq, _KV_TOKENS_PER_BLOCK)
    attention_window = max(attention_window, _MIN_ATTENTION_WINDOW)

    kv_cache_gb = kv_per_token_gb * max_batch_size * attention_window

    # Throughput teorico
    tps = theoretical_max_tps(profile, params_b, bytes_per_param)

    # Aviso de VRAM reservada por outros apps
    vram_warning: Optional[str] = None
    if profile.vram_reserved_gb > _VRAM_RESERVED_WARNING_GB:
        vram_warning = (
            f"{profile.vram_reserved_gb:.1f} GB de VRAM em uso por outros apps. "
            "Feche-os para maximizar performance."
        )

    # Fracao da VRAM livre para KV cache (usado pelo trtllm-serve)
    kv_cache_fraction = (
        min(0.95, available_for_kv / profile.vram_free_gb) if profile.vram_free_gb > 0 else 0.85
    )

    mode = EngineMode.SERVE if engine_mode == "serve" else EngineMode.CHAT

    return RuntimePlan(
        max_attention_window=attention_window,
        vram_budget_gb=available_for_kv,
        theoretical_max_tps=tps,
        vram_warning=vram_warning,
        mode=mode,
        max_batch_size=max_batch_size,
        vram_total_gb=profile.vram_total_gb,
        vram_free_gb=profile.vram_free_gb,
        vram_reserved_gb=profile.vram_reserved_gb,
        gpu_name=profile.name,
        model_id=model_id,
        quantization=quantization_str.upper(),
        kv_cache_gb=kv_cache_gb,
        kv_cache_fraction=kv_cache_fraction,
    )


def format_efficiency(actual_tps: float, theoretical_tps: float) -> str:
    """Formata a eficiencia relativa ao maximo teorico para display."""
    if theoretical_tps <= 0:
        return ""
    pct = min(100.0, (actual_tps / theoretical_tps) * 100)
    if pct >= 80:
        color = "green"
    elif pct >= 50:
        color = "yellow"
    else:
        color = "red"
    return f"[{color}]{pct:.0f}% do teórico[/{color}]"
