from __future__ import annotations

import time
from pathlib import Path

from rich.live import Live

from rtxmodelforge.features.build.types import BuildConfig, CompilationError
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.types import Quantization


def build_engine(config: BuildConfig, engine_dir: Path) -> Path:
    """Orquestra a compilação do engine via LLM API com parâmetros otimizados para a GPU."""
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

    if config.quantization == Quantization.FP8:
        quant_config.kv_cache_quant_algo = QuantAlgo.FP8

    console.print(
        f"\n[bold yellow]⚠ Compilação iniciada ({config.engine_mode.value.upper()} engine)."
        "[/bold yellow] Isto levará entre 10 e 30 minutos."
    )
    console.print(
        f"  [dim]max_batch_size={config.max_batch_size} "
        f"max_seq_len={config.max_seq_len} "
        f"chunked_context={config.enable_chunked_context}[/dim]"
    )
    console.print("[dim]O terminal exibirá o tempo decorrido. Não feche este processo.[/dim]\n")

    start_time = time.time()

    try:
        with Live(console=console, refresh_per_second=1) as live:
            def update_live():
                elapsed = time.time() - start_time
                mins, secs = divmod(int(elapsed), 60)
                timer = f"{mins}m {secs}s"
                live.update(
                    f"⠸ [bold cyan]Compilando engine "
                    f"({config.engine_mode.value})[/bold cyan]  "
                    f"[[tempo decorrido: {timer}]]"
                )

            # Janela mínima durante o build para evitar OOM no workspace do compilador.
            # Não afeta o engine salvo — o runtime usa max_attention_window separadamente.
            build_kv_cache_config = KvCacheConfig(
                max_attention_window=[config.max_seq_len]
            )

            llm = LLM(
                model=str(config.weights_dir),
                quant_config=quant_config,
                tensor_parallel_size=1,
                kv_cache_config=build_kv_cache_config,
                max_batch_size=config.max_batch_size,
                max_seq_len=config.max_seq_len,
            )

            update_live()

            llm.save(str(engine_dir))
            llm.shutdown()

        return engine_dir

    except Exception as e:
        raise CompilationError(f"Erro interno do TensorRT-LLM: {str(e)}") from None
