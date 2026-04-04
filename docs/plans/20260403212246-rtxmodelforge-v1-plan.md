---
title: "RTX Model Forge — V1 CLI Implementation"
type: enhancement
status: active
date: 2026-04-03
phased: true
---

# RTX Model Forge — V1 CLI Implementation Plan

**Brainstorm de origem:** `docs/brainstorms/20260403211929-rtxmodelforge-v1-brainstorm.md`

---

## Overview

CLI Python para Linux que orquestra o pipeline TensorRT-LLM — download de pesos, compilação do engine otimizado via LLM API — entregando modelos rodando 2–4× mais rápido que ferramentas genéricas, com uso máximo dos Tensor Cores da GPU.

**Público:** usuários Linux com GPU NVIDIA RTX série 30, 40 ou 50 que querem o máximo do hardware sem se tornar engenheiros de ML.

**Modelos suportados:** qualquer arquitetura compatível com TensorRT-LLM — Llama, Mistral/Mixtral, DeepSeek V2/V3/R1, Qwen 2/3, Phi 3/4, Gemma 2/3, e outros. A LLM API lida com as diferenças de arquitetura automaticamente; o RTX Model Forge não filtra por `model_type`.

---

## Decisões Técnicas Finais

| Decisão | Escolha |
|---------|---------|
| GPUs suportadas | RTX série 30 (Ampere SM86+), 40 (Ada SM89), 50 (Blackwell GB20x) — single-GPU apenas |
| Multi-GPU | V1: sempre `tensor_parallel_size=1`, GPU index 0. Doctor avisa se múltiplas GPUs detectadas. |
| RTX 20 series | ❌ Não suportado — TensorRT-LLM não suporta SM75 |
| Pipeline de compilação | `LLM(model, backend="tensorrt", quant_config)` + `llm.save(engine_dir)` |
| Seleção de quantização | Automática por SM version + VRAM disponível |
| Auth HuggingFace | `HF_TOKEN` env var → `config.toml` |
| Engine storage | `~/.rtxmodelforge/engines/<org>/<model>/<quantization>/` |
| Versioning de engines | `engine.json` com `trtllm_version` + `schema_version`; warning em incompatibilidade |
| Auth servidor local | Sem auth — bind exclusivo em `127.0.0.1` por padrão; `--host 0.0.0.0` exige confirmação explícita |
| Rebuild de engine existente | Detecta engine existente → exibe metadata → `typer.confirm("Recompilar?")` → se não, sugere `serve`/`chat` |
| Permissões de arquivo | `~/.rtxmodelforge/` → `700`; `config.toml` → `600` (set em `save_hf_token` e `install.sh`) |
| Distribuição | Bash `install.sh` no GitHub Releases |
| SO mínimo | Ubuntu 24.04 |
| CUDA | 13.1 |
| PyTorch | 2.10.0 (cu130) |

---

## Lógica de Quantização Automática

A seleção usa dois critérios em cascata: **SM version** (determina formatos disponíveis nos Tensor Cores) → **VRAM** (determina o que cabe).

### Formatos por arquitetura

| Arquitetura | SM | RTX série | Tensor Core Gen | Formato primário | Fallback 1 | Fallback 2 |
|-------------|-----|-----------|----------------|-----------------|-----------|-----------|
| Ampere | SM86 | RTX 30 | 3ª | INT8 (W8A16) | INT4 AWQ | — |
| Ada Lovelace | SM89 | RTX 40 | 4ª | **FP8 (W8A8)** | INT8 | INT4 AWQ |
| Blackwell | GB20x | RTX 50 | 5ª | **FP8 (W8A8)** | FP4 (NVFP4) | — |

> **Por que FP8 é o primário no Ada e Blackwell?**
> FP8 usa os Tensor Cores de 4ª/5ª geração no modo mais eficiente: ~99% da qualidade do FP16, 2× throughput vs INT8, 50% menos VRAM que FP16.
>
> **Por que FP4 é só fallback no Blackwell?**
> FP4 tem queda de qualidade mais acentuada (~95% vs FP16). Só vale quando VRAM é o gargalo.

### Estimativa de VRAM por formato

Dado `params_billions` (lido de `config.json`):

```
vram_needed = params_billions × bytes_per_param × 1.3  (30% overhead KV cache + ativações)

FP8 / INT8  → bytes_per_param = 1.0
INT4 / FP4  → bytes_per_param = 0.5
```

### Pseudocódigo da decisão

```
SM < 80  → UnsupportedGPUError (série 20 e anterior)

SM 80–88 (Ampere / RTX 30):
  cabe INT8?    → INT8  "Tensor Cores Ampere — melhor custo-benefício"
  cabe INT4?    → INT4 AWQ  "VRAM insuficiente para INT8"
  senão         → InsufficientVRAMError

SM 89 (Ada / RTX 40):
  cabe FP8?     → FP8   "4ª geração Tensor Cores — 2× INT8, ~99% qualidade"
  cabe INT8?    → INT8  "FP8 não cabe na VRAM disponível"
  cabe INT4?    → INT4 AWQ  "VRAM muito limitada"
  senão         → InsufficientVRAMError

SM ≥ 100 (Blackwell / RTX 50):
  cabe FP8?     → FP8   "5ª geração Tensor Cores — máximo custo-benefício"
  cabe FP4?     → FP4   "NVFP4 nativo Blackwell — 2× FP8 throughput"
  senão         → InsufficientVRAMError
```

---

## Proposed Solution

### Arquitetura: Vertical Slice Architecture (VSA)

Cada feature é um slice auto-contido. `shared/` é mínimo — apenas infraestrutura transversal. Features dependem de `shared/`, nunca de outras features.

### Estrutura de diretórios

