# Observability Checklist — RTX Model Forge V1

> Avalia a qualidade dos requisitos de visibilidade do sistema para o usuário durante operação.

- [ ] CHK041 O `stage_table` exibe tempo decorrido em tempo real (live update) ou apenas ao final de cada etapa? O requisito especifica qual comportamento? [Clarity]
- [ ] CHK042 O tempo total de compilação é exibido ao final do build (soma das 4 etapas)? [Completeness]
- [x] CHK043 O progresso interno do `LLM()` durante compilação é exposto ao usuário em modo padrão (sem `--verbose`)? Se não, o usuário vê apenas um spinner sem progresso percentual durante 20 min? [Coverage] ✅ Resolvido: `rich.live.Live` com elapsed time atualizado a cada segundo; `--verbose` exibe última linha de stdout do LLM()
- [ ] CHK044 O `--verbose` está especificado como flag global (aplicável a todos os comandos) ou por subcomando (apenas `build`)? [Clarity]
- [ ] CHK045 Em caso de `CompilationError`, o plano especifica quais informações do erro são exibidas ao usuário (mensagem resumida? log completo? path para log file?)? [Completeness]
- [ ] CHK046 O `rtxforge doctor` exibe versões exatas instaladas (não apenas pass/fail) para CUDA, driver, TensorRT-LLM e Python? [Completeness]
- [ ] CHK047 O warning de incompatibilidade de versão do engine (`trtllm_version` mismatch) tem formato especificado — exatamente onde aparece e qual estilo visual (cor, ícone)? [Clarity]
- [ ] CHK048 A estimativa de tempo restante durante compilação (ex: "~15 min restantes") está especificada ou foi explicitamente descartada? [Gap]
- [ ] CHK049 O tamanho do engine compilado é exibido ao final do build (útil para usuários com disco limitado)? [Coverage]
- [ ] CHK050 Erros de rede durante download (timeout, conexão recusada, rate limit HuggingFace) têm mensagens de observabilidade distintas ou são tratados genericamente? [Edge Case]
