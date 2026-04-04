# Clarifications — RTX Model Forge V1 CLI Implementation

## Source Plan
- `docs/plans/20260403212246-rtxmodelforge-v1-plan.md`

---

## Session 2026-04-03

### Q1: Comportamento do `LLM()` com `engine_dir`
- **Recommendation:** Verificar na documentação antes de assumir comportamento de cache automático
- **Research:** Código fonte em `tensorrt_llm/llmapi/llm.py` confirma: `LLM()` base herda de `_TorchLLM` e NÃO tem parâmetro `engine_dir`. Apenas `_TrtLLM` (backend TensorRT) tem método `save(engine_dir)`.
- **Final Answer:** Dois passos explícitos: `LLM(model=..., backend="tensorrt", quant_config=...)` + `llm.save(str(engine_dir))`. Para carregar: `LLM(model=str(engine_dir))`.
- **Impact on Plan:** T018 (`engine_builder.py`) reescrito — remove `engine_dir` do construtor, adiciona chamada explícita a `llm.save()`. `tensor_parallel_size=1` fixo no construtor.

### Q2: Overflow de contexto no chat
- **Recommendation:** Truncar com aviso (B)
- **Final Answer:** B — truncar mensagens mais antigas preservando `history[0]` (system prompt); exibir `[WARNING] Histórico truncado para caber no contexto (N tokens).` uma vez por rodada de truncagem.
- **Impact on Plan:** T022 (`chat/command.py`) atualizado com helper `_estimate_tokens()` e loop de truncagem antes de cada `llm.generate()`.

### Q3: Multi-GPU no V1
- **Recommendation:** Single-GPU apenas (A)
- **Final Answer:** A — `tensor_parallel_size=1` fixo, GPU index 0 sempre. Doctor avisa se múltiplas GPUs detectadas (não-bloqueante).
- **Impact on Plan:** Decisões técnicas atualizadas; T009 (`doctor/checks.py`) inclui aviso de multi-GPU; T018 (`engine_builder.py`) usa `tensor_parallel_size=1` explícito.

### Q4: Como medir `vram_used_gb`
- **Recommendation:** Estimativa estática (A)
- **Final Answer:** A — `vram_used_gb = params_billions × bytes_per_param × 1.3`. Simples e suficiente; medir VRAM em runtime é frágil.
- **Impact on Plan:** `EngineMetadata.vram_used_gb` comentado como estimativa estática; nenhuma medição em runtime necessária.

### Q5: `params_billions` quando `num_parameters` ausente + escopo de modelos
- **Recommendation:** Prompt interativo (B)
- **Final Answer:** B — quando campos insuficientes para estimativa, solicitar valor ao usuário via `console.input()`. Adicionalmente: escopo expandido para **todos os modelos compatíveis com TensorRT-LLM** (não apenas Llama/Mistral) — DeepSeek, Qwen, Phi, Gemma, etc. A LLM API lida com diferenças de arquitetura automaticamente.
- **Impact on Plan:** `read_params_billions()` remove validação de `model_type`; `UnsupportedArchitectureError` removido; campo `architecture` em `EngineMetadata` é informativo (valor de `model_type`); documentação de escopo atualizada.

---

## Coverage Summary

| Categoria | Status | Notas |
|-----------|--------|-------|
| Functional scope e success criteria | ✅ Claro | Escopo expandido para todos modelos TRT-LLM compatíveis |
| Domain/data model e lifecycle | ✅ Claro | `EngineMetadata` com `schema_version`, `vram_used_gb` como estimativa |
| UX/interaction flows | ✅ Claro | Context truncation com aviso, fallback de quantização comunicado |
| NFRs (security, performance) | ✅ Claro | Permissões de arquivo, single-GPU, `tensor_parallel_size=1` |
| Integration boundaries | ✅ Claro | `backend="tensorrt"` + `llm.save()` explícito |
| Edge cases e concorrência | ✅ Claro | Context overflow, rebuild de engine existente, multi-GPU |
| Terminology consistency | ✅ Claro | `engine_dir`, `params_billions`, `sm_version` consistentes |
| Completion signals | ✅ Claro | `summary_panel` com comandos sugeridos após build |
