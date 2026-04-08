# 📰 SharesForYou → Facebook Auto-Poster Bot

Bot que roda **de graça** no GitHub Actions a cada 1 hora:
1. Faz login no SharesForYou
2. Pega a notícia mais nova
3. Baixa a imagem pelo ícone do olho
4. Gera frase de gancho chamativa com IA (Claude)
5. Sobrepõe o texto na imagem com fundo colorido
6. Publica na sua Página do Facebook com título cortado
7. Adiciona o link da notícia no primeiro comentário

---

## 🚀 Como Configurar (passo a passo)

### 1. Criar repositório no GitHub

1. Acesse [github.com](https://github.com) e crie uma conta gratuita (se não tiver)
2. Clique em **New repository**
3. Nome sugerido: `sharesforyou-bot`
4. Marque **Public** (repositório público = Actions ilimitado e gratuito)
5. Clique **Create repository**
6. Faça upload de todos estes arquivos para o repositório

### 2. Configurar App no Facebook / Meta

> Você precisa de uma **Página do Facebook** (não perfil pessoal) e um **App Meta**.

**a) Criar App Meta:**
1. Acesse [developers.facebook.com](https://developers.facebook.com)
2. Meus Apps → Criar App → Tipo: **Negócios**
3. Adicione o produto **Facebook Login** e **Pages API**

**b) Obter Page Access Token de longa duração:**
1. No [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Selecione seu App
3. Selecione sua Página no campo "User or Page"
4. Adicione as permissões: `pages_manage_posts`, `pages_read_engagement`, `pages_read_user_content`
5. Gere o token → copie o **Page Access Token**

**c) Converter para token de longa duração (60 dias):**
```
https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=SEU_APP_ID
  &client_secret=SEU_APP_SECRET
  &fb_exchange_token=SEU_TOKEN_CURTO
```
Acesse essa URL no navegador. Copie o `access_token` retornado.

**d) Obter Page ID:**
```
https://graph.facebook.com/v21.0/me?access_token=SEU_PAGE_TOKEN&fields=id,name
```

### 3. Obter API Key do Claude (opcional mas recomendado)

1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Crie uma conta e gere uma API Key
3. Tem plano gratuito com créditos iniciais

### 4. Adicionar Secrets no GitHub

No repositório GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

Adicione estes 5 secrets:

| Nome | Valor |
|------|-------|
| `SFY_EMAIL` | robsonvitapm67@gmail.com |
| `SFY_PASSWORD` | Maracana12345@ |
| `FB_PAGE_ID` | ID numérico da sua Página |
| `FB_TOKEN` | Page Access Token de longa duração |
| `ANTHROPIC_API_KEY` | Sua API key do Claude (opcional) |

### 5. Ativar e Testar

1. Vá em **Actions** no repositório
2. Clique no workflow **SharesForYou → Facebook Bot**
3. Clique **Run workflow** para testar manualmente
4. Verifique os logs para ver se funcionou
5. A partir daí roda automaticamente toda hora!

---

## 🔄 Como Funciona o Anti-Duplicata

O arquivo `posted_ids.json` guarda os IDs de todas as notícias já postadas.
A cada execução, o GitHub Actions atualiza esse arquivo com commit automático.
Assim nunca a mesma notícia é postada duas vezes.

---

## 🎨 Personalizar Cores

No arquivo `bot.py`, edite a lista `COLOR_PALETTES` para mudar as cores da faixa de texto na imagem.

---

## ⏰ Mudar Horário de Execução

No arquivo `.github/workflows/bot.yml`, edite a linha:
```yaml
- cron: '0 * * * *'   # toda hora, no minuto 0
```
Exemplos:
- `'0 */2 * * *'` = a cada 2 horas  
- `'0 12 * * *'` = todo dia ao meio-dia UTC (9h Brasília)

---

## ⚠️ Observações Importantes

- O token do Facebook expira em ~60 dias. Precisará renovar manualmente.
- Considere usar um **System User Token** no Meta Business Suite para tokens permanentes.
- O bot posta **1 notícia por hora** (a mais nova ainda não postada).
- Repositório deve ser **público** para Actions gratuito ilimitado.
