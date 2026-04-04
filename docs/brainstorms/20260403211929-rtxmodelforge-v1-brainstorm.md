# RTX Model Forge — V1 Brainstorm

**Data:** 2026-04-03  
**Status:** Decisões tomadas — pronto para `/pwf-plan`

---

## 1. What We're Building

RTX Model Forge é uma ferramenta CLI open source para Linux que permite a qualquer pessoa com uma NVIDIA RTX moderna compilar e rodar modelos de linguagem no máximo desempenho do hardware, sem precisar entender CUDA, quantização ou pipelines de compilação.

O usuário informa um link do HuggingFace, informa sua GPU, e executa um único comando. A ferramenta cuida de todo o pipeline TensorRT-LLM — download de pesos, conversão de checkpoint, compilação do engine otimizado — e entrega um modelo rodando 2-4x mais rápido que ferramentas genéricas como Ollama.

O público primário são usuários Linux com GPUs RTX que conhecem modelos open source e querem o máximo do seu hardware sem se tornar engenheiros de ML. O público secundário são desenvolvedores que querem prototipar aplicações sobre modelos locais compilados.

---

## 2. Current State

Repositório completamente novo. Nenhum código, nenhuma infraestrutura, nenhum documento técnico existente.

- **Backend:** inexistente
- **Frontend/CLI:** inexistente
- **Pipelines:** inexistentes
- **Brainstorms anteriores:** nenhum

---

## 3. Architecture & Infrastructure

### Onde a lógica vive

Aplicação Python monolítica executada como CLI. Sem servidor central, sem cloud, sem backend remoto. Tudo roda localmente na máquina do usuário.

```
rtxforge build <model_url> --gpu <gpu_model>
rtxforge serve <engine_path>
rtxforge chat <engine_path>
```

### Stack técnica

| Camada | Escolha |
|--------|---------|
| Linguagem | Python 3.10+ |
| CLI framework | Typer |
| Output visual | Rich (progress bars, tabelas, painéis) |
| Compilação LLM | TensorRT-LLM |
| Download de modelos | `huggingface_hub` |
| Servidor de inferência | `trtllm-serve` (OpenAI-compatible REST) |
| Detecção de GPU | `pynvml` / `nvidia-smi` |

### Pipeline de compilação (ordem de execução)

```
1. Detectar GPU → VRAM disponível
2. Recomendar quantização baseada na VRAM
3. Download dos pesos (HuggingFace)
4. Conversão de checkpoint (formato TRT-LLM)
5. Compilação do engine TensorRT-LLM
6. Validação do engine gerado
7. Entrega: engine em disco + instruções de uso
```

### Quantização automática por VRAM

| VRAM disponível | Recomendação automática | Label para usuário |
|----------------|------------------------|--------------------|
| ≥ 16GB | FP16 | Máxima qualidade |
| 8–15GB | INT8 | Balanceado |
| < 8GB | INT4 (AWQ) | Máxima velocidade |

Usuário pode sobrescrever com `--quality [max-quality|balanced|max-speed]`.

### Pós-compilação

Dois modos disponíveis após compilar um engine:

1. **`rtxforge serve <engine>`** — Sobe servidor REST OpenAI-compatible em `localhost:8000`. Compatível com Open WebUI, Continue.dev, Cursor, `openai` SDK Python.
2. **`rtxforge chat <engine>`** — Chat interativo no terminal via Rich.

### Distribuição

- **Método:** Bash install script (`install.sh`)
- **Hospedagem:** GitHub Releases
- **Instalação:** `curl -sSL https://github.com/user/rtxmodelforge/releases/latest/download/install.sh | bash`
- O script instala dependências do sistema, cria virtualenv isolado, expõe `rtxforge` no PATH

### SO e requisitos

- **SO suportado v1:** Linux (Ubuntu 22.04+ como target primário)
- **GPU suportada v1:** NVIDIA RTX 4060 – 4090
- **Arquiteturas de modelo v1:** Llama e Mistral families
- **Pré-requisitos:** CUDA Toolkit, driver NVIDIA ≥ 525

---

## 4. Integration Impact

Projeto novo — sem impacto em sistemas existentes.

**Dependências externas que precisam funcionar:**
- HuggingFace Hub (download de pesos — pode exigir token para modelos gated)
- TensorRT-LLM (instalação local pelo install script)
- NVIDIA drivers e CUDA toolkit (pré-existentes na máquina do usuário)

---

## 5. Key Decisions

1. ✅ **DECIDED:** Plataforma v1 é Linux CLI only — sem GUI desktop, sem Windows, sem macOS
2. ✅ **DECIDED:** Stack CLI é Python + Typer + Rich
3. ✅ **DECIDED:** Pós-compilação entrega engine + servidor REST OpenAI-compatible + chat CLI
4. ✅ **DECIDED:** Distribuição via Bash install script no GitHub Releases (sem .deb, sem pip público)
5. ✅ **DECIDED:** Quantização auto-detecta por VRAM com override via opções simples (`max-quality`, `balanced`, `max-speed`)
6. ✅ **DECIDED:** Arquiteturas suportadas na v1: Llama e Mistral families
7. ✅ **DECIDED:** GPUs suportadas na v1: RTX 4060–4090
8. ⚠️ **OPEN:** Modelos gated no HuggingFace (ex: Llama 3) exigem token de autenticação — precisa decidir como o usuário configura isso (`rtxforge login`? variável de ambiente `HF_TOKEN`?)
9. ⚠️ **OPEN:** Onde os engines compilados são armazenados por padrão — `~/.rtxmodelforge/engines/`? Configurável?
10. ⚠️ **OPEN:** Estrutura de comandos do CLI — subcomandos (`build`, `serve`, `chat`, `list`) e flags completas

---

## 6. Open Questions

1. **Autenticação HuggingFace:** Como o usuário configura o token para modelos gated? Opções: `rtxforge login`, `HF_TOKEN` env var, arquivo `~/.rtxmodelforge/config.toml`
2. **Gerenciamento de engines:** Onde ficam os engines compilados? Precisa de um `rtxforge list` e `rtxforge delete`?
3. **Versioning de engines:** Se o usuário atualizar o TensorRT-LLM, engines antigos precisam ser recompilados — como avisar sobre incompatibilidade?
4. **Logs e debug:** Compilação pode demorar 20+ min — quanta verbosidade expor por padrão? Flag `--verbose`?
5. **Teste de sanidade pós-compilação:** Rodar uma inferência rápida após compilar para validar que o engine funciona?

---

## 7. Next Steps

- Rodar `/pwf-plan docs/brainstorms/20260403211929-rtxmodelforge-v1-brainstorm.md` para gerar o plano de implementação
- Durante o planejamento, resolver as Open Questions 1-3 (impactam estrutura de comandos e sistema de arquivos)
- Verificar versão mínima do TensorRT-LLM compatível com RTX 4060–4090 antes de começar a implementação
- Definir estrutura do repositório (monorepo Python com `pyproject.toml`)
