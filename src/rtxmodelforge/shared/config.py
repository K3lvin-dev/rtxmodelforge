from __future__ import annotations
from pathlib import Path
from typing import Final, Optional
import tomllib
import tomli_w
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR: Final[Path] = Path.home() / ".rtxmodelforge"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RTXFORGE_",
        extra="ignore",
    )

    hf_token: Optional[str] = Field(default=None)
    engines_dir: Path = Field(default=CONFIG_DIR / "engines")

    @classmethod
    def load(cls) -> Settings:
        """Carrega configurações do TOML se existir, sobrescrevendo com Env Vars."""
        config_path = CONFIG_DIR / "config.toml"
        toml_data = {}
        if config_path.exists():
            with config_path.open("rb") as f:
                toml_data = tomllib.load(f)
        
        # Garantir diretório de engines
        settings = cls(**toml_data)
        settings.engines_dir.mkdir(parents=True, exist_ok=True)
        return settings

def save_hf_token(token: str) -> None:
    """Salva o token do HuggingFace no config.toml com permissões restritas (600)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)
    
    config_path = CONFIG_DIR / "config.toml"
    config_data = {}
    if config_path.exists():
        with config_path.open("rb") as f:
            config_data = tomllib.load(f)
    
    config_data["hf_token"] = token
    
    with config_path.open("wb") as f:
        f.write(tomli_w.dumps(config_data).encode("utf-8"))
    
    config_path.chmod(0o600)

def get_settings() -> Settings:
    return Settings.load()
