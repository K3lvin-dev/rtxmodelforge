from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from rtxmodelforge.shared import config, gpu


@dataclass
class CheckResult:
    label: str
    passed: bool
    detail: str
    blocking: bool = True


def check_nvidia_driver() -> CheckResult:
    """Verifica versão do driver NVIDIA."""
    gpu_info = gpu.detect_gpu()
    if not gpu_info:
        return CheckResult("Driver NVIDIA", False, "Nenhuma GPU detectada.")

    # Exemplo simplificado de check de versão (v1 requer driver recente)
    # Ubuntu 24.04 + CUDA 13.1 geralmente > 560
    try:
        major_version = int(gpu_info.driver_version.split(".")[0])
        passed = major_version >= 525  # Mínimo absoluto para TRT-LLM decente
        return CheckResult(
            "Driver NVIDIA", passed, f"Versão {gpu_info.driver_version} (Mínimo: 525.x)"
        )
    except (ValueError, IndexError):
        return CheckResult("Driver NVIDIA", False, "Não foi possível verificar versão.")


def check_cuda_toolkit() -> CheckResult:
    """Verifica nvcc e versão do CUDA."""
    nvcc = shutil.which("nvcc")
    if not nvcc:
        return CheckResult("CUDA Toolkit (nvcc)", False, "nvcc não encontrado no PATH.")

    try:
        output = subprocess.check_output([nvcc, "--version"], encoding="utf-8")
        # "release 13.1, V13.1.xxx"
        if "release" in output:
            version_str = output.split("release ")[1].split(",")[0]
            major = int(version_str.split(".")[0])
            passed = major >= 12  # TRT-LLM v0.17 requer CUDA 12.x+
            return CheckResult("CUDA Toolkit", passed, f"Versão {version_str}")
    except (subprocess.SubprocessError, ValueError, IndexError):
        pass
    return CheckResult("CUDA Toolkit", False, "Falha ao ler versão do CUDA.")


def check_libopenmpi() -> CheckResult:
    """Verifica libopenmpi-dev (necessário para TRT-LLM multi-gpu/tp)."""
    # Em sistemas baseados em Debian:
    dpkg = shutil.which("dpkg")
    if not dpkg:
        return CheckResult("OpenMPI", True, "dpkg não encontrado, ignorando check.", blocking=False)

    try:
        subprocess.check_call(
            ["dpkg", "-s", "libopenmpi-dev"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return CheckResult("OpenMPI (libopenmpi-dev)", True, "Instalado.")
    except subprocess.CalledProcessError:
        return CheckResult("OpenMPI (libopenmpi-dev)", False, "sudo apt-get install libopenmpi-dev")


def check_gpu() -> CheckResult:
    """Verifica presença da GPU e SM version."""
    gpu_info = gpu.detect_gpu()
    if not gpu_info:
        return CheckResult(
            "GPU NVIDIA", False, "Nenhuma GPU NVIDIA detectada ou nvidia-smi falhou."
        )

    detail = f"{gpu_info.name} (SM{gpu_info.sm_version}, {gpu_info.vram_free_gb:.1f}GB livres)"

    # Check extra para multi-gpu (apenas aviso informativo no v1)
    try:
        import pynvml  # pyright: ignore[reportMissingImports]

        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        if count > 1:
            detail += f" | Multi-GPU detectado ({count} GPUs). V1 usa apenas GPU 0."
        pynvml.nvmlShutdown()
    except Exception:
        pass

    return CheckResult("GPU NVIDIA", True, detail)

def check_sm_support() -> CheckResult:
    """Verifica se a SM version é >= 80 (Ampere+)."""
    gpu_info = gpu.detect_gpu()
    if not gpu_info:
        return CheckResult("Suporte de Arquitetura", False, "Dependente da detecção de GPU.")

    passed = gpu_info.sm_version >= 80
    if not passed:
        return CheckResult(
            "Suporte de Arquitetura",
            False,
            f"SM{gpu_info.sm_version} não suportada. RTX série 20 e anteriores não compatíveis.",
        )
    return CheckResult("Suporte de Arquitetura", True, f"SM{gpu_info.sm_version} suportada.")


def check_trtllm() -> CheckResult:
    """Verifica instalação do tensorrt_llm."""
    try:
        import tensorrt_llm  # pyright: ignore[reportMissingImports]

        return CheckResult("TensorRT-LLM", True, f"Versão {tensorrt_llm.__version__}", blocking=False)

    except ImportError:
        return CheckResult("TensorRT-LLM", False, "Pacote 'tensorrt_llm' não instalado.")


def check_hf_token() -> CheckResult:
    """Verifica se o token do HuggingFace está configurado."""
    settings = config.get_settings()
    if settings.hf_token:
        # Mostra apenas os 4 primeiros caracteres por segurança
        masked = f"{settings.hf_token[:4]}..."
        return CheckResult("HuggingFace Token", True, f"Configurado ({masked})", blocking=False)
    return CheckResult(
        "HuggingFace Token", False, "Não configurado. Use 'rtxforge login'", blocking=False
    )
