# Conhecimento: Permissões Meta Graph API (Comentários e Engajamento)

**Última atualização:** 2026-04-08
**Versão documentada:** v22.0+
**Fonte:** [Permissions Reference - Facebook Login](https://developers.facebook.com/docs/facebook-login/permissions/)

## Permissões Necessárias para Comentários

A permissão `pages_read_comments` **NÃO EXISTE** nas versões atuais da API do Facebook. Ela foi consolidada em permissões de "engajamento" mais amplas.

### 1. `pages_read_engagement` (Substituta para leitura)
- **O que faz:** Permite que o app leia o conteúdo da Página (posts, fotos, vídeos) e, crucialmente, os **comentários** feitos nesses conteúdos. 
- **Uso:** Necessário se o bot precisa monitorar o que as pessoas estão escrevendo para decidir se responde ou não.
- **Acesso:** Requer "Acesso Avançado" (Advanced Access) para funcionar com usuários que não são administradores do App.

### 2. `pages_manage_engagement` (Necessária para o Bot responder)
- **O que faz:** Permite que o app crie, edite e exclua comentários, curta posts e gerencie outras interações de engajamento em nome da Página.
- **Uso:** É a permissão que o `bot.py` atual usa no endpoint `/{post-id}/comments`.
- **Acesso:** Sem "Acesso Avançado", o bot só conseguirá comentar em posts feitos por desenvolvedores do próprio App Meta.

## Onde encontrar no Dashboard do Meta for Developers

1. Vá para o seu App no [Meta Developers](https://developers.facebook.com/).
2. No menu lateral, clique em **App Settings** -> **Permissions and Features** (ou **Configurações do App** -> **Permissões e Recursos**).
3. Na barra de busca, digite `engagement`.
4. Você encontrará:
   - `pages_read_engagement`
   - `pages_manage_engagement`
5. Clique no botão para solicitar o nível de acesso necessário (geralmente mudar de "Standard Access" para "Advanced Access").

## Erros Comuns

- **Erro #200 (Permissions error):** Acontece se o token não tiver `pages_manage_engagement` ou se o app estiver em modo de desenvolvimento e tentando interagir com posts de usuários externos.
- **Erro "O campo comments não existe":** Acontece se você tentar ler comentários sem a permissão `pages_read_engagement`.

## MCPs Disponíveis
Não há um MCP oficial específico para permissões Meta, mas a documentação da Graph API é a fonte definitiva.
