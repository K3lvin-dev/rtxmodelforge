# UX Checklist — RTX Model Forge V1

> Avalia a qualidade dos requisitos de experiência do usuário no CLI.

- [ ] CHK011 Todos os subcomandos (`build`, `serve`, `chat`, `list`, `delete`, `login`, `doctor`) têm flags e argumentos completamente especificados no plano? [Completeness]
- [ ] CHK012 A experiência durante os 10–30 minutos de compilação está especificada: quais informações são exibidas, em qual frequência, e o que o usuário vê se ficar idle? [Clarity]
- [x] CHK013 O `header_panel` exibe o `rationale` de quantização (ex: `"FP8: 4ª geração Tensor Cores — 2× INT8, ~99% qualidade"`) antes de iniciar — o requisito de mostrar isso ao usuário está explícito? [Completeness] ✅ Resolvido: `header_panel` inclui `rationale` e linha de estimativa de tempo
- [x] CHK014 O comportamento de fallback de quantização (ex: FP8 não cabe, caindo para INT8) tem requisito de comunicação ao usuário — aviso visível antes ou durante o build? [Coverage] ✅ Resolvido: warning explícito com VRAM necessária vs disponível antes do `header_panel`
- [ ] CHK015 As mensagens de erro para cada `Exception` do build slice (`GatedModelError`, `UnsupportedArchitectureError`, `UnsupportedGPUError`, `InsufficientVRAMError`, `CompilationError`) estão especificadas com tom e formato? [Completeness]
- [ ] CHK016 O comportamento do `rtxforge chat` para modelos que não aplicam chat template (base models vs instruct models) está especificado? [Edge Case]
- [ ] CHK017 Os comandos especiais do chat (`/exit`, `/clear`) estão documentados no `--help` do subcomando `chat`? [Clarity]
- [ ] CHK018 O `rtxforge list` com zero engines tem output especificado (mensagem amigável com instrução de próximo passo)? [Edge Case]
- [ ] CHK019 O `rtxforge delete` com path inválido ou não-engine tem mensagem de erro especificada? [Edge Case]
- [ ] CHK020 O comportamento de `--verbose` está especificado: exatamente o quê é impresso (logs crus do `LLM()`? subprocess output? ambos?) [Clarity]
- [ ] CHK021 A experiência de primeiro uso (usuário sem nenhuma configuração, sem HF token, sem GPU validada) tem um fluxo recomendado documentado no `--help` ou `doctor`? [Coverage]
- [x] CHK022 O tempo estimado de compilação é comunicado ao usuário antes de iniciar (ex: "Compilação pode levar 10–30 minutos dependendo do modelo")? [Clarity] ✅ Resolvido: exibido no `header_panel` e no início da etapa de compilação em `engine_builder.py`