```
rtxmodelforge/
├── pyproject.toml
├── install.sh
└── src/
    └── rtxmodelforge/
        ├── __init__.py
        ├── main.py
        ├── shared/
        │   ├── __init__.py
        │   ├── console.py          # Rich Console singleton
        │   ├── panels.py           # Painéis Rich reutilizáveis
        │   ├── config.py           # Pydantic Settings + TOML
        │   ├── gpu.py              # GPU detection (pynvml + sm_version)
        │   └── types.py            # Enums, dataclasses, lógica de quantização
        └── features/
            ├── build/
            │   ├── __init__.py
            │   ├── command.py      # rtxforge build
            │   ├── pipeline.py     # orquestrador (download → compile → save)
            │   ├── downloader.py   # HuggingFace download
            │   ├── engine_builder.py  # LLM API wrapper (compila + salva engine)
            │   └── types.py        # BuildConfig, StageResult, erros do slice
            ├── serve/
            │   ├── __init__.py
            │   └── command.py      # rtxforge serve
            ├── chat/
            │   ├── __init__.py
            │   └── command.py      # rtxforge chat
            ├── login/
            │   ├── __init__.py
            │   └── command.py      # rtxforge login
            ├── doctor/
            │   ├── __init__.py
            │   ├── command.py      # rtxforge doctor
            │   └── checks.py      # funções de check individuais
            └── engines/
                ├── __init__.py
                ├── store.py        # engine storage, metadata, listagem
                ├── list_command.py
                ├── delete_command.py
                └── types.py        # EngineMetadata (Pydantic)
```

### Stack técnica

| Camada | Biblioteca | Versão |
|--------|-----------|--------|
| Python | — | 3.12+ |
| CLI | `typer` | `>=0.15` |
| Output visual | `rich` | `>=14.0` |
| Settings | `pydantic-settings[toml]` | `>=2.7` |
| Modelos de dados | `pydantic` | `>=2.10` |
| HTTP | `httpx` | `>=0.28` |
| GPU detection | `pynvml` | `>=12.0` |
| Download | `huggingface_hub` | `>=0.28` |
| Compilação/Inferência | `tensorrt_llm` | `>=0.17` |
| Serialização TOML | `tomli-w` | `>=1.1` |

### Schema `EngineMetadata`

```python
class EngineMetadata(BaseModel):
    schema_version: int = 1  # incrementar a cada mudança breaking no schema
    model_id: str
    gpu_model: str
    sm_version: int
    quantization: str        # "fp8" | "int8" | "int4_awq" | "fp4"
    quality_label: str       # "max-quality" | "balanced" | "max-speed"
    quantization_rationale: str  # ex: "FP8: 4ª geração Tensor Cores — 2× INT8, ~99% qualidade"
    trtllm_version: str
    built_at: datetime
    engine_path: str
    params_billions: float
    vram_used_gb: float      # estimativa: params_billions × bytes_per_param × 1.3
    engine_size_gb: float    # tamanho do diretório do engine em disco
    architecture: str        # valor de model_type do config.json (ex: "llama", "qwen2", "deepseek_v3")
    max_seq_len: int
```

**Política de `schema_version`:** `load_metadata()` compara `schema_version` do arquivo com `CURRENT_SCHEMA_VERSION = 1` no código. Se diferente, exibe `[WARNING]` com instrução de recompilar — nunca falha silenciosamente.

---

## Clarifications

Ver arquivo completo: `docs/plans/20260403212246-rtxmodelforge-v1-plan.clarifications.md`

**Decisões resolvidas:**
- `LLM()` requer `backend="tensorrt"` + `llm.save(engine_dir)` explícito (não tem `engine_dir` no construtor)
- Chat trunca histórico com aviso quando excede `max_seq_len`, preservando system prompt
- V1 é single-GPU apenas (`tensor_parallel_size=1`); doctor avisa se múltiplas GPUs detectadas
- `vram_used_gb` é estimativa estática (`params_billions × bytes_per_param × 1.3`)
- Escopo de modelos expandido para todos compatíveis com TensorRT-LLM (DeepSeek, Qwen, Phi, Gemma, etc.)

---

## Technical Considerations

- `from __future__ import annotations` em todos os módulos
- **`pydantic-settings[toml]`** — o extra `[toml]` é obrigatório para `SettingsConfigDict(toml_file=...)`
- **`tomli-w`** para serializar TOML ao salvar `config.toml`; `tomllib` (stdlib 3.12) apenas para leitura
- **`setuptools.build_meta`** como build-backend (não `setuptools.backends.legacy:build`)
- **`pynvml.nvmlDeviceGetCudaComputeCapability(handle)`** retorna `(major, minor)` → `sm_version = major * 10 + minor`; RTX 3090 = SM86, RTX 4090 = SM89, RTX 5090 = SM100+
- **LLM API (TensorRT backend)** — dois passos distintos: `LLM(model=model_id, backend="tensorrt", quant_config=QuantConfig(...))` compila internamente → `llm.save(str(engine_dir))` persiste em disco → `llm.shutdown()`. Para carregar engine salvo: `LLM(model=str(engine_dir))`. O backend PyTorch (`_TorchLLM`) não tem `save()` e não gera engines compilados — não usar para este projeto.
- **`QuantConfig` e `QuantAlgo`** importados de `tensorrt_llm.llmapi`
- **`trtllm-serve serve <model>`** — subcomando `serve` obrigatório; `--tokenizer` obrigatório quando carregando engine compilado
- **Parâmetros do modelo** — lidos de `weights_dir/config.json`; campo `num_parameters` ou estimado via `num_hidden_layers × hidden_size × ...` se não presente
- **VSA rule** — `shared/` nunca importa de `features/`; `StageResult`/`StageStatus` ficam em `shared/types.py`

---

## Acceptance Criteria

### Comunicação de quantização selecionada (CHK013/CHK014)

