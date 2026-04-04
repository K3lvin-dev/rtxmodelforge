# Security Checklist — RTX Model Forge V1

> Avalia a qualidade dos requisitos de segurança.

- [x] CHK023 As permissões do arquivo `config.toml` estão especificadas? (deve ser `600` — legível apenas pelo dono, pois contém `hf_token`) [Completeness] ✅ Resolvido: `chmod 600` em `save_hf_token()` e `install.sh`
- [ ] CHK024 O `hf_token` é sanitizado antes de ser gravado no `config.toml`? O requisito proíbe logging do token em modo `--verbose`? [Security]
- [ ] CHK025 O `model_url` / `model_id` passado pelo usuário é validado antes de ser usado em subprocess ou paths de arquivo? (risco de path traversal em `engine_dir`) [Edge Case]
- [ ] CHK026 O `engine_path` passado para `rtxforge serve` e `rtxforge delete` é validado como path absoluto dentro de `engines_dir`? (risco de deletar arquivos fora do escopo) [Security]
- [ ] CHK027 O `install.sh` usa `curl | bash` pattern — o requisito especifica verificação de checksum ou assinatura do script antes de executar? [Security]
- [x] CHK028 O servidor REST local (`trtllm-serve`) escuta por padrão em `127.0.0.1` (loopback only)? O requisito proíbe bind em `0.0.0.0` sem aviso explícito? [Security] ✅ Resolvido: default `127.0.0.1`; `--host 0.0.0.0` exige `typer.confirm` com warning explícito
- [ ] CHK029 O `hf_token` não é passado como argumento de linha de comando (visível em `ps aux`) mas sim via variável de ambiente ou arquivo? [Security]
- [x] CHK030 O diretório `~/.rtxmodelforge/` tem permissões especificadas no `install.sh` (ex: `700`)? [Completeness] ✅ Resolvido: `chmod 700 ~/.rtxmodelforge` em `install.sh` e `save_hf_token()`
