from __future__ import annotations

import time
from pathlib import Path

from rtxmodelforge.features.build import downloader, engine_builder
from rtxmodelforge.features.build import types as build_types
from rtxmodelforge.features.engines import store
from rtxmodelforge.features.engines import types as engine_types
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.panels import stage_table
from rtxmodelforge.shared.types import StageResult, StageStatus


def run(config: build_types.BuildConfig) -> Path:
    """Executa o pipeline completo de build."""

    engine_dir = store.get_engine_dir(config.model_id, config.quantization)
    if (engine_dir / "engine.json").exists():
        console.print(
            f"\n[bold yellow]⚠ Engine já existe:[/bold yellow] {engine_dir}\n"
            "  Use [cyan]rtxforge list[/cyan] para ver engines compilados.\n"
            "  Use [cyan]rtxforge delete[/cyan] para remover e recompilar.\n"
        )
        return engine_dir

    stages = [
        StageResult("Baixando pesos do HuggingFace"),
        StageResult("Lendo configuração do modelo"),
        StageResult("Compilando engine (pode levar 10–30 min)"),
        StageResult("Salvando metadados e limpeza"),
    ]

    weights_dir = engine_dir / "weights"

    def update_display():
        console.clear()
        console.print(stage_table(stages))

    from rtxmodelforge.shared import config as shared_config
    settings = shared_config.get_settings()

    try:
        # Stage 1: Download
        stages[0].status = StageStatus.RUNNING
        update_display()
        start = time.time()
        downloader.download_weights(
            model_id=config.model_id,
            target_dir=engine_dir,
            hf_token=settings.hf_token,
            verbose=config.verbose,
        )
        stages[0].duration_s = time.time() - start
        stages[0].status = StageStatus.DONE

        # Stage 2: Read Params
        stages[1].status = StageStatus.RUNNING
        update_display()
        start = time.time()
        config.weights_dir = weights_dir
        config.params_billions = downloader.read_params_billions(weights_dir)
        stages[1].duration_s = time.time() - start
        stages[1].status = StageStatus.DONE

        # Stage 3: Build
        stages[2].status = StageStatus.RUNNING
        update_display()
        start = time.time()
        engine_builder.build_engine(config, engine_dir)
        stages[2].duration_s = time.time() - start
        stages[2].status = StageStatus.DONE

        # Stage 4: Metadata
        stages[3].status = StageStatus.RUNNING
        update_display()
        start = time.time()

        # Coleta versão do TRT-LLM para metadata
        trt_ver = "desconhecido"
        try:
            import tensorrt_llm  # pyright: ignore[reportMissingImports]

            trt_ver = tensorrt_llm.__version__
        except ImportError:
            pass

        metadata = engine_types.EngineMetadata(
            model_id=config.model_id,
            gpu_model=config.gpu_info.name,
            sm_version=config.gpu_info.sm_version,
            quantization=config.quantization,
            quality_label=config.quality_label,
            quantization_rationale=config.rationale,
            trtllm_version=trt_ver,
            engine_path=str(engine_dir),
            params_billions=config.params_billions,
            vram_used_gb=config.gpu_info.vram_total_gb
            - config.gpu_info.vram_free_gb,  # Estimativa real de uso
            engine_size_gb=store.get_dir_size_gb(engine_dir),
            architecture="desconhecida",  # TODO: Extrair do config.json se possível
        )
        store.save_metadata(engine_dir, metadata)

        stages[3].duration_s = time.time() - start
        stages[3].status = StageStatus.DONE
        update_display()

        return engine_dir

    except Exception as e:
        for stage in stages:
            if stage.status == StageStatus.RUNNING:
                stage.status = StageStatus.FAILED
        update_display()
        raise e