Antes de iniciar qualquer etapa, o `header_panel` exibe:
```
┌─────────────────────────────────────────────────────┐
│  RTX Model Forge — Building Engine                  │
│  Modelo:      meta-llama/Llama-3.1-8B               │
│  GPU:         RTX 4070 (12.0GB livres)              │
│  Formato:     FP8 ← automático                      │
│  Motivo:      4ª geração Tensor Cores — 2× INT8,    │
│               ~99% qualidade, cabe em VRAM           │
│  Estimativa:  10–30 minutos. Não feche o terminal.  │
└─────────────────────────────────────────────────────┘
```

Se houve **fallback** (formato primário não coube na VRAM), exibir aviso antes do painel:
```
[WARNING] FP8 requer ~10.4GB, disponível: 7.8GB. Usando INT8 (próximo melhor formato).
```

### Progresso durante compilação (CHK043)

O `LLM()` não expõe progresso percentual interno via API pública. Solução:
- Exibir **Rich Live** com elapsed time atualizado a cada segundo durante a etapa de compilação
- Em modo `--verbose`: capturar stdout do `LLM()` via redirect e exibir linhas em tempo real
- Formato do live display (etapa 3):
  ```
  ⠸ Compilando engine    ████████████░░░░  [tempo decorrido: 8m 32s]
                         Última linha: "Building TRT engine layer 47/128..."
  ```
- A "última linha" é atualizada sempre que `LLM()` emite stdout (mode verbose) ou mostra `"Processando..."` em modo padrão

### Servidor local — auth (CHK007)

**Decisão explícita:** sem autenticação. Justificativa: serve exclusivamente em `127.0.0.1` (loopback). Acessível apenas por processos locais do mesmo usuário.

Se usuário passa `--host 0.0.0.0`:
```
[WARNING] Expondo o servidor na rede local (0.0.0.0). Sem autenticação.
          Qualquer dispositivo na rede poderá enviar requisições.
Continuar? [s/N]:
```

---

### Seleção automática — RTX 40 com modelo 8B

- **Given** RTX 4070 (12GB VRAM livre), modelo Llama-3.1-8B (8.03B params)
- **When** `rtxforge build meta-llama/Llama-3.1-8B`
- **Then** seleciona FP8 (8.03B × 1.0 × 1.3 ≈ 10.4GB — cabe); exibe `"FP8: 4ª geração Tensor Cores — 2× INT8, ~99% qualidade"`

### Seleção automática — RTX 30 (sem FP8)

- **Given** RTX 3080 (10GB VRAM livre), modelo 7B
- **When** `rtxforge build <modelo>`
- **Then** seleciona INT8 (FP8 não disponível no Ampere); exibe rationale correto

### Fallback por VRAM — RTX 40 modelo grande

- **Given** RTX 4060 (8GB VRAM), modelo 13B
- **When** `rtxforge build <modelo>`
- **Then** FP8 não cabe (13B × 1.0 × 1.3 ≈ 16.9GB > 8GB) → INT8 não cabe → INT4 AWQ (13B × 0.5 × 1.3 ≈ 8.4GB) — próximo; se não couber: `InsufficientVRAMError` com mensagem clara

### GPU não suportada — RTX 20

- **Given** RTX 2080 detectada (SM75)
- **When** qualquer comando de build
- **Then** `UnsupportedGPUError`: `"RTX série 20 (SM75) não suportada. TensorRT-LLM requer SM80+."`

### Doctor — CUDA 13.1

- **Given** CUDA 12.x instalado
- **When** `rtxforge doctor`
- **Then** check CUDA falha com `✘` e mensagem `"CUDA 13.1+ necessário. Instalado: 12.x"`

### Serve com tokenizer

- **Given** engine compilado em `~/.rtxmodelforge/engines/meta-llama/Llama-3.1-8B/fp8/`
- **When** `rtxforge serve <engine_path>`
- **Then** executa `trtllm-serve serve <engine_path> --tokenizer meta-llama/Llama-3.1-8B --port 8000`

---

## Implementation Plan

| Phase | Name | Depends On | Status |
|-------|------|------------|--------|
| 1 | Project Foundation | None | ⬜ Pending |
| 2 | Shared Infrastructure | Phase 1 | ⬜ Pending |
| 3 | Doctor & Login Slices | Phase 2 | ⬜ Pending |
| 4 | Engines Slice | Phase 2 | ⬜ Pending |
| 5 | Build Slice | Phase 4 | ⬜ Pending |
| 6 | Serve & Chat Slices | Phase 5 | ⬜ Pending |
| 7 | Install Script | Phase 6 | ⬜ Pending |

---

### Phase 1: Project Foundation

**Status**: ⬜ Pending
**Objective**: `pyproject.toml` configurado, estrutura VSA criada, `rtxforge --help` operacional.
**Dependencies**: None

**Tasks**:

- [ ] T001 Criar `pyproject.toml` na raiz
  - `[project]`: `name = "rtxmodelforge"`, `version = "0.1.0"`, `requires-python = ">=3.12"`
  - `[project.dependencies]`:
    ```
    "typer>=0.15",
    "rich>=14.0",
    "pydantic>=2.10",
    "pydantic-settings[toml]>=2.7",
    "httpx>=0.28",
    "pynvml>=12.0",
    "huggingface_hub>=0.28",
    "tomli-w>=1.1",
    "transformers>=4.48",
    ```
  - `[project.optional-dependencies]`: `dev = ["pytest>=8.3", "pytest-mock>=3.14", "mypy>=1.13"]`
  - `[project.scripts]`: `rtxforge = "rtxmodelforge.main:app"`
  - `[build-system]`: `requires = ["setuptools>=75"]`, `build-backend = "setuptools.build_meta"`
  - `[tool.setuptools.packages.find]`: `where = ["src"]`
  - `[tool.mypy]`: `strict = true`, `python_version = "3.12"`

