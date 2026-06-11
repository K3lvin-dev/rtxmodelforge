from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import pynvml

# Bandwidth de memória por GPU (GB/s). Fonte: especificações oficiais NVIDIA.
# Para GPUs fora da tabela, usamos estimativa via sm_count × clock × bus_width.
_BANDWIDTH_LOOKUP: dict[str, float] = {
    # RTX 50 series (Blackwell)
    "rtx 5090": 1792.0,
    "rtx 5080": 960.0,
    "rtx 5070 ti": 896.0,
    "rtx 5070": 672.0,
    "rtx 5060 ti": 448.0,
    "rtx 5060": 304.0,
    # RTX 40 series (Ada Lovelace)
    "rtx 4090": 1008.0,
    "rtx 4080 super": 736.0,
    "rtx 4080": 717.0,
    "rtx 4070 ti super": 672.0,
    "rtx 4070 ti": 504.0,
    "rtx 4070 super": 504.0,
    "rtx 4070": 504.0,
    "rtx 4060 ti": 288.0,
    "rtx 4060": 272.0,
    # RTX 30 series (Ampere)
    "rtx 3090 ti": 1008.0,
    "rtx 3090": 936.0,
    "rtx 3080 ti": 912.0,
    "rtx 3080 12gb": 912.0,
    "rtx 3080": 760.0,
    "rtx 3070 ti": 608.0,
    "rtx 3070": 448.0,
    "rtx 3060 ti": 448.0,
    "rtx 3060": 360.0,
    "rtx 3050": 224.0,
    # RTX 20 series (Turing) - SM 75, nao suportado pelo TRT-LLM mas listado para completude
    "rtx 2080 ti": 616.0,
    "rtx 2080 super": 496.0,
    "rtx 2080": 448.0,
    "rtx 2070 super": 448.0,
    "rtx 2070": 448.0,
    "rtx 2060 super": 448.0,
    "rtx 2060": 336.0,
}

# Bus width por GPU (bits) — para fallback de estimativa de bandwidth
_BUS_WIDTH_LOOKUP: dict[str, int] = {
    "rtx 5090": 512,
    "rtx 5080": 256,
    "rtx 5070 ti": 256,
    "rtx 5070": 192,
    "rtx 5060 ti": 128,
    "rtx 5060": 128,
    "rtx 4090": 384,
    "rtx 4080 super": 256,
    "rtx 4080": 256,
    "rtx 4070 ti super": 256,
    "rtx 4070 ti": 192,
    "rtx 4070 super": 192,
    "rtx 4070": 192,
    "rtx 4060 ti": 128,
    "rtx 4060": 128,
    "rtx 3090 ti": 384,
    "rtx 3090": 384,
    "rtx 3080 ti": 384,
    "rtx 3080 12gb": 384,
    "rtx 3080": 320,
    "rtx 3070 ti": 256,
    "rtx 3070": 256,
    "rtx 3060 ti": 256,
    "rtx 3060": 192,
    "rtx 3050": 128,
}


@dataclass(frozen=True)
class GPUProfile:
    """Perfil completo da GPU com dados de performance para otimizacao de build e runtime."""

    name: str
    sm_version: int
    vram_total_gb: float
    vram_free_gb: float
    driver_version: str
    # dados de performance
    memory_bandwidth_gbs: float
    sm_count: int
    tensor_core_gen: int  # 3 = Ampere, 4 = Ada, 5 = Blackwell
    max_clock_mhz: int
    vram_reserved_gb: float  # total - free (apps em uso no momento)
    bandwidth_from_lookup: bool  # True = lookup table, False = estimativa


def _lookup_bandwidth(name: str) -> Optional[float]:
    """Busca bandwidth na tabela por substring do nome da GPU (case-insensitive)."""
    name_lower = name.lower()
    # Busca mais especifica primeiro (nomes mais longos tem prioridade)
    candidates = sorted(_BANDWIDTH_LOOKUP.keys(), key=len, reverse=True)
    for key in candidates:
        if key in name_lower:
            return _BANDWIDTH_LOOKUP[key]
    return None


def _lookup_bus_width(name: str) -> int:
    """Retorna bus width em bits para estimativa de bandwidth."""
    name_lower = name.lower()
    candidates = sorted(_BUS_WIDTH_LOOKUP.keys(), key=len, reverse=True)
    for key in candidates:
        if key in name_lower:
            return _BUS_WIDTH_LOOKUP[key]
    return 128  # fallback conservador


def _estimate_bandwidth(sm_count: int, max_clock_mhz: int, bus_width_bits: int) -> float:
    """Estima bandwidth de memoria: clock * bus_width * 2 (DDR) / 8 (bits->bytes) / 1000 (MB->GB)."""
    # max_clock_mhz aqui e o clock de memoria, mas pynvml retorna clock do SM
    # Usamos uma heuristica: clock_mem ~= clock_sm * 1.5 para GPUs RTX modernas
    estimated_mem_clock_mhz = max_clock_mhz * 1.5
    bandwidth_gbs = (estimated_mem_clock_mhz * bus_width_bits * 2) / (8 * 1000)
    return round(bandwidth_gbs, 1)


def _tensor_core_gen(sm_version: int) -> int:
    """Determina geracao dos Tensor Cores baseada na versao SM."""
    if sm_version >= 100:
        return 5  # Blackwell
    elif sm_version >= 89:
        return 4  # Ada Lovelace
    elif sm_version >= 80:
        return 3  # Ampere
    else:
        return 2  # Turing (nao suportado, mas mapeado)


