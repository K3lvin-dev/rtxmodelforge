# RTX Model Forge UI

Interface web React/TypeScript para o RTX Model Forge - um cockpit visual inspirado em nvtop/htop para monitorar e controlar GPUs NVIDIA RTX.

## Design System

Veja `../DESIGN.md` para o design system completo:
- Paleta de cores OKLCH perceptualmente uniforme
- Tipografia: Inter (UI) + JetBrains Mono (dados)
- Regras: flush-mount (sem shadows), mono-for-data, chroma-zero surfaces

## Desenvolvimento

### Instalacao

```bash
npm install
```

### Servidor de Desenvolvimento

```bash
npm run dev
```

Acesse `http://localhost:5173`

### Build para Producao

```bash
npm run build
```

Os arquivos compilados vao para `dist/`.

### Preview da Build

```bash
npm run preview
```

## Scripts Disponiveis

- `npm run dev` - Servidor de desenvolvimento Vite
- `npm run dev:legacy` - Servidor Node.js legado (server.js)
- `npm run build` - Build de producao (TypeScript + Vite)
- `npm run preview` - Preview da build de producao
- `npm run lint` - Verificar lint com Biome
- `npm run lint:fix` - Corrigir erros de lint automaticamente
- `npm run format` - Formatar codigo com Biome
- `npm run typecheck` - Verificar tipos TypeScript

## Estrutura de Diretorios

```
ui/
├── src/
│   ├── components/     # Componentes React
│   │   ├── App.tsx
│   │   ├── Header.tsx
│   │   ├── HardwarePanel.tsx
│   │   ├── OperationsPanel.tsx
│   │   ├── ChatPanel.tsx
│   │   ├── Layout.tsx
│   │   └── Diagnostic.tsx
│   ├── hooks/          # Custom hooks
│   │   ├── useSystemState.ts
│   │   ├── useKeyboard.ts
│   │   └── useTheme.ts
│   ├── lib/            # Logica de CLI (simulacao)
│   │   └── cli.ts
│   ├── types/          # Tipos TypeScript
│   │   ├── gpu.ts
│   │   ├── engine.ts
│   │   ├── system.ts
│   │   ├── chat.ts
│   │   ├── operations.ts
│   │   └── theme.ts
│   ├── styles/         # CSS (design system)
│   │   └── index.css
│   └── main.tsx        # Entry point
├── public/             # Assets estaticos
├── dist/               # Build de producao (gerado)
├── biome.json          # Configuracao Biome (lint + format)
├── vite.config.ts      # Configuracao Vite
└── package.json
```

## Componentes Principais

### HardwarePanel
Metricas em tempo real da GPU:
- VRAM (uso, total, percentual)
- Temperatura
- Utilizacao (GPU load)
- Clocks (core, memoria)

### OperationsPanel
Lista de operacoes com atalhos de teclado:
- **P** - Prepare (compilar engines)
- **S** - Serve (iniciar servidor)
- **C** - Chat (abrir chat)
- **R** - Run (executar)
- **D** - Doctor (diagnostico)
- **I** - List (listar engines)
- **L** - Login (HuggingFace)
- **X** - Delete (remover engine)

### ChatPanel
Interface de chat com:
- Streaming de tokens em tempo real
- Metricas de throughput (tokens/sec)
- Historico de mensagens
- Botao de abortar

### Diagnostic
Estados de diagnostico:
- NoGpuDiagnostic - GPU nao detectada
- NoEnginesDiagnostic - Nenhum engine compilado
- FirstRunDiagnostic - Primeira execucao

## Estado Atual

A UI esta em modo de **simulacao** (`SIMULATE = true` em `lib/cli.ts`).
Os dados sao gerados localmente para desenvolvimento standalone.

### Integracao com Backend

Para conectar com o backend real:
1. Implementar comunicacao CLI via subprocess ou API
2. Remover flag `SIMULATE` em `lib/cli.ts`
3. Implementar polling de estado real da GPU
4. Conectar operacoes aos comandos CLI (`rtxforge prepare`, etc.)

## Tecnologias

- **React 19.1** - UI library
- **TypeScript 5.7** - Type safety
- **Vite 6.0** - Build tool e dev server
- **Biome** - Lint e formatacao (substitui ESLint + Prettier)
- **CSS puro** - Design system custom (sem frameworks)

## Atalhos de Teclado

A navegacao e 100% por teclado:
- `P` - Prepare
- `S` - Serve
- `C` - Chat (toggle)
- `R` - Run
- `D` - Doctor
- `I` - List (Informacao)
- `L` - Login
- `X` - Delete
- `Esc` - Fechar chat
- `Ctrl+R` - Refresh

## Contribuindo

1. Siga o design system em `DESIGN.md`
2. Mantenha tipagem TypeScript rigorosa
3. Teste em modo escuro e claro
4. Garanta acessibilidade (ARIA labels, navegacao por teclado)
5. Rode `npm run lint` e `npm run typecheck` antes de commitar