- [ ] T002 Criar estrutura de diretórios VSA e `__init__.py` files
  - `src/rtxmodelforge/__init__.py` → `__version__ = "0.1.0"`
  - `src/rtxmodelforge/shared/__init__.py` vazio
  - `src/rtxmodelforge/features/__init__.py` vazio
  - Um `__init__.py` vazio em cada feature: `build/`, `serve/`, `chat/`, `login/`, `doctor/`, `engines/`

- [ ] T003 Criar `src/rtxmodelforge/shared/console.py`
  - `from __future__ import annotations`
  - `console: Final[Console] = Console(highlight=False)`
  - `error_console: Final[Console] = Console(stderr=True, style="bold red")`

- [ ] T004 Criar `src/rtxmodelforge/shared/panels.py`
  - `from __future__ import annotations`; importa `StageResult` de `shared/types.py`
  - `header_panel(model_id: str, gpu: str, quantization: str, rationale: str, time_estimate: str = "10–30 minutos") -> Panel`
    - `box=box.ROUNDED`; exibe 5 linhas: model, gpu, formato, rationale, estimativa de tempo
  - `stage_table(stages: list[StageResult]) -> Table`
    - Colunas: `Status`, `Etapa`, `Duração`
  - `summary_panel(engine_path: Path, next_commands: list[str]) -> Panel`
    - `style="bold green"`; path do engine + comandos sugeridos

- [ ] T005 Criar `src/rtxmodelforge/main.py`
  - `app = typer.Typer(name="rtxforge", rich_markup_mode="rich", no_args_is_help=True)`
  - Callback `--version` imprime `rtxforge 0.1.0` e `raise typer.Exit()`
  - Registrar stubs de todos os 7 subcomandos (exibem `"Em breve"`)

**Verificação após Phase 1**:
```bash
pip install -e ".[dev]"
rtxforge --help
rtxforge --version
```

---

### Phase 2: Shared Infrastructure

**Status**: ⬜ Pending
**Objective**: `types.py` com quantização por arquitetura, `config.py` e `gpu.py` com SM version.
**Dependencies**: Phase 1

**Tasks**:

- [ ] T006 Criar `src/rtxmodelforge/shared/types.py`
  - `from __future__ import annotations`
  - `class Quantization(str, Enum)`: `FP8 = "fp8"`, `INT8 = "int8"`, `INT4_AWQ = "int4_awq"`, `FP4 = "fp4"`
  - `class QualityLabel(str, Enum)`: `MAX_QUALITY = "max-quality"`, `BALANCED = "balanced"`, `MAX_SPEED = "max-speed"`
  - `QUANT_DISPLAY: Final[dict[Quantization, str]]` — labels amigáveis para exibição no terminal
  - `class StageStatus(str, Enum)`: `PENDING = "—"`, `RUNNING = "⠸"`, `DONE = "✔"`, `FAILED = "✘"`
  - `@dataclass class StageResult`: `label: str`, `status: StageStatus = PENDING`, `duration_s: float = 0.0`; propriedade `duration_display: str` formata como `"2m 14s"`
  - `@dataclass(frozen=True) class GPUInfo`: `name: str`, `sm_version: int`, `vram_total_gb: float`, `vram_free_gb: float`, `driver_version: str`
  - `class UnsupportedGPUError(Exception): pass`
  - `class InsufficientVRAMError(Exception): pass`
  - Função `_vram_needed_gb(params_billions: float, quant: Quantization) -> float`
    - `bytes_per_param = 1.0` se `FP8|INT8`, `0.5` se `INT4_AWQ|FP4`
    - `return params_billions * 1e9 * bytes_per_param / 1e9 * 1.3`
  - Função `recommend_quantization(gpu: GPUInfo, params_billions: float) -> tuple[Quantization, QualityLabel, str]`
    - Implementa a cascata completa descrita na seção "Lógica de Quantização Automática"
    - Levanta `UnsupportedGPUError` se `gpu.sm_version < 80`
    - Levanta `InsufficientVRAMError` com mensagem `f"Modelo {params_billions:.1f}B params não cabe na {gpu.name} ({gpu.vram_free_gb:.1f}GB livres). Considere um modelo menor."` se nenhum formato couber
    - Retorna `(quantization, label, rationale_str)`

- [ ] T007 Criar `src/rtxmodelforge/shared/config.py`
  - `from __future__ import annotations`
  - `CONFIG_DIR: Final[Path] = Path.home() / ".rtxmodelforge"`
  - `class Settings(BaseSettings)` com:
    - `model_config = SettingsConfigDict(env_prefix="RTXFORGE_", toml_file=str(CONFIG_DIR / "config.toml"), extra="ignore")`
    - `hf_token: str | None = Field(default=None, validation_alias="HF_TOKEN")`
    - `engines_dir: Path = Field(default=CONFIG_DIR / "engines")`
    - `model_post_init`: `self.engines_dir.mkdir(parents=True, exist_ok=True)`
  - `def get_settings() -> Settings` — retorna `Settings()`
  - `def save_hf_token(token: str) -> None`
    - `CONFIG_DIR.mkdir(parents=True, exist_ok=True)`
    - `CONFIG_DIR.chmod(0o700)` — apenas dono pode ler/escrever/listar
    - Lê config existente se houver com `tomllib.loads`
    - Atualiza `{"hf_token": token}` e grava com `tomli_w.dumps`
    - `(CONFIG_DIR / "config.toml").chmod(0o600)` — após gravar, restringe permissões

