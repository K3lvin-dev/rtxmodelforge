from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Final, List, Optional, Tuple

from rtxmodelforge.features.engines.types import CURRENT_SCHEMA_VERSION, EngineMetadata
from rtxmodelforge.shared import config
from rtxmodelforge.shared.console import console
from rtxmodelforge.shared.types import Quantization

logger = logging.getLogger(__name__)

METADATA_FILENAME: Final[str] = "engine.json"

# Cache em memória para load_metadata: evita re-parse de JSON no mesmo path.
# TTL curto (5s) para capturar mudanças, mas evitar n+1 leituras no mesmo fluxo.
_metadata_cache: dict[Path, tuple[float, Optional[EngineMetadata]]] = {}
_METADATA_CACHE_TTL: float = 5.0


class EngineNotFoundError(Exception):
    pass


def get_engine_dir(model_id: str, quantization: Quantization, mode: str = "chat") -> Path:
    """Retorna o path padrão para um engine (ex: engines/org/model/fp8-chat/)."""
    settings = config.get_settings()
    return settings.engines_dir / model_id / f"{quantization.value}-{mode}"


def save_metadata(engine_path: Path, metadata: EngineMetadata) -> None:
    """Salva o metadata.json no diretório do engine."""
    engine_path.mkdir(parents=True, exist_ok=True)
    metadata_path = engine_path / METADATA_FILENAME

    with metadata_path.open("w", encoding="utf-8") as f:
        f.write(metadata.model_dump_json(indent=2))

    # Invalida cache para garantir que próxima leitura pegue a versão atualizada
    _metadata_cache.pop(engine_path, None)


def load_metadata(engine_path: Path) -> Optional[EngineMetadata]:
    """Carrega o metadata de um engine. Emite warning se schema for antigo.

    Mantém cache em memória com TTL de {_METADATA_CACHE_TTL}s para evitar
    re-parse de JSON no mesmo fluxo de execução.
    """
    now = time.monotonic()
    cached = _metadata_cache.get(engine_path)
    if cached is not None and now - cached[0] < _METADATA_CACHE_TTL:
        return cached[1]

    metadata_path = engine_path / METADATA_FILENAME
    if not metadata_path.exists():
        _metadata_cache[engine_path] = (now, None)
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
            _metadata_cache[engine_path] = (now, metadata)
            return metadata
    except Exception:
        logger.debug("Falha ao carregar metadata de %s", engine_path, exc_info=True)
        _metadata_cache[engine_path] = (now, None)
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
    _metadata_cache.pop(engine_path, None)


# Cache para get_dir_size_gb — evita re-statar todos os arquivos do mesmo dir
_dir_size_cache: dict[Path, tuple[float, float]] = {}
_DIR_SIZE_CACHE_TTL: float = 30.0


def get_dir_size_gb(path: Path) -> float:
    """Calcula o tamanho de um diretório em GB com cache TTL de {_DIR_SIZE_CACHE_TTL}s."""
    now = time.monotonic()
    cached = _dir_size_cache.get(path)
    if cached is not None and now - cached[0] < _DIR_SIZE_CACHE_TTL:
        return cached[1]

    total = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())
    size_gb = total / 1e9
    _dir_size_cache[path] = (now, size_gb)
    return size_gb
