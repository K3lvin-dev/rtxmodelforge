from __future__ import annotations

import time
from io import StringIO
from pathlib import Path

from rich.live import Live

from rtxmodelforge.features.build.types import BuildConfig, CompilationError
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.types import Quantization


def build_engine(config: BuildConfig, engine_dir: Path) -> Path:
    """Orquestra a compilação do engine via LLM API."""
    try:
        from tensorrt_llm._tensorrt_engine import LLM  # pyright: ignore[reportMissingImports]
        from tensorrt_llm.llmapi import (
            KvCacheConfig,
            QuantAlgo,
            QuantConfig,
        )  # pyright: ignore[reportMissingImports]
    except ImportError:
        raise CompilationError(
            "TensorRT-LLM não encontrado. Verifique a instalação com 'rtxforge doctor'."
        ) from None

    # Mapeamento de quantização
    _ALGO_MAP = {
        Quantization.FP8: QuantAlgo.FP8,
        Quantization.INT8: QuantAlgo.INT8,
        Quantization.INT4_AWQ: QuantAlgo.W4A16_AWQ,
        Quantization.FP4: QuantAlgo.NVFP4,
    }

    quant_algo = _ALGO_MAP.get(config.quantization)
    if not quant_algo:
        raise CompilationError(
            f"Quantização '{config.quantization}' não suportada pelo TensorRT-LLM."
        )

    quant_config = QuantConfig(quant_algo=quant_algo)

    # FP8 beneficia de quantização do KV Cache também
    if config.quantization == Quantization.FP8:
        quant_config.kv_cache_quant_algo = QuantAlgo.FP8

    console.print(
        "\n[bold yellow]⚠ Compilação iniciada.[/bold yellow] Isto levará entre 10 e 30 minutos."
    )
    console.print("[dim]O terminal exibirá o tempo decorrido. Não feche este processo.[/dim]\n")

    start_time = time.time()

    try:
        with Live(console=console, refresh_per_second=1) as live:
            # TODO: Em um ambiente real, o processamento do LLM() acontece aqui.
            # O desafio é capturar o stdout do TensorRT-LLM que é C++ (extensão)
            # Para o v1, mostraremos o tempo decorrido.

            def update_live():
                elapsed = time.time() - start_time
                mins, secs = divmod(int(elapsed), 60)
                timer = f"{mins}m {secs}s"
                live.update(
                    f"⠸ [bold cyan]Compilando engine[/bold cyan]  [[tempo decorrido: {timer}]]"
                )

            # Instancia o LLM e compila
            # tensor_parallel_size=1 fixo para v1
            # During build, the compiler workspace + runtime buffers consume most
            # VRAM. A minimal max_attention_window allows the executor to init
            # without OOM — it does NOT affect the saved engine's max context.
            build_kv_cache_config = KvCacheConfig(max_attention_window=[512])

            llm = LLM(
                model=str(config.weights_dir),
                quant_config=quant_config,
                tensor_parallel_size=1,
                kv_cache_config=build_kv_cache_config,
            )

            update_live()

            # Persiste no disco
            llm.save(str(engine_dir))

            # Shutdown limpo
            llm.shutdown()

        return engine_dir

    except Exception as e:
        raise CompilationError(f"Erro interno do TensorRT-LLM: {str(e)}") from None