- [ ] T008 Criar `src/rtxmodelforge/shared/gpu.py`
  - `from __future__ import annotations`
  - Função `detect_gpu() -> GPUInfo | None`
    - Tenta via pynvml:
      - `pynvml.nvmlInit()`
      - `handle = pynvml.nvmlDeviceGetHandleByIndex(0)`
      - `name = pynvml.nvmlDeviceGetName(handle)`
      - `major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)` → `sm_version = major * 10 + minor`
      - `mem = pynvml.nvmlDeviceGetMemoryInfo(handle)` → `vram_total_gb = mem.total / 1e9`, `vram_free_gb = mem.free / 1e9`
      - `driver = pynvml.nvmlSystemGetDriverVersion()`
    - Em `pynvml.NVMLError`: fallback para `nvidia-smi` via subprocess:
      - `nvidia-smi --query-gpu=name,compute_cap,memory.total,memory.free,driver_version --format=csv,noheader,nounits`
      - Parse: `compute_cap` no formato `"8.9"` → `sm_version = int("8") * 10 + int("9")`
    - Retorna `None` se ambos falham

**Verificação após Phase 2**:
```bash
python -c "
from rtxmodelforge.shared.types import recommend_quantization, GPUInfo, Quantization
gpu = GPUInfo('RTX 4090', 89, 24.0, 22.0, '560.0')
print(recommend_quantization(gpu, 8.0))
"
```

---

### Phase 3: Doctor & Login Slices

**Status**: ⬜ Pending
**Objective**: `rtxforge doctor` e `rtxforge login` funcionais.
**Dependencies**: Phase 2

**Tasks**:

- [ ] T009 Criar `src/rtxmodelforge/features/doctor/checks.py`
  - `from __future__ import annotations`
  - `@dataclass class CheckResult`: `label: str`, `passed: bool`, `detail: str`, `blocking: bool = True`
  - `check_nvidia_driver() -> CheckResult` — `nvidia-smi --query-gpu=driver_version --format=csv,noheader`; `passed = version >= 560` (mínimo Ubuntu 24.04 + CUDA 13.1); blocking
  - `check_cuda_toolkit() -> CheckResult` — `nvcc --version`; parse `"release X.Y"`; `passed = major >= 13`; `detail` inclui instrução de instalação se falhar; blocking
  - `check_libopenmpi() -> CheckResult` — `dpkg -s libopenmpi-dev`; `passed = exit_code == 0`; `detail = "sudo apt-get install libopenmpi-dev"` se falhar; blocking
  - `check_gpu() -> CheckResult` — chama `gpu.detect_gpu()` (GPU index 0); `passed = gpu is not None`; exibe nome, SM version e VRAM; se múltiplas GPUs detectadas via `pynvml.nvmlDeviceGetCount() > 1`, inclui em `detail`: `"Multi-GPU detectado ({N} GPUs). V1 usa apenas GPU 0."` como aviso não-bloqueante; blocking
  - `check_sm_support() -> CheckResult` — se GPU detectada, verifica `sm_version >= 80`; `passed = sm_version >= 80`; mensagem clara sobre RTX 20 não suportado; blocking
  - `check_trtllm() -> CheckResult` — `python3 -c "import tensorrt_llm; print(tensorrt_llm.__version__)"`; `blocking = False` (informativo)
  - `check_hf_token() -> CheckResult` — `config.get_settings().hf_token is not None`; `blocking = False`

- [ ] T010 Criar `src/rtxmodelforge/features/doctor/command.py`
  - Executa os 7 checks em sequência com tabela Rich live
  - Colunas: `Status` (✔ verde / ✘ vermelho / ⚠ amarelo), `Check`, `Detalhe`
  - `raise typer.Exit(1)` se qualquer check `blocking=True` falhar
  - Registrar em `main.py`

- [ ] T011 Criar `src/rtxmodelforge/features/login/command.py`
  - `login(token: Annotated[str, typer.Option("--token", prompt=True, hide_input=True)]) -> None`
  - `httpx.get("https://huggingface.co/api/whoami", headers={"Authorization": f"Bearer {token}"}, timeout=10.0)`
  - `200` → `config.save_hf_token(token)`; exibe `✔ Autenticado como: {response.json()['name']}`
  - `401` → `error_console.print("Token inválido.")` + `raise typer.Exit(1)`
  - `httpx.TimeoutException` → mensagem + exit 1
  - Registrar em `main.py`

**Verificação após Phase 3**:
```bash
rtxforge doctor
rtxforge login --token <token>
```

---

### Phase 4: Engines Slice

**Status**: ⬜ Pending
**Objective**: Storage de engines e comandos `rtxforge list` / `rtxforge delete`.
**Dependencies**: Phase 2

**Tasks**:

- [ ] T012 Criar `src/rtxmodelforge/features/engines/types.py`
  - `CURRENT_SCHEMA_VERSION: Final[int] = 1`
  - `class EngineMetadata(BaseModel)` com todos os campos do schema definido acima (incluindo `schema_version`, `quantization_rationale`, `engine_size_gb`)
  - `model_config = ConfigDict(use_enum_values=True)`

- [ ] T013 Criar `src/rtxmodelforge/features/engines/store.py`
  - `METADATA_FILENAME: Final[str] = "engine.json"`
  - `engine_dir(model_id: str, quantization: Quantization) -> Path`
    - `settings.get_settings().engines_dir / model_id / quantization.value`
  - `save_metadata(engine_path: Path, metadata: EngineMetadata) -> None`
    - `engine_path.mkdir(parents=True, exist_ok=True)`
    - Grava `metadata.model_dump_json(indent=2)` em `engine_path / METADATA_FILENAME`
  - `load_metadata(engine_path: Path) -> EngineMetadata | None`
    - Lê e deserializa com `EngineMetadata.model_validate_json()`; `None` se não existe
    - Se `metadata.schema_version != CURRENT_SCHEMA_VERSION`: exibe `[WARNING] engine.json schema v{metadata.schema_version} (atual: v{CURRENT_SCHEMA_VERSION}). Recomenda-se recompilar.` mas retorna metadata normalmente
  - `list_engines() -> list[tuple[Path, EngineMetadata]]`
    - `rglob("engine.json")` sobre `engines_dir`; ordena por `built_at` desc
  - `delete_engine(engine_path: Path) -> None`
    - Verifica `engine.json` existe; `shutil.rmtree(engine_path)`
  - `check_version_compatibility(metadata: EngineMetadata) -> tuple[bool, str]`
    - Compara `metadata.trtllm_version` com `tensorrt_llm.__version__`
  - `class EngineNotFoundError(Exception): pass`

