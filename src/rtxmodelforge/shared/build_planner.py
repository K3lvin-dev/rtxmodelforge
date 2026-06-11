from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from rtxmodelforge.shared.gpu_profiler import GPUProfile, theoretical_max_tps
from rtxmodelforge.shared.types import Quantization

logger = logging.getLogger(__name__)

# Tokens por bloco de KV cache do TRT-LLM (deve ser multiplo exato)
_KV_TOKENS_PER_BLOCK: int = 32

# Fracao da VRAM disponivel reservada para workspace e buffers TRT-LLM durante o build
_BUILD_OVERHEAD_GB: float = 0.8

# Minimo e maximo seguros de max_seq_len para compilacao
_MIN_SEQ_LEN: int = 2048
_MAX_SEQ_LEN: int = 131072

# Fator de seguranca: nao usar 100% da VRAM calculada (deixa margem para variacao)
_SAFETY_FACTOR: float = 0.85


class EngineMode(str, Enum):
    CHAT = "chat"
    SERVE = "serve"


@dataclass(frozen=True)
class ModelArchParams:
    """Parametros de arquitetura do modelo necessarios para calculo do KV cache."""

    num_layers: int
    num_kv_heads: int
    head_dim: int
    max_position_embeddings: int


@dataclass(frozen=True)
class BuildPlan:
    """Plano de compilacao calculado para uma GPU e modo especifico."""

    mode: EngineMode
    max_batch_size: int
    max_seq_len: int
    max_num_tokens: int  # max_batch_size * max_seq_len
    quantization: Quantization
    kv_cache_quant: bool  # True = FP8 KV cache (Ada/Blackwell)
    enable_chunked_context: bool
    build_kv_window: int  # max_attention_window para o build
    kv_cache_gb: float  # VRAM estimada para KV cache em runtime
    theoretical_max_tps: float  # tok/s teorico para este modo

    @property
    def summary(self) -> str:
        return (
            f"batch={self.max_batch_size} seq={self.max_seq_len} "
            f"kv={self.kv_cache_gb:.1f}GB ~{self.theoretical_max_tps:.0f}tok/s"
        )


def read_model_arch(weights_dir: Path) -> Optional[ModelArchParams]:
    """
    Le parametros de arquitetura do config.json para calcular KV cache.
    Suporta Llama, Mistral, Qwen2, Phi, Falcon e similares.
    """
    config_path = weights_dir / "config.json"
    if not config_path.exists():
        return None

    try:
        with config_path.open("r") as f:
            cfg = json.load(f)

        num_layers = cfg.get("num_hidden_layers") or cfg.get("n_layer")
        hidden_size = cfg.get("hidden_size") or cfg.get("n_embd")
        num_attn_heads = cfg.get("num_attention_heads") or cfg.get("n_head")
        num_kv_heads = cfg.get("num_key_value_heads") or num_attn_heads
        max_pos = (
            cfg.get("max_position_embeddings")
            or cfg.get("n_positions")
            or cfg.get("seq_length")
            or 4096
        )

        if not (num_layers and hidden_size and num_attn_heads):
            return None

        head_dim = hidden_size // num_attn_heads

        return ModelArchParams(
            num_layers=int(num_layers),
            num_kv_heads=int(num_kv_heads),
            head_dim=int(head_dim),
            max_position_embeddings=int(max_pos),
        )
    except Exception:
        logger.debug("Falha ao parsear config.json em %s", weights_dir, exc_info=True)
        return None


def _bytes_per_kv_param(quantization: Quantization) -> float:
    """Bytes por elemento do KV cache (FP8 = 1, FP16/BF16 = 2)."""
    if quantization in (Quantization.FP8, Quantization.INT8):
        return 1.0
    elif quantization == Quantization.FP4:
        return 0.5
    return 2.0  # FP16/BF16


def _kv_cache_gb_per_token(arch: ModelArchParams, quantization: Quantization) -> float:
    """
    VRAM consumida pelo KV cache por token (todos os layers).
    Formula: 2 (K+V) x num_kv_heads x head_dim x bytes_per_elem x num_layers
    """
    bytes_per_elem = _bytes_per_kv_param(quantization)
    bytes_per_token = 2 * arch.num_kv_heads * arch.head_dim * bytes_per_elem * arch.num_layers
    return bytes_per_token / 1e9


