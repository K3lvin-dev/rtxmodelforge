from __future__ import annotations

import shutil
from pathlib import Path
from typing import Final, List, Optional, Tuple

from rtxmodelforge.features.engines.types import CURRENT_SCHEMA_VERSION, EngineMetadata
from rtxmodelforge.shared import config
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.types import Quantization

METADATA_FILENAME: Final[str] = "engine.json"


class EngineNotFoundError(Exception):
    pass


def get_engine_dir(model_id: str, quantization: Quantization) -> Path:
    """Retorna o path padrão para um engine (ex: engines/org/model/fp8/)."""
    settings = config.get_settings()
    return settings.engines_dir / model_id / quantization.value


def save_metadata(engine_path: Path, metadata: EngineMetadata) -> None:
    """Salva o metadata.json no diretório do engine."""
    engine_path.mkdir(parents=True, exist_ok=True)
    metadata_path = engine_path / METADATA_FILENAME

    with metadata_path.open("w", encoding="utf-8") as f:
        f.write(metadata.model_dump_json(indent=2))


def load_metadata(engine_path: Path) -> Optional[EngineMetadata]:
    """Carrega o metadata de um engine. Emite warning se schema for antigo."""
    metadata_path = engine_path / METADATA_FILENAME
    if not metadata_path.exists():
        return None

    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = EngineMetadata.model_validate_json(f.read())

            if metadata.schema_version != CURRENT_SCHEMA_VERSION:
                console.print(
                    f"[yellow][WARNING] Engine em {engine_path} usa schema "
                    f"v{metadata.schema_version} (atual: v{CURRENT_SCHEMA_VERSION}). "
                    "Recomenda-se recompilar.[/yellow]"
                )
            return metadata
    except Exception:
        return None


def list_engines() -> List[Tuple[Path, EngineMetadata]]:
    """Lista todos os engines encontrados no engines_dir, ordenados pelo mais recente."""
    settings = config.get_settings()
    engines = []

    for meta_path in settings.engines_dir.rglob(METADATA_FILENAME):
        meta = load_metadata(meta_path.parent)
        if meta:
            engines.append((meta_path.parent, meta))

    # Ordenar por data de compilação (descendente)
    engines.sort(key=lambda x: x[1].built_at, reverse=True)
    return engines


def delete_engine(engine_path: Path) -> None:
    """Remove o diretório do engine completamente."""
    if not (engine_path / METADATA_FILENAME).exists():
        raise EngineNotFoundError(f"Nenhum engine encontrado em {engine_path}")

    shutil.rmtree(engine_path)


def get_dir_size_gb(path: Path) -> float:
    """Calcula o tamanho de um diretório em GB."""
    total = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())
    return total / 1e9
