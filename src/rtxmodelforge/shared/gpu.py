from __future__ import annotations

import subprocess
from typing import Optional

import pynvml

from rtxmodelforge.shared.types import GPUInfo


def detect_gpu() -> Optional[GPUInfo]:
    """Detecta a GPU index 0 via pynvml (preferencial) ou nvidia-smi (fallback)."""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        name = pynvml.nvmlDeviceGetName(handle)
        # pynvml retorna bytes em algumas versões
        if isinstance(name, bytes):
            name = name.decode("utf-8")

        major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
        sm_version = major * 10 + minor

        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        driver = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver, bytes):
            driver = driver.decode("utf-8")

        return GPUInfo(
            name=name,
            sm_version=sm_version,
            vram_total_gb=mem.total / 1e9,
            vram_free_gb=mem.free / 1e9,
            driver_version=driver,
        )
    except pynvml.NVMLError:
        return _detect_gpu_via_smi()
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


def _detect_gpu_via_smi() -> Optional[GPUInfo]:
    """Fallback via subprocess nvidia-smi."""
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
        # compute_cap é "8.9"
        major_minor = parts[1].split(".")
        sm_version = int(major_minor[0]) * 10 + int(major_minor[1])

        return GPUInfo(
            name=parts[0],
            sm_version=sm_version,
            vram_total_gb=float(parts[2])
            / 1024,  # nvidia-smi retorna MiB com nounits? Geralmente sim.
            vram_free_gb=float(parts[3]) / 1024,
            driver_version=parts[4],
        )
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, IndexError):
        return None
