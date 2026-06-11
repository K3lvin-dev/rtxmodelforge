from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import huggingface_hub
from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError

from rtxmodelforge.features.build.types import GatedModelError
from rtxmodelforge.shared.console import console

logger = logging.getLogger(__name__)


def _estimate_params_from_config(data: dict) -> Optional[float]:
    """Estima número de parâmetros a partir do config.json.

    Tenta campo explícito 'num_parameters', senão calcula via arquitetura
    (Llama, Mistral, Qwen2, etc.).
    """
    if "num_parameters" in data:
        return data["num_parameters"] / 1e9

    h = data.get("hidden_size")
    num_layers = data.get("num_hidden_layers")
    i = data.get("intermediate_size")
    v = data.get("vocab_size", 32000)

    if h and num_layers and i:
        # Aproximação simplificada: (Embeddings + Layers(Self-Attn + MLP))
        # MLP costuma ser 3 * intermediate_size * hidden_size (Gate, Up, Down)
        # Attn costuma ser 4 * hidden_size^2 (Q, K, V, O)
        params = v * h + num_layers * (4 * h**2 + 3 * i * h)
        return params / 1e9

    return None


def fetch_params_billions(model_id: str, hf_token: Optional[str] = None) -> Optional[float]:
    """Baixa apenas o config.json para estimar parâmetros antes do download completo."""
    try:
        config_path = huggingface_hub.hf_hub_download(  # type: ignore
            repo_id=model_id,
            filename="config.json",
            token=hf_token,
        )
        with open(config_path) as f:
            data = json.load(f)

        return _estimate_params_from_config(data)

    except Exception:
        logger.debug("Falha ao buscar/parsear config.json de %s", model_id, exc_info=True)

    return None


def download_weights(
    model_id: str, target_dir: Path, hf_token: Optional[str] = None, verbose: bool = False
) -> Path:
    """Baixa os pesos do HuggingFace e retorna o caminho local."""
    try:
        # Padrões para ignorar para economizar espaço
        ignore = ["*.msgpack", "flax_model*", "tf_model*", "*.h5", "*.ot"]

        weights_path = huggingface_hub.snapshot_download( # type: ignore
            repo_id=model_id,
            local_dir=str(target_dir / "weights"),
            token=hf_token,
            ignore_patterns=ignore,
        )

        return Path(weights_path)

    except GatedRepoError:
        raise GatedModelError(
            f"O modelo '{model_id}' exige acesso autorizado. "
            "Configure com: [cyan]rtxforge login --token <token>[/cyan]"
        ) from None
    except RepositoryNotFoundError:
        raise ValueError(f"Modelo não encontrado no HuggingFace: {model_id}") from None
    except Exception as e:
        raise RuntimeError(f"Falha no download: {e}") from None


def read_params_billions(weights_dir: Path) -> float:
    """
    Lê o config.json do modelo e extrai/estima o número de parâmetros em bilhões.
    Tenta o campo 'num_parameters' ou calcula via arquitetura.
    """
    config_path = weights_dir / "config.json"
    if not config_path.exists():
        return _prompt_params_billions()

    try:
        with config_path.open("r") as f:
            data = json.load(f)

        result = _estimate_params_from_config(data)
        if result is not None:
            return result

    except Exception:
        logger.debug("Falha ao parsear config.json em %s", weights_dir, exc_info=True)

    return _prompt_params_billions()


def _prompt_params_billions() -> float:
    """Fallback: pergunta ao usuário o tamanho do modelo."""
    console.print(
        "[yellow]Não foi possível detectar o número de parâmetros automaticamente.[/yellow]"
    )
    while True:
        val = console.input(
            "[bold cyan]Qual o tamanho do modelo em bilhões de parâmetros? (ex: 8.0): [/bold cyan]"
        )
        try:
            return float(val)
        except ValueError:
            console.print("[red]Por favor, informe um número válido.[/red]")