- [ ] T014 Criar `src/rtxmodelforge/features/engines/list_command.py`
  - Tabela Rich: `Modelo`, `GPU`, `SM`, `Formato`, `VRAM`, `Compilado em`, `Path`
  - Registrar em `main.py` como `app.command("list")`

- [ ] T015 Criar `src/rtxmodelforge/features/engines/delete_command.py`
  - Carrega metadata → exibe painel com detalhes → `typer.confirm(..., abort=True)` → `store.delete_engine()`
  - Registrar em `main.py` como `app.command("delete")`

**Verificação após Phase 4**:
```bash
rtxforge list   # "Nenhum engine encontrado"
```

---

### Phase 5: Build Slice

**Status**: ⬜ Pending
**Objective**: `rtxforge build` completo usando LLM API — download → quantização automática → compilação → engine salvo.
**Dependencies**: Phase 4

**Tasks**:

- [ ] T016 Criar `src/rtxmodelforge/features/build/types.py`
  - `from __future__ import annotations`
  - `@dataclass class BuildConfig`:
    - `model_id: str`, `weights_dir: Path`, `gpu_info: GPUInfo`, `quantization: Quantization`, `quality_label: QualityLabel`
    - `rationale: str`, `params_billions: float`, `verbose: bool`
  - `class CompilationError(Exception): pass`
  - `class GatedModelError(Exception): pass`

- [ ] T017 Criar `src/rtxmodelforge/features/build/downloader.py`
  - `download_weights(model_id: str, target_dir: Path, hf_token: str | None, verbose: bool) -> Path`
  - `huggingface_hub.snapshot_download(repo_id=model_id, local_dir=target_dir / "weights", token=hf_token, ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"])`
  - Exibe Rich `Status` spinner durante download
  - `huggingface_hub.errors.GatedRepoError` → re-levanta como `GatedModelError("Configure com: rtxforge login --token <token>")`
  - `huggingface_hub.errors.RepositoryNotFoundError` → `ValueError(f"Modelo não encontrado: {model_id}")`
  - Função `read_params_billions(weights_dir: Path) -> float`
    - Lê `weights_dir / "config.json"` com `json.loads`
    - Tenta campo `"num_parameters"` direto; se ausente, estima via `num_hidden_layers`, `hidden_size`, `intermediate_size`, `num_attention_heads`
    - Lê campo `"model_type"` para gravar em `EngineMetadata.architecture` (informativo apenas — não valida nem rejeita)
    - Se campos insuficientes para estimar: prompt interativo `console.input("Informe o número de parâmetros em bilhões (ex: 8.0 para um modelo 8B): ")` e usa valor fornecido
    - Retorna float em bilhões

- [ ] T018 Criar `src/rtxmodelforge/features/build/engine_builder.py`
  - `from __future__ import annotations`
  - `from tensorrt_llm import LLM`
  - `from tensorrt_llm.llmapi import QuantConfig, QuantAlgo`
  - `_QUANT_TO_ALGO: Final[dict[Quantization, QuantAlgo]]` mapeando:
    - `FP8 → QuantAlgo.FP8`
    - `INT8 → QuantAlgo.INT8`
    - `INT4_AWQ → QuantAlgo.AWQ`
    - `FP4 → QuantAlgo.NVFP4`
  - Função `build_engine(config: BuildConfig, engine_dir: Path) -> Path`
    - Monta `quant_config = QuantConfig(quant_algo=_QUANT_TO_ALGO[config.quantization])`
    - Para FP8 adiciona `kv_cache_quant_algo=QuantAlgo.FP8` (KV cache também nos Tensor Cores)
    - Exibe aviso de tempo antes de instanciar: `"Compilação pode levar 10–30 minutos. Não feche o terminal."`
    - Usa `rich.live.Live` com `refresh_per_second=1` durante o `LLM()` para exibir elapsed time em tempo real
    - Se `config.verbose`: redireciona stdout/stderr do processo para `console.print` linha a linha, exibindo também a última linha do output no live display
    - Instancia `llm = LLM(model=str(config.weights_dir), backend="tensorrt", quant_config=quant_config, tensor_parallel_size=1)`
    - Após compilação: `llm.save(str(engine_dir))` persiste em disco
    - Chama `llm.shutdown()` no `finally` (mesmo em caso de erro)
    - Levanta `CompilationError(str(e))` em caso de exceção
    - Retorna `engine_dir`

- [ ] T019 Criar `src/rtxmodelforge/features/build/pipeline.py`
  - `from __future__ import annotations`
  - Função `run(config: BuildConfig) -> Path`
  - 4 etapas rastreadas com `StageResult`:
    - Etapa 1 `"Baixando pesos"` → `downloader.download_weights()`
    - Etapa 2 `"Lendo configuração do modelo"` → `downloader.read_params_billions()`
    - Etapa 3 `"Compilando engine (pode levar 10–30 min)"` → `engine_builder.build_engine()`
    - Etapa 4 `"Salvando metadata"` → `store.save_metadata()`
  - Helper `_run_stage(idx, label, fn)`: marca `RUNNING`, executa, mede tempo, marca `DONE`/`FAILED`; re-renderiza `stage_table` via `console.print` a cada mudança
  - Em qualquer exceção: marca etapa como `FAILED`, re-levanta
  - `engine_dir = store.engine_dir(config.model_id, config.quantization)`
  - Monta `EngineMetadata` com todos os campos após compilação bem-sucedida