# Cache em memória para profile_gpu: evita chamar NVML init/shutdown múltiplas vezes
# no mesmo fluxo de execução (ex: splash + serve + plan_runtime).
# TTL curto (3s) pois VRAM livre muda frequentemente; o importante é evitar
# n+1 chamadas no mesmo comando.
_cached_profile: Optional[GPUProfile] = None
_cached_profile_ts: float = 0.0
_PROFILE_CACHE_TTL: float = 3.0


def profile_gpu() -> Optional[GPUProfile]:
    """
    Detecta a GPU index 0 e retorna perfil completo com dados de performance.
    Usa pynvml como fonte principal, com fallbacks para cada campo.

    Mantém cache em memória com TTL de {_PROFILE_CACHE_TTL}s para evitar
    chamadas repetidas ao NVML no mesmo fluxo de comando.
    """
    global _cached_profile, _cached_profile_ts
    now = time.monotonic()
    if _cached_profile is not None and now - _cached_profile_ts < _PROFILE_CACHE_TTL:
        return _cached_profile

    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")

        major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
        sm_version = major * 10 + minor

        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_total_gb = float(mem.total) / 1e9
        vram_free_gb = float(mem.free) / 1e9
        vram_reserved_gb = vram_total_gb - vram_free_gb

        driver = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver, bytes):
            driver = driver.decode("utf-8")

        # SM count
        try:
            sm_count = pynvml.nvmlDeviceGetNumGpuCores(handle)
        except (pynvml.NVMLError, AttributeError):
            sm_count = _estimate_sm_count(sm_version, name)

        # Max clock (SM/graphics clock em MHz)
        try:
            max_clock_mhz = pynvml.nvmlDeviceGetMaxClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
        except (pynvml.NVMLError, AttributeError):
            max_clock_mhz = 2000  # fallback conservador

        # Bandwidth de memoria
        bw_from_lookup = True
        bandwidth = _lookup_bandwidth(name)
        if bandwidth is None:
            bw_from_lookup = False
            bus_width = _lookup_bus_width(name)
            bandwidth = _estimate_bandwidth(sm_count, max_clock_mhz, bus_width)

        pynvml.nvmlShutdown()

        result = GPUProfile(
            name=name,
            sm_version=sm_version,
            vram_total_gb=vram_total_gb,
            vram_free_gb=vram_free_gb,
            driver_version=driver,
            memory_bandwidth_gbs=bandwidth,
            sm_count=sm_count,
            tensor_core_gen=_tensor_core_gen(sm_version),
            max_clock_mhz=max_clock_mhz,
            vram_reserved_gb=vram_reserved_gb,
            bandwidth_from_lookup=bw_from_lookup,
        )
        _cached_profile = result
        _cached_profile_ts = time.monotonic()
        return result

    except pynvml.NVMLError:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
        result = _profile_gpu_via_smi()
        if result is not None:
            _cached_profile = result
            _cached_profile_ts = time.monotonic()
        return result


def _estimate_sm_count(sm_version: int, name: str) -> int:
    """Heuristica para SM count quando pynvml nao disponibiliza nvmlDeviceGetNumGpuCores."""
    name_lower = name.lower()
    # Valores tipicos por classe de GPU
    if "4090" in name_lower:
        return 128
    elif "4080" in name_lower:
        return 76
    elif "4070 ti" in name_lower:
        return 60
    elif "4070" in name_lower:
        return 46
    elif "4060 ti" in name_lower:
        return 34
    elif "4060" in name_lower:
        return 24
    elif "3090" in name_lower:
        return 82
    elif "3080" in name_lower:
        return 68
    elif "3070" in name_lower:
        return 46
    elif "3060" in name_lower:
        return 28
    # Fallback por geracao SM
    if sm_version >= 89:
        return 48
    elif sm_version >= 80:
        return 46
    return 32


def _profile_gpu_via_smi() -> Optional[GPUProfile]:
    """Fallback via subprocess nvidia-smi quando pynvml falha."""
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,compute_cap,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits",
        ]
        output = subprocess.check_output(cmd, encoding="utf-8").strip()
        if not output:
            return None

        parts = [p.strip() for p in output.split(",")]
        major_minor = parts[1].split(".")
        sm_version = int(major_minor[0]) * 10 + int(major_minor[1])

        name = parts[0]
        vram_total_gb = float(parts[2]) / 1024.0
        vram_free_gb = float(parts[3]) / 1024.0
        vram_reserved_gb = vram_total_gb - vram_free_gb

        sm_count = _estimate_sm_count(sm_version, name)

        bw_from_lookup = True
        bandwidth = _lookup_bandwidth(name)
        if bandwidth is None:
            bw_from_lookup = False
            bus_width = _lookup_bus_width(name)
            bandwidth = _estimate_bandwidth(sm_count, 2000, bus_width)

        return GPUProfile(
            name=name,
            sm_version=sm_version,
            vram_total_gb=vram_total_gb,
            vram_free_gb=vram_free_gb,
            driver_version=parts[4],
            memory_bandwidth_gbs=bandwidth,
            sm_count=sm_count,
            tensor_core_gen=_tensor_core_gen(sm_version),
            max_clock_mhz=2000,
            vram_reserved_gb=vram_reserved_gb,
            bandwidth_from_lookup=bw_from_lookup,
        )
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, IndexError):
        return None


def theoretical_max_tps(profile: GPUProfile, params_b: float, bytes_per_param: float) -> float:
    """
    Throughput teorico maximo (memory-bound, batch=1).
    Formula: bandwidth_GB_s / model_size_GB
    Ref: https://horace.io/brrr_intro.html
    """
    model_size_gb = params_b * bytes_per_param
    if model_size_gb <= 0:
        return 0.0
    return profile.memory_bandwidth_gbs / model_size_gb
