from __future__ import annotations

import ctypes
import os
import sys
from typing import Optional


# ruff: noqa: E402, PLC2401
# Ensure the venv-bundled NVIDIA cuBLASLt is loaded instead of the system's.
# On systems with CUDA 13.2+ installed, the linker picks up libcublasLt from
# /usr/local/cuda-13.2 while PyTorch's handle was created with the bundled
# CUDA 13.0 library — causing CUBLAS_STATUS_NOT_INITIALIZED on F.linear+bias.
# Fix: pre-load the bundled cuBLASLt via ctypes with RTLD_GLOBAL before any
# CUDA-using library (PyTorch) initializes its context.
def _ensure_bundled_cuda_libs() -> None:
    if os.environ.get("_RTXFORGE_CUDA_LIBS_SET"):
        return
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    venv_site = os.path.join(
        os.path.dirname(os.path.dirname(sys.executable)), "lib", py_ver, "site-packages"
    )
    for cu_dir in ("nvidia/cu13/lib", "nvidia/cu12/lib"):
        lib_dir = os.path.join(venv_site, cu_dir)
        if os.path.isdir(lib_dir) and any(f.startswith("libcublasLt") for f in os.listdir(lib_dir)):
            cublas_path = os.path.join(lib_dir, "libcublasLt.so")
            if os.path.exists(cublas_path):
                # RTLD_NOLOAD: don't error if already loaded; RTLD_GLOBAL: make
                # symbols available to subsequently-loaded libraries (PyTorch).
                flags = os.RTLD_NOLOAD | os.RTLD_GLOBAL
                try:
                    ctypes.CDLL(cublas_path, flags)
                except OSError:
                    pass
    os.environ["_RTXFORGE_CUDA_LIBS_SET"] = "1"


_ensure_bundled_cuda_libs()

import typer
from typer import Context, Exit

from rtxmodelforge import __version__
from rtxmodelforge.features.build.command import build
from rtxmodelforge.features.chat.command import chat
from rtxmodelforge.features.doctor.command import doctor
from rtxmodelforge.features.engines.delete_command import delete
from rtxmodelforge.features.engines.list_command import list_engines
from rtxmodelforge.features.login.command import login
from rtxmodelforge.features.run.command import run
from rtxmodelforge.features.serve.command import serve
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.interactive_menu import run_interactive_menu

app = typer.Typer(
    name="rtxforge",
    help="CLI Tensor Core first para preparar e executar modelos locais com TensorRT-LLM em GPUs RTX.",
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"rtxforge {__version__}")
        raise Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: Context,
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True, help="Exibe a versão e sai."
    ),
) -> None:
    if ctx.invoked_subcommand is None:
        run_interactive_menu()
        raise Exit()


app.command(name="prepare")(build)
app.command(name="build", hidden=True)(build)
app.command()(serve)
app.command()(chat)
app.command()(run)
app.command()(login)
app.command()(doctor)
app.command(name="list")(list_engines)
app.command()(delete)

if __name__ == "__main__":
    app()