- [ ] T020 Criar `src/rtxmodelforge/features/build/command.py`
  - `build(model_url: Annotated[str, typer.Argument()], gpu: Annotated[str | None, typer.Option("--gpu")] = None, verbose: Annotated[bool, typer.Option("--verbose")] = False) -> None`
  - Normaliza `model_url` → `model_id` (extrai `org/model` de URL HuggingFace se necessário)
  - Detecta GPU via `shared.gpu.detect_gpu()`; erro claro se `None`
  - Download + leitura de `params_billions` antecipada (necessária para recomendação)
  - Verifica se engine já existe: `store.load_metadata(store.engine_dir(model_id, quant))` — se existente, exibe metadata do engine atual e `typer.confirm("Engine já existe. Recompilar? (não = usar engine existente)", default=False)`; se usuário recusa: exibe `summary_panel` com engine existente e `raise typer.Exit(0)`
  - Chama `shared.types.recommend_quantization(gpu_info, params_billions)` → obtém `(quant, label, rationale)`
  - Se houve fallback (formato primário não coube): exibe warning antes do painel: `"[WARNING] {formato_primario} requer {X:.1f}GB, disponível: {Y:.1f}GB. Usando {fallback}."`
  - Exibe `header_panel(model_id, gpu_info.name, quant.value, rationale)` com linha de estimativa de tempo antes de iniciar
  - Constrói `BuildConfig` e chama `pipeline.run(config)`
  - Exibe `summary_panel(engine_path, [f"rtxforge serve {engine_path}", f"rtxforge chat {engine_path}"])`
  - Captura `GatedModelError`, `UnsupportedGPUError`, `InsufficientVRAMError`, `CompilationError` → `error_console.print(...)` + `raise typer.Exit(1)`
  - Registrar em `main.py`

**Verificação após Phase 5** (requer GPU + TensorRT-LLM):
```bash
rtxforge build meta-llama/Llama-3.1-8B --verbose
rtxforge list
```

---

### Phase 6: Serve & Chat Slices

**Status**: ⬜ Pending
**Objective**: `rtxforge serve` e `rtxforge chat` sobre engines compilados.
**Dependencies**: Phase 5

**Tasks**:

- [ ] T021 Criar `src/rtxmodelforge/features/serve/command.py`
  - `serve(engine_path: Annotated[Path, typer.Argument()], port: Annotated[int, typer.Option("--port")] = 8000, host: Annotated[str, typer.Option("--host")] = "127.0.0.1") -> None`
  - Carrega metadata com `store.load_metadata(engine_path)`; erro se `None`
  - Chama `store.check_version_compatibility(metadata)`; se incompatível exibe `[WARNING]` amarelo
  - Exibe painel informativo: modelo, GPU, SM version, formato, `http://{host}:{port}/v1/chat/completions`
  - Se `host == "0.0.0.0"`: exibe `[WARNING]` sobre exposição na rede local e solicita `typer.confirm("Continuar?", abort=True)`
  - Executa (blocking): `subprocess.run(["trtllm-serve", "serve", str(engine_path), "--tokenizer", metadata.model_id, "--host", host, "--port", str(port)])`
  - Captura `KeyboardInterrupt` → `console.print("\n[bold]Servidor encerrado.[/bold]")` sem traceback
  - Registrar em `main.py`

- [ ] T022 Criar `src/rtxmodelforge/features/chat/command.py`
  - `chat(engine_path: Annotated[Path, typer.Argument()], system_prompt: Annotated[str, typer.Option()] = "You are a helpful assistant.", max_tokens: Annotated[int, typer.Option()] = 512) -> None`
  - Valida engine_path + check de versão (igual ao serve)
  - Com Rich `Status` spinner `"Carregando engine..."` instancia `llm = LLM(model=str(engine_path))`
  - Instancia `tokenizer = AutoTokenizer.from_pretrained(metadata.model_id)`
  - Lê `max_seq_len` do engine: `metadata.max_seq_len` se presente, senão default `4096`
  - `history: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]`
  - Helper `_estimate_tokens(history: list[dict]) -> int` — estimativa rápida: `sum(len(m["content"].split()) * 1.3 for m in history)` (tokens ≈ palavras × 1.3)
  - Loop:
    - `user_input = console.input("[bold cyan]Você:[/bold cyan] ")`
    - `"/exit"` → break; `"/clear"` → `history = [history[0]]` + `console.clear()`; continue
    - Append `{"role": "user", "content": user_input}`
    - **Gerenciamento de contexto:** enquanto `_estimate_tokens(history) > max_seq_len - max_tokens`:
      - Remove `history[1]` (a mensagem mais antiga, preservando `history[0]` = system prompt)
      - Ao remover a primeira mensagem: exibe `[WARNING] Histórico truncado para caber no contexto ({max_seq_len} tokens).`
      - O aviso é exibido apenas uma vez por rodada de truncagem
    - Formata o histórico com `prompt = tokenizer.apply_chat_template(history, tokenize=False, add_generation_prompt=True)`
    - `output = llm.generate([prompt], SamplingParams(max_tokens=max_tokens))`
    - `response = output[0].outputs[0].text`
    - Append `{"role": "assistant", "content": response}`
    - `console.print(f"[bold green]Assistente:[/bold green] {response}\n")`
  - `llm.shutdown()` no finally; captura `KeyboardInterrupt` limpo
  - Registrar em `main.py`

