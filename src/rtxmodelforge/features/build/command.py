from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from typer import Exit

from rtxmodelforge.features.build import pipeline
from rtxmodelforge.features.build import types as build_types
from rtxmodelforge.features.build.downloader import fetch_params_billions
from rtxmodelforge.features.build.types import GatedModelError
from rtxmodelforge.shared import config as shared_config
from rtxmodelforge.shared import gpu
from rtxmodelforge.shared import types as shared_types
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.panels import header_panel, summary_panel


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
    
    console.print(f"[bold cyan]Iniciando processo de build para:[/bold cyan] {model_id}")
    
    # 1. Detectar GPU
    gpu_info = gpu.detect_gpu()
    if not gpu_info:
        error_console.print("[bold red]✘ Nenhuma GPU NVIDIA compatível detectada.[/bold red]")
        raise Exit(1)
        
    try:
        settings = shared_config.get_settings()
        console.print("[dim]Buscando configuração do modelo...[/dim]")
        params_est = fetch_params_billions(model_id, settings.hf_token) or 8.0

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
            raise Exit()
            
        # 4. Executar Pipeline
        build_conf = build_types.BuildConfig(
            model_id=model_id,
            weights_dir=Path("tmp"), # pipeline ajustará isso
            gpu_info=gpu_info,
            quantization=quant,
            quality_label=quality,
            rationale=rationale,
            params_billions=params_est,  # pipeline atualiza com valor exato no Stage 2
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
        
    except GatedModelError:
        error_console.print(
            f"\n[bold red]✘ Acesso negado ao modelo '[cyan]{model_id}[/cyan]'.[/bold red]\n\n"
            "  Este modelo requer autorização. Para resolver:\n\n"
            f"  [bold]1.[/bold] Aceite os termos em: [cyan]https://huggingface.co/{model_id}[/cyan]\n"
            "  [bold]2.[/bold] Gere um token em:    [cyan]https://huggingface.co/settings/tokens[/cyan]\n"
            "  [bold]3.[/bold] Autentique-se com:   [cyan]rtxforge login[/cyan]\n"
        )
        raise Exit(1) from None
    except shared_types.UnsupportedGPUError as e:
        error_console.print(f"[bold red]✘ GPU não suportada:[/bold red] {e}")
        raise Exit(1) from None
    except shared_types.InsufficientVRAMError as e:
        error_console.print(f"[bold red]✘ VRAM insuficiente:[/bold red] {e}")
        raise Exit(1) from None
    except Exception as e:
        error_console.print(f"[bold red]✘ Falha crítica no pipeline:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise Exit(1) from None