def _snap_to_multiple(value: int, multiple: int) -> int:
    """Arreda value para o multiplo de 'multiple' mais proximo (para baixo)."""
    return max(multiple, (value // multiple) * multiple)


def _practical_seq_len_cap(params_b: float) -> int:
    """
    Cap de contexto baseado no tamanho do modelo para performance otimizada.

    Modelos menores têm KV cache proporcionalmente mais barato, mas compilar
    e alocar para 32K quando o modelo tem 1.5B params gera overhead desnecessário.
    O cap é derivado da relação entre params_b e a janela de atenção prática:
    mais params → mais camadas/heads → KV cache cresce → contexto útil menor.

    Pode ser sobreposto pelo max_position_embeddings do modelo (via min() no chamador).
    """
    if params_b <= 2.0:
        return 8_192     # 1-2B: 8K mais que suficiente; overhead de 32K é 4× desnecessário
    elif params_b <= 4.0:
        return 16_384    # 3-4B: 16K equilibra contexto e latência de build
    elif params_b <= 8.0:
        return 32_768    # 5-8B: 32K razoável para modelos médios
    elif params_b <= 14.0:
        return 65_536    # 9-14B: 64K onde modelos tendem a precisar de contexto longo
    else:
        return 131_072   # 14B+: máximo — modelos grandes ganham com contexto amplo


def _bytes_per_model_param(quantization: Quantization) -> float:
    if quantization in (Quantization.FP8, Quantization.INT8):
        return 1.0
    elif quantization in (Quantization.INT4_AWQ, Quantization.FP4):
        return 0.5
    return 2.0


def _calc_max_seq_len(
    available_vram_gb: float,
    batch_size: int,
    arch: ModelArchParams,
    quantization: Quantization,
    params_b: float,
) -> int:
    """
    Calcula o max_seq_len que cabe na VRAM disponivel para o KV cache.
    O TRT-LLM aloca KV cache para max_batch_size * max_seq_len tokens no worst case.

    O resultado é limitado por três fatores em ordem de prioridade:
      1. VRAM disponível para KV cache (hardware constraint)
      2. max_position_embeddings do modelo (model constraint)
      3. Cap prático baseado em params_b (performance constraint)
    """
    kv_per_token_gb = _kv_cache_gb_per_token(arch, quantization)
    if kv_per_token_gb <= 0:
        return _MIN_SEQ_LEN

    # VRAM disponivel para KV cache apos aplicar fator de seguranca
    safe_vram_gb = available_vram_gb * _SAFETY_FACTOR

    # Tokens totais que cabem: vram / kv_per_token / batch_size
    # (batch_size sequencias em paralelo, cada uma com max_seq_len tokens)
    max_tokens_total = int(safe_vram_gb / kv_per_token_gb)
    max_seq = max_tokens_total // batch_size

    # Limita pelo max_position_embeddings do modelo (capacidade do modelo)
    max_seq = min(max_seq, arch.max_position_embeddings)
    # Limita pelo cap prático baseado no tamanho do modelo (performance)
    max_seq = min(max_seq, _practical_seq_len_cap(params_b))
    # Limita pelo teto absoluto e garante mínimo seguro
    max_seq = min(max_seq, _MAX_SEQ_LEN)
    max_seq = max(max_seq, _MIN_SEQ_LEN)

    # Snap para multiplo de 64 (alinhamento de blocos KV)
    return _snap_to_multiple(max_seq, 64)


def plan_build(
    profile: GPUProfile,
    params_b: float,
    quantization: Quantization,
    arch: Optional[ModelArchParams] = None,
) -> tuple[BuildPlan, BuildPlan]:
    """
    Calcula os BuildPlans otimais para modos chat e serve.

    Args:
        profile: Perfil da GPU (VRAM, bandwidth, etc.)
        params_b: Tamanho do modelo em bilhoes de parametros
        quantization: Tipo de quantizacao escolhido
        arch: Parametros de arquitetura do modelo (extraidos do config.json)
              Se None, usa valores conservadores baseados no modelo.

    Returns:
        Tupla (chat_plan, serve_plan)
    """
    bytes_per_param = _bytes_per_model_param(quantization)
    model_size_gb = params_b * bytes_per_param

    # VRAM disponivel apos carregar o modelo + overhead de build/runtime
    available_for_kv = max(0.5, profile.vram_free_gb - model_size_gb - _BUILD_OVERHEAD_GB)

    # Fallback de arquitetura: valores conservadores para modelos desconhecidos
    if arch is None:
        arch = _default_arch_for_params(params_b)

    kv_per_token_gb = _kv_cache_gb_per_token(arch, quantization)
    kv_cache_quant = quantization in (Quantization.FP8,)  # FP8 KV cache disponivel em Ada+
    enable_chunked = profile.sm_version >= 80  # Ampere+ suporta chunked context

    # --- Chat Plan (single user, maximiza seq_len) ---
    chat_batch = 1
    chat_seq = _calc_max_seq_len(available_for_kv, chat_batch, arch, quantization, params_b)
    chat_kv_gb = kv_per_token_gb * chat_batch * chat_seq
    chat_tps = theoretical_max_tps(profile, params_b, bytes_per_param)

    chat_plan = BuildPlan(
        mode=EngineMode.CHAT,
        max_batch_size=chat_batch,
        max_seq_len=chat_seq,
        max_num_tokens=chat_batch * chat_seq,
        quantization=quantization,
        kv_cache_quant=kv_cache_quant,
        enable_chunked_context=enable_chunked,
        build_kv_window=min(512, chat_seq),
        kv_cache_gb=chat_kv_gb,
        theoretical_max_tps=chat_tps,
    )

    # --- Serve Plan (multi-client, balanceia batch e seq_len) ---
    # Heuristica: batch = floor(available_vram / 0.5 GB), limitado a 2..16
    serve_batch = min(16, max(2, int(available_for_kv / 0.5)))
    serve_seq = _calc_max_seq_len(available_for_kv, serve_batch, arch, quantization, params_b)
    # Para serve, min seq_len e 2048 (conversas de API tendem a ser mais curtas)
    serve_seq = max(serve_seq, 2048)
    serve_kv_gb = kv_per_token_gb * serve_batch * serve_seq
    # Serve tem throughput menor por request mas maior throughput total
    serve_tps = chat_tps * 0.85  # overhead de batching reduz ligeiramente tok/s por request

    serve_plan = BuildPlan(
        mode=EngineMode.SERVE,
        max_batch_size=serve_batch,
        max_seq_len=serve_seq,
        max_num_tokens=serve_batch * serve_seq,
        quantization=quantization,
        kv_cache_quant=kv_cache_quant,
        enable_chunked_context=enable_chunked,
        build_kv_window=min(512, serve_seq),
        kv_cache_gb=serve_kv_gb,
        theoretical_max_tps=serve_tps,
    )

    return chat_plan, serve_plan


def _default_arch_for_params(params_b: float) -> ModelArchParams:
    """
    Parametros de arquitetura conservadores para modelos desconhecidos.
    Baseado em valores tipicos de modelos Llama/Qwen da faixa de tamanho.
    """
    if params_b <= 2.0:
        return ModelArchParams(
            num_layers=28, num_kv_heads=4, head_dim=64, max_position_embeddings=8192
        )
    elif params_b <= 4.0:
        return ModelArchParams(
            num_layers=32, num_kv_heads=8, head_dim=128, max_position_embeddings=8192
        )
    elif params_b <= 8.0:
        return ModelArchParams(
            num_layers=32, num_kv_heads=8, head_dim=128, max_position_embeddings=8192
        )
    elif params_b <= 14.0:
        return ModelArchParams(
            num_layers=40, num_kv_heads=8, head_dim=128, max_position_embeddings=16384
        )
    elif params_b <= 32.0:
        return ModelArchParams(
            num_layers=64, num_kv_heads=8, head_dim=128, max_position_embeddings=32768
        )
    else:
        return ModelArchParams(
            num_layers=80, num_kv_heads=8, head_dim=128, max_position_embeddings=32768
        )