**Verificação após Phase 6**:
```bash
rtxforge serve ~/.rtxmodelforge/engines/meta-llama/Llama-3.1-8B/fp8
curl http://localhost:8000/v1/models
rtxforge chat ~/.rtxmodelforge/engines/meta-llama/Llama-3.1-8B/fp8
```

---

### Phase 7: Install Script

**Status**: ⬜ Pending
**Objective**: `install.sh` para Ubuntu 24.04 instalando todas as dependências incluindo TensorRT-LLM.
**Dependencies**: Phase 6

**Tasks**:

- [ ] T023 Criar `install.sh` na raiz
  - `#!/usr/bin/env bash` + `set -euo pipefail`
  - Cores ANSI: `RED`, `GREEN`, `YELLOW`, `NC`; funções `info()`, `success()`, `warn()`, `error()`
  - **Verificações pré-requisito** (exit 1 com mensagem clara):
    - `[[ "$(uname -s)" == "Linux" ]]`
    - `command -v nvidia-smi` — GPU NVIDIA presente
    - `python3 --version | grep -E "3\.(1[2-9])"` — Python 3.12+
    - Verifica SM version via `nvidia-smi --query-gpu=compute_cap --format=csv,noheader`; se `< 8.0` exibe aviso de GPU não suportada
  - **Dependências do sistema**:
    ```bash
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip git libopenmpi-dev
    ```
  - **Criação do diretório com permissões corretas**:
    ```bash
    mkdir -p ~/.rtxmodelforge
    chmod 700 ~/.rtxmodelforge
    ```
  - **Criação do virtualenv**: `python3 -m venv ~/.rtxmodelforge/venv`
  - **PyTorch com CUDA 13.0**:
    ```bash
    ~/.rtxmodelforge/venv/bin/pip install \
      torch==2.10.0 torchvision \
      --index-url https://download.pytorch.org/whl/cu130
    ```
  - **TensorRT-LLM** (avisa que pode levar vários minutos e ~3GB):
    ```bash
    info "Instalando TensorRT-LLM (~3GB, pode levar 5-10 minutos)..."
    ~/.rtxmodelforge/venv/bin/pip install --ignore-installed pip setuptools wheel
    ~/.rtxmodelforge/venv/bin/pip install tensorrt_llm
    ```
  - **RTX Model Forge**:
    ```bash
    ~/.rtxmodelforge/venv/bin/pip install git+https://github.com/OWNER/rtxmodelforge.git
    ```
  - **Wrapper** `~/.local/bin/rtxforge`:
    ```bash
    #!/bin/bash
    source "$HOME/.rtxmodelforge/venv/bin/activate"
    exec rtxforge "$@"
    ```
  - **PATH**: adiciona `export PATH="$HOME/.local/bin:$PATH"` ao `~/.bashrc` e `~/.zshrc` se não presente (verifica com `grep -qF` antes)
  - **Mensagem final**:
    ```
    ✔ RTX Model Forge instalado!

    Abra um novo terminal e execute:
      rtxforge doctor        # verificar ambiente
      rtxforge --help        # ver todos os comandos
    ```

**Verificação após Phase 7**:
```bash
bash install.sh
# Novo terminal:
rtxforge --version
rtxforge doctor
```

---

## Master Checklist

### Phase 1: Project Foundation
- [ ] T001 Criar `pyproject.toml`
- [ ] T002 Criar estrutura VSA + `__init__.py`
- [ ] T003 Criar `src/rtxmodelforge/shared/console.py`
- [ ] T004 Criar `src/rtxmodelforge/shared/panels.py`
- [ ] T005 Criar `src/rtxmodelforge/main.py`
- [ ] Verificação: `pip install -e ".[dev]" && rtxforge --help`

### Phase 2: Shared Infrastructure
- [ ] T006 Criar `src/rtxmodelforge/shared/types.py`
- [ ] T007 Criar `src/rtxmodelforge/shared/config.py`
- [ ] T008 Criar `src/rtxmodelforge/shared/gpu.py`
- [ ] Verificação: `recommend_quantization` retorna correto por SM version

### Phase 3: Doctor & Login Slices
- [ ] T009 Criar `src/rtxmodelforge/features/doctor/checks.py`
- [ ] T010 Criar `src/rtxmodelforge/features/doctor/command.py`
- [ ] T011 Criar `src/rtxmodelforge/features/login/command.py`
- [ ] Verificação: `rtxforge doctor && rtxforge login --token <token>`

### Phase 4: Engines Slice
- [ ] T012 Criar `src/rtxmodelforge/features/engines/types.py`
- [ ] T013 Criar `src/rtxmodelforge/features/engines/store.py`
- [ ] T014 Criar `src/rtxmodelforge/features/engines/list_command.py`
- [ ] T015 Criar `src/rtxmodelforge/features/engines/delete_command.py`
- [ ] Verificação: `rtxforge list`

### Phase 5: Build Slice
- [ ] T016 Criar `src/rtxmodelforge/features/build/types.py`
- [ ] T017 Criar `src/rtxmodelforge/features/build/downloader.py`
- [ ] T018 Criar `src/rtxmodelforge/features/build/engine_builder.py`
- [ ] T019 Criar `src/rtxmodelforge/features/build/pipeline.py`
- [ ] T020 Criar `src/rtxmodelforge/features/build/command.py`
- [ ] Verificação: `rtxforge build <modelo> --verbose`

### Phase 6: Serve & Chat Slices
- [ ] T021 Criar `src/rtxmodelforge/features/serve/command.py`
- [ ] T022 Criar `src/rtxmodelforge/features/chat/command.py`
- [ ] Verificação: `rtxforge serve <engine>` + `rtxforge chat <engine>`

### Phase 7: Install Script
- [ ] T023 Criar `install.sh`
- [ ] Verificação: `bash install.sh` em Ubuntu 24.04 limpo
