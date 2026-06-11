from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer import Exit

from rtxmodelforge.features.engines import store
from rtxmodelforge.shared.cli_decorators import handle_cli_errors
from rtxmodelforge.shared.console import console, error_console
from rtxmodelforge.shared.gpu_profiler import profile_gpu
from rtxmodelforge.shared.panels import runtime_dashboard
from rtxmodelforge.shared.runtime_planner import plan_runtime
from rtxmodelforge.shared.workflow import prepare_model


@handle_cli_errors(verbose=False)
def serve(
    model_id: Annotated[Optional[str], typer.Argument(help="ID do modelo no HuggingFace.")] = None,
    engine_path: Annotated[
        Optional[Path],
        typer.Option("--engine-path", help="Caminho direto para um engine já compilado."),
    ] = None,
    port: Annotated[int, typer.Option("--port", help="Porta para o servidor REST.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Host para o servidor REST.")] = "127.0.0.1",
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Exibe logs detalhados na preparação.")
    ] = False,
) -> None:
    """Prepara automaticamente o melhor artefato para Tensor Cores e sobe API local."""
    if engine_path is None:
        if model_id is None:
            error_console.print("[bold red]✘ Informe um model_id ou --engine-path.[/bold red]")
            raise Exit(1)
        _chat_engine, engine_path, _gpu, selection = prepare_model(model_id, verbose=verbose)
        console.print(
            f"[bold green]Modo acelerado escolhido para sua RTX:[/bold green] "
            f"{selection.tensor_core_path_label} ({selection.acceleration_class.value})"
        )

    meta = store.load_metadata(engine_path)
    if not meta:
        error_console.print(f"[bold red]✘ Nenhum engine válido em:[/bold red] {engine_path}")
        raise Exit(1) from None

    if meta.engine_mode != "serve":
        error_console.print(
            f"[bold yellow]⚠ Este engine foi compilado para modo '{meta.engine_mode}'.[/bold yellow]\n"
            "  Para serve, use um engine compilado com modo 'serve' (multi-batch).\n"
            "  Dica: use o diretório com sufixo '-serve', ex: .../fp8-serve/"
        )
        raise Exit(1)

    # Detectar GPU e calcular plano de runtime
    gpu_profile = profile_gpu()
    if gpu_profile is None:
        error_console.print("[bold red]✘ GPU não detectada.[/bold red]")
        raise Exit(1)

    runtime_plan = plan_runtime(
        profile=gpu_profile,
        model_id=meta.model_id,
        quantization_str=meta.quantization.lower(),
        params_b=meta.params_billions,
        engine_mode=meta.engine_mode,
        max_batch_size=meta.max_batch_size,
        engine_size_gb=meta.engine_size_gb,
        architecture_label=meta.target_architecture or gpu_profile.architecture.value,
        acceleration_class=meta.acceleration_class or "modo acelerado parcial",
        tensor_core_path_label=meta.effective_precision or meta.quantization.upper(),
        fallback_reason=meta.fallback_reason or None,
    )

    console.print("\n[bold blue]Iniciando Servidor de Inferência[/bold blue]")
    console.print(runtime_dashboard(runtime_plan))

    if runtime_plan.vram_warning:
        console.print(f"[bold yellow]⚠ Aviso:[/bold yellow] {runtime_plan.vram_warning}\n")

    console.print(f"  Endereço:  [bold underline]http://{host}:{port}/v1/...[/bold underline]\n")

    if host == "0.0.0.0":
        console.print("[yellow]⚠ Aviso: O servidor estará exposto na rede local.[/yellow]")
        if not typer.confirm("Deseja continuar?", default=False):
            raise Exit() from None

    cmd = [
        "trtllm-serve",
        "serve",
        str(engine_path),
        "--tokenizer",
        meta.model_id,
        "--host",
        host,
        "--port",
        str(port),
        "--max_batch_size",
        str(runtime_plan.max_batch_size),
        "--kv_cache_free_gpu_memory_fraction",
        f"{runtime_plan.kv_cache_fraction:.2f}",
    ]

    try:
        console.print("[dim]Pressione Ctrl+C para encerrar o servidor.[/dim]\n")
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[bold green]✔ Servidor encerrado pelo usuário.[/bold green]")
    except subprocess.CalledProcessError as e:
        error_console.print(f"[bold red]✘ Falha ao iniciar trtllm-serve:[/bold red] {e}")
        raise Exit(1) from None
    except FileNotFoundError:
        error_console.print("[bold red]✘ Comando 'trtllm-serve' não encontrado.[/bold red]")
        raise Exit(1) from None
