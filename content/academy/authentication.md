---
slug: authentication
title: "Autenticação: identidade, sessões e recuperação"
category: auth
difficulty: easy
summary: "Teste login, enumeração, gestão de sessão, recuperação de senha e ciclo de vida de tokens como um sistema, não como formulários isolados."
tags: [authentication, sessions, enumeration, password-reset, cookies]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 30
---

# Autenticação: identidade, sessões e recuperação

Autenticação responde a uma pergunta: *quem é este ator?* Todo caminho que responde a essa pergunta está no escopo — login, cadastro, reset de senha, remember-me, callback OAuth, API key e refresh de sessão. Atacantes raramente precisam quebrar criptografia; eles encontram o caminho que esqueceu uma checagem.

## Construa um mapa de identidade

Liste todas as formas de estabelecer ou alterar uma identidade:

- Login com usuário/senha, incluindo content types alternativos.
- Cadastro e verificação por e-mail/telefone.
- Fluxos de reset e troca de senha.
- Links de convite, impersonação de suporte e "login as" de admin.
- API keys, bearer tokens, JWTs e fluxos OAuth/OIDC.
- Cookies remember-me e sessões de longa duração.

Para cada um, registre o que prova a identidade e o que acontece depois da prova. Um token de reset válido para qualquer conta é um bypass de autenticação, mesmo que o formulário de login seja perfeito.

## Enumeração de usuários

Respostas diferentes para contas existentes e inexistentes vazam um diretório de usuários. Observe:

- Corpo e status code da resposta.
- Tempo de resposta (bcrypt em usuários existentes costuma levar mais tempo).
- Mensagens de "esqueci minha senha".
- Conflitos de cadastro.
- Redação dos erros de login.

Os labs de autenticação do PortSwigger cobrem as variantes comuns, incluindo diferenças sutis de tempo e resposta. [PortSwigger — Authentication](https://portswigger.net/web-security/authentication)

A correção não é só "deixar a mensagem igual". Normalize o tempo quando viável, limite a taxa por conta e por IP, e evite expor a existência de contas por side channels.

## Ataques de senha e desenho de lockout

Credential stuffing usa pares usuário/senha vazados; força bruta tenta adivinhar dentro de um alvo. Ambos são limitados por rate limits, lockouts e MFA. O que testar:

- O limite é por IP, por conta, por dispositivo ou global?
- Ele pode ser contornado com mudanças de caixa, espaços, endpoints alternativos ou multiplexação HTTP/2?
- Um login bem-sucedido limpa as falhas da chave correta?
- Um atacante consegue bloquear todas as contas conhecidas (negação de serviço)?

O NIST SP 800-63B recomenda rate limiting e desaconselha regras de composição e rotação forçada. Também recomenda checar senhas candidatas contra corpora de vazamentos. [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html)

## Gestão de sessão

Um token de sessão é uma credencial bearer. Teste:

- Ele é gerado com CSPRNG e longo o suficiente para resistir a adivinhação?
- Ele é rotacionado após login e mudança de privilégio?
- Ele é invalidado no logout e na troca de senha?
- Os cookies são `HttpOnly`, `Secure` (quando HTTPS) e `SameSite`?
- O token é exposto em URLs, logs ou referrers?
- O servidor aceita um token de outro user agent ou IP? (Binding é defesa em profundidade, não substitui entropia do token.)

A RFC 6265 define a semântica de cookies, incluindo `HttpOnly` e `SameSite`. [RFC 6265 — HTTP State Management Mechanism](https://www.rfc-editor.org/rfc/rfc6265)

Uma falha comum é session fixation: o servidor aceita um identificador de sessão fornecido antes da autenticação e não o rotaciona depois. Sempre compare o cookie pré-login e pós-login.

## Recuperação de senha

Fluxos de recuperação são caminhos de autenticação com impacto maior porque terminam em account takeover. Inspecione:

- Geração do token: aleatório, longo, de uso único, restrito a um usuário?
- Transporte do token: URL, link de e-mail, host header, vazamento por referrer?
- Expiração e invalidação após uso ou troca de senha?
- A página de reset confia em um usuário ou ID escondido?
- O host header ou `X-Forwarded-Host` alteram o link de reset?
- A resposta difere para tokens válidos e inválidos?

O OWASP Forgot Password Cheat Sheet é uma referência precisa de implementação. [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)

## JWT e tokens de API

Questões específicas de JWT estão no artigo de JWT. Na camada de autenticação, lembre:

- Um token não é automaticamente uma sessão. Revogação, rotação e audience importam.
- `alg: none`, segredos HMAC fracos e confusão de algoritmo são falhas de verificação de assinatura.
- Claims como `role`, `tenant`, `sub` e `exp` devem ser validados server-side.
- Nunca confie no header de um token para escolher o algoritmo de verificação.

A RFC 7519 define o conjunto de claims do JWT, não um perfil de segurança. [RFC 7519 — JSON Web Token](https://www.rfc-editor.org/rfc/rfc7519)

## Checklist de teste

- [ ] Enumere todos os endpoints que estabelecem identidade
- [ ] Compare respostas e tempos para usuários válidos/inválidos
- [ ] Teste rate limits por conta, IP e endpoint
- [ ] Verifique rotação de sessão no login e na mudança de privilégio
- [ ] Confirme que logout e troca de senha invalidam sessões antigas
- [ ] Revise flags de cookie e exposição de tokens
- [ ] Teste escopo, expiração, reuso e envenenamento por host header no token de reset
- [ ] Teste bypass de MFA: checagem ausente, manipulação de resposta, caminho de recuperação
- [ ] Confirme autorização server-side depois de cada mudança de identidade

## Referências

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
- [PortSwigger — Authentication](https://portswigger.net/web-security/authentication)
- [NIST SP 800-63B — Digital Identity Guidelines](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [RFC 6265 — HTTP State Management Mechanism](https://www.rfc-editor.org/rfc/rfc6265)