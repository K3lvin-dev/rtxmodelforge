from __future__ import annotations

import time
from pathlib import Path

from rtxmodelforge.features.build import downloader, engine_builder
from rtxmodelforge.features.build import types as build_types
from rtxmodelforge.features.engines import store
from rtxmodelforge.features.engines import types as engine_types
from rtxmodelforge.shared import build_planner
from rtxmodelforge.shared.build_planner import EngineMode, plan_build, read_model_arch
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.panels import stage_table
from rtxmodelforge.shared.types import StageResult, StageStatus


def run(config: build_types.BuildConfig) -> tuple[Path, Path]:
    """
    Executa o pipeline completo de build, compilando dois engines:
    um otimizado para chat (batch=1) e outro para serve (batch dinâmico).

    Returns:
        Tupla (chat_engine_dir, serve_engine_dir)
    """
    chat_engine_dir = store.get_engine_dir(config.model_id, config.quantization, "chat")
    serve_engine_dir = store.get_engine_dir(config.model_id, config.quantization, "serve")

    chat_exists = (chat_engine_dir / "engine.json").exists()
    serve_exists = (serve_engine_dir / "engine.json").exists()

    if chat_exists and serve_exists:
        console.print(
            f"\n[bold yellow]⚠ Ambos os engines já existem:[/bold yellow]\n"
            f"  Chat:  {chat_engine_dir}\n"
            f"  Serve: {serve_engine_dir}\n"
            "  Use [cyan]rtxforge list[/cyan] para ver engines compilados.\n"
            "  Use [cyan]rtxforge delete[/cyan] para remover e recompilar.\n"
        )
        return chat_engine_dir, serve_engine_dir

    stages = [
        StageResult("Baixando pesos do HuggingFace"),
        StageResult("Lendo configuração e calculando BuildPlan"),
        StageResult("Compilando engine CHAT (batch=1, max seq)"),
        StageResult("Compilando engine SERVE (multi-client)"),
        StageResult("Salvando metadados e limpeza"),
    ]

    weights_dir = chat_engine_dir / "weights"

    def update_display():
        console.clear()
        console.print(stage_table(stages))

    from rtxmodelforge.shared import config as shared_config
    settings = shared_config.get_settings()

    try:
        # Stage 1: Download (apenas se pesos ainda nao existem)
        if not weights_dir.exists():
            stages[0].status = StageStatus.RUNNING
            update_display()
            start = time.time()
            downloader.download_weights(
                model_id=config.model_id,
                target_dir=chat_engine_dir,
                hf_token=settings.hf_token,
                verbose=config.verbose,
            )
            stages[0].duration_s = time.time() - start
        stages[0].status = StageStatus.DONE

        # Stage 2: Read params + BuildPlan
        stages[1].status = StageStatus.RUNNING
        update_display()
        start = time.time()

        config.weights_dir = weights_dir
        config.params_billions = downloader.read_params_billions(weights_dir)

        arch = read_model_arch(weights_dir)
        chat_plan, serve_plan = plan_build(
            profile=config.gpu_info,
            params_b=config.params_billions,
            quantization=config.quantization,
            arch=arch,
        )

        stages[1].duration_s = time.time() - start
        stages[1].status = StageStatus.DONE

        # Atualiza o display para mostrar os planos calculados
        console.print(
            f"\n  [bold cyan]Chat:[/bold cyan] {chat_plan.summary}"
            f"\n  [bold cyan]Serve:[/bold cyan] {serve_plan.summary}\n"
        )

        # Coleta versão do TRT-LLM para metadata
        trt_ver = "desconhecido"
        try:
            import tensorrt_llm  # pyright: ignore[reportMissingImports]
            trt_ver = tensorrt_llm.__version__
        except ImportError:
            pass

        # Stage 3: Compilar engine CHAT (se ainda nao existe)
        if not chat_exists:
            stages[2].status = StageStatus.RUNNING
            update_display()
            start = time.time()

            chat_config = build_types.BuildConfig(
                model_id=config.model_id,
                weights_dir=weights_dir,
                gpu_info=config.gpu_info,
                quantization=config.quantization,
                quality_label=config.quality_label,
                rationale=config.rationale,
                params_billions=config.params_billions,
                verbose=config.verbose,
                engine_mode=EngineMode.CHAT,
                max_batch_size=chat_plan.max_batch_size,
                max_seq_len=chat_plan.max_seq_len,
                enable_chunked_context=chat_plan.enable_chunked_context,
            )
            engine_builder.build_engine(chat_config, chat_engine_dir)

            stages[2].duration_s = time.time() - start
        stages[2].status = StageStatus.DONE

        # Stage 4: Compilar engine SERVE (se ainda nao existe)
        if not serve_exists:
            stages[3].status = StageStatus.RUNNING
            update_display()
            start = time.time()

            serve_config = build_types.BuildConfig(
                model_id=config.model_id,
                weights_dir=weights_dir,
                gpu_info=config.gpu_info,
                quantization=config.quantization,
                quality_label=config.quality_label,
                rationale=config.rationale,
                params_billions=config.params_billions,
                verbose=config.verbose,
                engine_mode=EngineMode.SERVE,
                max_batch_size=serve_plan.max_batch_size,
                max_seq_len=serve_plan.max_seq_len,
                enable_chunked_context=serve_plan.enable_chunked_context,
            )
            engine_builder.build_engine(serve_config, serve_engine_dir)

            stages[3].duration_s = time.time() - start
        stages[3].status = StageStatus.DONE

        # Stage 5: Metadados
        stages[4].status = StageStatus.RUNNING
        update_display()
        start = time.time()

        vram_snapshot_gb = config.gpu_info.vram_total_gb - config.gpu_info.vram_free_gb

        for plan, engine_dir in (
            (chat_plan, chat_engine_dir),
            (serve_plan, serve_engine_dir),
        ):
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
                vram_used_gb=vram_snapshot_gb,
                engine_size_gb=store.get_dir_size_gb(engine_dir),
                architecture="desconhecida",
                max_seq_len=plan.max_seq_len,
                engine_mode=plan.mode.value,
                max_batch_size=plan.max_batch_size,
                build_plan_summary=plan.summary,
            )
            store.save_metadata(engine_dir, metadata)

        stages[4].duration_s = time.time() - start
        stages[4].status = StageStatus.DONE
        update_display()

        return chat_engine_dir, serve_engine_dir

    except Exception as e:
        for stage in stages:
            if stage.status == StageStatus.RUNNING:
                stage.status = StageStatus.FAILED
        update_display()
        raise e
