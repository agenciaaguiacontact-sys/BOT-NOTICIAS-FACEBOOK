# 📰 Facebook News Bot - Aconteceu Hoje

Bot profissional que roda automaticamente no GitHub Actions a cada 10 minutos para manter a página **Aconteceu Hoje** sempre atualizada com as últimas notícias.

## 🚀 Funcionalidades
1.  **Monitoramento Real**: Busca notícias recentes no portal SFY.
2.  **IA Sensacionalista**: Usa o Google Gemini para criar ganchos de alto impacto.
3.  **Design Automático**: Gera imagens quadradas (1:1) com tarjas "URGENTE".
4.  **Comentários Automáticos**: Posta o link da notícia no primeiro comentário para aumentar o alcance.
5.  **Automação na Nuvem**: Roda 100% no GitHub sem depender do seu computador.

---

## 🛠️ Configuração de Segredos (GitHub Secrets)

Para o robô funcionar, os seguintes segredos devem estar configurados em **Settings > Secrets and variables > Actions**:

| Secret | Descrição |
| :--- | :--- |
| `FB_PAGE_ID` | `1021302557732355` (Aconteceu Hoje) |
| `FB_TOKEN` | Page Access Token de longa duração |
| `GEMINI_API_KEY` | Chave da API do Google Gemini |
| `FB_APP_ID` | ID do seu App na Meta |
| `FB_APP_SECRET` | Chave secreta do seu App na Meta |
| `FB_USER_TOKEN` | Token de usuário para renovação automática |
| `SFY_EMAIL` | Seu e-mail de login no SFY |
| `SFY_PASSWORD` | Sua senha do SFY |

---

## 📅 Agendamento
O robô está configurado no arquivo `.github/workflows/facebook_news_bot.yml` para disparar a cada **10 minutos**. 

Se desejar alterar, edite a linha `cron: '*/10 * * * *'`.

---

## 🎨 Personalização Visual
As cores e fontes das imagens podem ser ajustadas diretamente no arquivo `bot.py` na função `adicionar_texto_premium`.

---

## ⚠️ Manutenção
O robô possui um sistema de **renovação automática** de tokens (`auth_manager.py`), o que minimiza a necessidade de intervenção manual. Se as postagens pararem, verifique a aba **Actions** no seu repositório para ver os logs de erro.
