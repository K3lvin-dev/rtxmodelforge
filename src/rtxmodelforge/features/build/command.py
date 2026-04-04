from __future__ import annotations
from typing import Annotated, Optional
import typer
from rtxmodelforge.shared import gpu, types as shared_types, config as shared_config
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.panels import header_panel, summary_panel
from rtxmodelforge.features.build import pipeline, types as build_types
from rtxmodelforge.features.engines import store

def build(
    model_id: Annotated[
        str, 
        typer.Argument(help="ID do modelo no HuggingFace (ex: meta-llama/Llama-3.1-8B).")
    ],
    verbose: Annotated[
        bool, 
        typer.Option("--verbose", help="Exibe logs detalhados durante a compilação.")
    ] = False,
) -> None:
    """Compila um engine TensorRT-LLM otimizado para sua GPU RTX."""
    
    console.print("[bold cyan]Iniciando processo de build para:[/bold cyan] " + model_id)
    
    # 1. Detectar GPU
    gpu_info = gpu.detect_gpu()
    if not gpu_info:
        error_console.print("[bold red]✘ Nenhuma GPU NVIDIA compatível detectada.[/bold red]")
        raise typer.Exit(1)
        
    # 2. Recomendação de Quantização
    # Precisamos de uma estimativa de parâmetros. Como não baixamos ainda,
    # tentaremos obter via API do HF ou usaremos um valor default conservador
    # para a primeira passagem de recomendação, ou solicitaremos ao usuário.
    # TODO: Refinar busca de params_billions antes do download se possível via Hub API.
    
    # Por enquanto, usaremos 8.0B como exemplo para demonstração ou pediremos
    # No pipeline real, Stage 2 atualiza este valor.
    params_est = 8.0 
    
    try:
        quant, quality, rationale = shared_types.recommend_quantization(gpu_info, params_est)
        
        # 3. Exibir Painel de Início
        console.print(header_panel(
            model_id=model_id,
            gpu=gpu_info.name,
            quantization=quant.value.upper(),
            rationale=rationale
        ))
        
        if not typer.confirm("\nDeseja prosseguir com a compilação?", default=True):
            console.print("Operação cancelada pelo usuário.")
            raise typer.Exit()
            
        # 4. Executar Pipeline
        build_conf = build_types.BuildConfig(
            model_id=model_id,
            weights_dir=Path("tmp"), # pipeline ajustará isso
            gpu_info=gpu_info,
            quantization=quant,
            quality_label=quality,
            rationale=rationale,
            params_billions=params_est,
            verbose=verbose
        )
        
        engine_path = pipeline.run(build_conf)
        
        # 5. Resumo Final
        console.print(summary_panel(
            engine_path=engine_path,
            next_commands=[
                f"rtxforge serve {engine_path}",
                f"rtxforge chat {engine_path}"
            ]
        ))
        
    except shared_types.UnsupportedGPUError as e:
        error_console.print(f"[bold red]✘ GPU não suportada:[/bold red] {e}")
        raise typer.Exit(1)
    except shared_types.InsufficientVRAMError as e:
        error_console.print(f"[bold red]✘ VRAM insuficiente:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        error_console.print(f"[bold red]✘ Falha crítica no pipeline:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)

from pathlib import Path
