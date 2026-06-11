from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _serialize(obj: Any) -> Any:
    """Serializa objetos para JSON — suporta dataclass, pydantic, enum, datetime, Path."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    return obj


def print_json(data: Any, **overrides: Any) -> None:
    """Serializa `data` para JSON e imprime no stdout.

    Args:
        data: objeto serializavel (dataclass, pydantic, dict, lista).
        overrides: campos extras para mesclar no resultado.
    """
    if overrides:
        base = _serialize(data) if not isinstance(data, dict) else data
        base.update(overrides)
        output = base
    elif isinstance(data, dict):
        output = data
    else:
        output = _serialize(data)

    json.dump(output, sys.stdout, default=_serialize, ensure_ascii=False)
    sys.stdout.write("\n")
