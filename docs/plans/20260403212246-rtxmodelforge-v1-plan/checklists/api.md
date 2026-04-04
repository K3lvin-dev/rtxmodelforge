# API Checklist — RTX Model Forge V1

> Avalia a qualidade dos requisitos relacionados à API REST servida pelo `trtllm-serve`.

- [ ] CHK001 Os endpoints OpenAI-compatible expostos pelo `rtxforge serve` estão listados explicitamente no plano (`/v1/chat/completions`, `/v1/completions`, `/v1/models`, `/health`, `/metrics`)? [Completeness]
- [ ] CHK002 O contrato de request/response de `/v1/chat/completions` está especificado (campos obrigatórios, tipos, formato de `messages`)? [Clarity]
- [ ] CHK003 Os campos de resposta de erro da API (status HTTP, `error.message`, `error.type`) estão especificados para falhas conhecidas (modelo não carregado, token excedido, GPU OOM)? [Completeness]
- [ ] CHK004 O comportamento de streaming (`stream: true`) é suportado? Se sim, o requisito está documentado. Se não, a exclusão está explícita? [Coverage]
- [ ] CHK005 O requisito `--tokenizer` no comando `trtllm-serve serve` está documentado com clareza de quando é obrigatório vs opcional (engine compilado vs modelo HF direto)? [Clarity]
- [ ] CHK006 O `model_id` retornado por `/v1/models` está especificado — usa o nome original do HuggingFace ou o path do engine? [Consistency]
- [x] CHK007 A autenticação da API local está especificada? (explicitamente sem auth, ou com API key configurável?) [Gap] ✅ Resolvido: sem auth explicitamente — bind em `127.0.0.1` por padrão; `0.0.0.0` exige confirmação
- [ ] CHK008 O comportamento do servidor quando a GPU fica sem memória durante inferência (OOM mid-request) está especificado? [Edge Case]
- [ ] CHK009 Limites de `max_tokens` e `max_seq_len` configuráveis via CLI estão mapeados para flags do `trtllm-serve`? [Completeness]
- [ ] CHK010 O CORS está especificado para o servidor local? (relevante para integrações com Open WebUI rodando em browser) [Gap]
