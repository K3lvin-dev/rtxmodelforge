# RTX Model Forge

CLI para compilar e rodar LLMs localmente em GPUs NVIDIA RTX usando TensorRT-LLM com prioridade Tensor Core first.

## Sobre

RTX Model Forge substitui a experiência do ChatRTX da NVIDIA com uma abordagem otimizada para Tensor Cores. O sistema seleciona automaticamente o melhor modo de aceleração (FP4, FP8, INT8, INT4) baseado na sua GPU e VRAM disponível.

## Requisitos de Hardware

- **GPU**: NVIDIA RTX serie 3000 ou superior (Ampere, Ada Lovelace, Blackwell)
- **VRAM**: 8GB minimo (12GB+ recomendado para modelos maiores)
- **Driver NVIDIA**: versao 525.x ou superior
- **CUDA**: 12.x ou superior
- **Sistema Operacional**: Linux (Ubuntu 24.04+ recomendado)

## Instalacao

### Desenvolvimento

```bash
# Clonar o repositorio
git clone https://github.com/K3lvin-dev/rtxmodelforge.git
cd rtxmodelforge

# Instalar com uv (recomendado)
uv sync

# Ou com pip
pip install -e ".[dev]"
```

### Dependencias do Sistema

```bash
# Ubuntu/Debian
sudo apt-get install libopenmpi-dev

# Verificar instalacao
rtxforge doctor
```

## Uso

### Fluxo Principal

```bash
# 1. Verificar saude do sistema
rtxforge doctor

# 2. Compilar engines otimizados para sua GPU
rtxforge prepare meta-llama/Llama-3.1-8B

# 3. Rodar chat interativo
rtxforge run meta-llama/Llama-3.1-8B

# 4. Servir via API (compativel OpenAI)
rtxforge serve caminho/para/engine
```

### Comandos Disponiveis

- `rtxforge doctor` - Diagnostico completo do sistema (GPU, driver, CUDA, dependencias)
- `rtxforge prepare <model_id>` - Compila engines chat e serve otimizados para sua GPU
- `rtxforge run <model_id>` - Abre chat interativo com o modelo
- `rtxforge serve <engine_path>` - Sobe servidor REST compativel com OpenAI
- `rtxforge list` - Lista engines compilados
- `rtxforge delete <engine_path>` - Remove engine compilado
- `rtxforge login` - Configura token do HuggingFace para modelos restritos

### Interface Web (UI)

O projeto inclui uma interface web React/TypeScript:

```bash
cd ui
npm install
npm run dev
```

Acesse `http://localhost:5173` para o cockpit visual com metricas em tempo real.

## Arquitetura

### Pipeline de Build

1. **Download** - Baixa pesos do HuggingFace
2. **Analise** - Le config.json e estima parametros
3. **Planejamento** - Calcula KV cache, batch size, sequencia maxima
4. **Compilacao** - Compila engines chat (batch=1) e serve (batch dinamico)
5. **Metadata** - Salva configuracao para reutilizacao

### Selecao de Aceleracao

O sistema seleciona automaticamente o melhor caminho:

- **Blackwell (RTX 50)**: FP4 (maxima velocidade) ou FP8 (qualidade)
- **Ada Lovelace (RTX 40)**: FP8 ou INT8/INT4 AWQ
- **Ampere (RTX 30)**: INT8 ou INT4 AWQ

Veja `docs/architecture-flows.md` para diagramas detalhados.

## Desenvolvimento

### Testes

```bash
# Backend (Python)
pytest tests/ --cov=rtxmodelforge

# Frontend (TypeScript)
cd ui && npm test
```

### Lint e Formatacao

```bash
# Backend
ruff check src/
mypy src/

# Frontend
cd ui && npm run lint
cd ui && npm run typecheck
```

### CI/CD

GitHub Actions roda automaticamente em push/PR:
- Backend: ruff, mypy, pytest com cobertura
- Frontend: biome lint, typecheck, build

## Documentacao Adicional

- `DESIGN.md` - Design system e principios de UI
- `PRODUCT.md` - Personas, principios de produto
- `docs/architecture-flows.md` - Diagramas de fluxo (Mermaid)

## Contribuindo

1. Fork o repositorio
2. Crie uma branch para sua feature (`git checkout -b feature/nome`)
3. Commit com mensagens semanticas (`feat:`, `fix:`, `docs:`, etc.)
4. Push para a branch (`git push origin feature/nome`)
5. Abra um Pull Request

## Licenca

Este projeto esta sob desenvolvimento ativo. Licenca a ser definida.
