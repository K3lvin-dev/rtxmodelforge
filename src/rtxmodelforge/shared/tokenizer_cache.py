"""Cache de tokenizers em memória para evitar re-download/re-carga do HuggingFace.

Usado por chat.py e workflow.py para reutilizar o AutoTokenizer carregado
sem precisar chamar from_pretrained() a cada inicialização de sessão.
"""

from __future__ import annotations

from typing import Optional

from transformers import AutoTokenizer  # pyright: ignore[reportMissingImports]

_tokenizer_cache: dict[str, "AutoTokenizer"] = {}


def get_tokenizer(model_id: str) -> "AutoTokenizer":
    """Retorna tokenizer cacheado para o model_id. Carrega na primeira chamada."""
    if model_id not in _tokenizer_cache:
        _tokenizer_cache[model_id] = AutoTokenizer.from_pretrained(model_id)
    return _tokenizer_cache[model_id]


def invalidate_tokenizer_cache(model_id: Optional[str] = None) -> None:
    """Invalida cache de tokenizer. Se model_id=None, limpa tudo."""
    if model_id is None:
        _tokenizer_cache.clear()
    else:
        _tokenizer_cache.pop(model_id, None)
