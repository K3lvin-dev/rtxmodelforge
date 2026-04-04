# Data Checklist — RTX Model Forge V1

> Avalia a qualidade dos requisitos de modelos de dados, persistência e contratos de schema.

- [x] CHK031 O schema do `EngineMetadata` tem versão explícita (campo `schema_version`)? Sem versionamento, mudanças futuras quebram `engine.json` existentes silenciosamente. [Edge Case] ✅ Resolvido: `schema_version: int = 1` adicionado; `load_metadata()` emite warning em mismatch
- [ ] CHK032 O path do engine para `model_id = "meta-llama/Llama-3.1-8B"` é especificado como `engines_dir/meta-llama/Llama-3.1-8B/fp8/` — o comportamento de `Path / "meta-llama/Llama-3.1-8B"` no Linux está validado (cria subdiretórios corretamente)? [Clarity]
- [ ] CHK033 A estimativa de `params_billions` via `config.json` está especificada para o caso em que `num_parameters` não existe no arquivo (fórmula de estimativa ou fonte alternativa)? [Completeness]
- [ ] CHK034 O campo `vram_used_gb` do `EngineMetadata` está especificado como medido (VRAM antes vs depois da compilação? estimativa pela fórmula?) [Clarity]
- [ ] CHK035 O schema do `config.toml` está documentado (campos aceitos, tipos, valores padrão)? [Completeness]
- [ ] CHK036 O comportamento de `load_metadata()` para `engine.json` corrompido ou com schema inválido está especificado (retorna `None`? levanta exceção? tenta recuperar)? [Edge Case]
- [x] CHK037 A unicidade do engine: o que acontece se o usuário rodar `rtxforge build` para o mesmo modelo + GPU + quantização duas vezes? Sobrescreve silenciosamente? Pergunta confirmação? [Coverage] ✅ Resolvido: detecta engine existente → exibe metadata → `typer.confirm("Recompilar?", default=False)`
- [ ] CHK038 Os arquivos temporários criados durante a compilação (weights baixados, checkpoints intermediários) têm localização e política de limpeza especificadas (cleanup em falha? em sucesso?) [Completeness]
- [ ] CHK039 O campo `architecture` no `EngineMetadata` tem valores válidos especificados (`"llama"`, `"mistral"`) e a fonte (campo `model_type` do `config.json`)? [Clarity]
- [ ] CHK040 O `engines_dir` configurável via `RTXFORGE_ENGINES_DIR` env var tem comportamento especificado quando o diretório não existe (cria automaticamente? erro?) [Edge Case]
