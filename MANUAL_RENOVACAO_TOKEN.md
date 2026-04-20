# Manual de Renovação do Token Meta (Facebook)

Este guia explica como renovar os tokens de acesso do seu bot de notícias quando eles expirarem (geralmente a cada 60 dias).

> [!IMPORTANT]
> O bot utiliza dois segredos principais no GitHub: `FB_USER_TOKEN` (Token de Usuário) e `FB_TOKEN` (Token de Página). É essencial atualizar ambos ou garantir que o Token de Página obtido seja permanente.

---

## 📋 Pré-requisitos
1. Acesso à conta do [Meta for Developers](https://developers.facebook.com/).
2. O **App ID** e **App Secret** do seu aplicativo (já configurados no GitHub).

---

## 🛠️ Passo 1: Obter Novo Token de Usuário (Curta Duração)

1. Vá para o [Messenger Graph API Explorer](https://developers.facebook.com/tools/explorer/).
2. No menu à direita:
   - **Meta App**: Selecione o seu aplicativo do bot.
   - **User or Page**: Selecione "User Access Token".
   - **Permissions**: Garanta que as permissões `pages_manage_posts`, `pages_read_engagement` e `public_profile` estejam marcadas.
3. Clique em **Generate Access Token**.
4. Faça o login e autorize as permissões se solicitado.
5. Copie o token gerado (é uma string longa).

---

## ⚙️ Passo 2: Transformar em Token de Longa Duração e Obter Token de Página

Você pode fazer isso facilmente usando o script que já existe no seu projeto.

### Opção A: Usando o script local (Recomendado)
1. No seu computador, abra o arquivo `.env`.
2. Cole o token que você copiou no passo anterior na variável `FB_USER_TOKEN`.
3. Abra um terminal na pasta do projeto e execute:
   ```powershell
   python obter_page_token.py
   ```
4. O script irá:
   - Listar suas páginas.
   - Encontrar a página correta pelo ID.
   - Gerar um arquivo chamado `found_token.txt` com o **Token de Página**.

### Opção B: Manualmente via Debugger
1. Vá para o [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/).
2. Cole o token de usuário e clique em **Debug**.
3. Clique em **Extend Access Token** para transformá-lo em um token de 60 dias.
4. Use esse token estendido na URL abaixo para pegar o token da página:
   `https://graph.facebook.com/v22.0/me/accounts?access_token=SEU_TOKEN_ESTENDIDO`

---

## 🚀 Passo 3: Atualizar o GitHub Secrets

Agora que você tem os novos tokens, precisa salvá-los no GitHub para que o bot automatizado continue funcionando.

1. Acesse o seu repositório no GitHub.
2. Vá em **Settings** (Configurações) > **Secrets and variables** > **Actions**.
3. Você verá uma lista de segredos. Clique no ícone de lápis (editar) nos seguintes:
   - `FB_USER_TOKEN`: Cole o novo token de usuário (o de longa duração).
   - `FB_TOKEN`: Cole o token de página obtido no Passo 2 (este costuma ser permanente).
4. Clique em **Update secret**.

---

## 🔍 Como verificar se o token é permanente?

1. Cole o `FB_TOKEN` (Token de Página) no [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/).
2. Olhe o campo **Expires** (Expira em):
   - Se disser **Never** (Nunca), você nunca mais precisará trocar este token, a menos que mude sua senha do Facebook.
   - Se mostrar uma data (60 dias), você terá que repetir este processo quando chegar perto dessa data.

---

> [!TIP]
> Marque na sua agenda um lembrete para daqui a 55 dias, caso o seu token de página não apareça como "Never". Se ele for "Never", você só precisará renovar se algo parar de funcionar!
