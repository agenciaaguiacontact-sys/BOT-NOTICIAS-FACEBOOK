# Conhecimento: GitHub Actions para Bots Python

**Última atualização:** 2026-04-09
**Fonte:** https://docs.github.com/en/actions

---

## Secrets

### Como configurar (via GH CLI — mais rápido)
```bash
# Subir TODOS os secrets do .env de uma vez:
gh secret set -f .env

# Ou setar individual:
gh secret set FB_TOKEN --body "valor_aqui"
```

### Como usar no workflow
```yaml
env:
  FB_TOKEN: ${{ secrets.FB_TOKEN }}
```

### Regras importantes
- Nomes: apenas letras, números e underscore
- Não podem começar com `GITHUB_` ou número
- Secrets são mascarados automaticamente nos logs

---

## Schedule (Cron)

```yaml
on:
  schedule:
    - cron: '*/10 * * * *'  # A cada 10 minutos
```

> ⚠️ **GOTCHA:** O GitHub pode atrasar o schedule em até 1h em períodos de alta demanda.
> Use `workflow_dispatch` para testes confiáveis.

---

## Persistência entre Execuções

O runner é **efêmero** — nenhum arquivo sobrevive entre execuções.

### Solução: Git Commit de volta ao repo

```yaml
- name: Salvar estado
  run: |
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git add posted_ids.json last_title.txt 2>/dev/null || true
    if git diff --cached --quiet; then
      echo "Sem mudanças"
    else
      git commit -m "chore: estado do bot [skip ci]"
      git push
    fi
```

> **[skip ci]** na mensagem de commit evita loop infinito de workflows.

### Permissão necessária no job
```yaml
permissions:
  contents: write
```

---

## Playwright no Ubuntu (Linux)

```bash
# Instalar navegador com todas as dependências do SO:
python -m playwright install --with-deps chromium
```

> Sem `--with-deps`, o Playwright falha no Ubuntu por falta de libs do sistema.

---

## workflow_dispatch (Gatilho Manual)

```yaml
on:
  workflow_dispatch:
```

- Permite rodar manualmente pelo painel: **Actions → Workflow → Run workflow**
- Útil para testes antes de confiar no schedule

---

## Lições Aprendidas (Bot Notícias Facebook)

- **SFY retorna 403** para downloads diretos de imagem via `requests` — solução: baixar dentro da sessão autenticada do Playwright via `page.request.get(url)`
- **auth_manager.py** com lógica de renovação automática causa problemas no cloud — simplificar para ler diretamente de `os.environ`
- O `.env` deve estar no `.gitignore` — secrets vão para o GitHub via `gh secret set -f .env`
- `posted_ids.json` e `last_title.txt` devem ser commitados de volta ao repo para persistência
