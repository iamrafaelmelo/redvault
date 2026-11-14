---
slug: own-oidc-openid-connect
title: "OpenID Connect: ID Token, validação e falhas de implementação"
category: api-security
summary: "O que o OIDC acrescenta ao OAuth 2.0, quais claims o ID Token precisa ter, o que o RP deve validar e quais erros de validação são exploráveis."
tags: "oidc openid-connect oauth jwt id-token nonce iss aud"
owasp: "API2:2023, API9:2023"
severity: high
references:
  - OpenID Connect Core 1.0 (errata set 2) | https://openid.net/specs/openid-connect-core-1_0.html
  - OpenID Connect Discovery 1.0 | https://openid.net/specs/openid-connect-discovery-1_0.html
  - OAuth 2.0 Authorization Framework — RFC 6749 | https://www.rfc-editor.org/rfc/rfc6749
  - OAuth 2.0 Bearer Token Usage — RFC 6750 | https://www.rfc-editor.org/rfc/rfc6750
  - OAuth 2.0 Security Best Current Practice — RFC 9700 | https://www.rfc-editor.org/rfc/rfc9700
  - OWASP WSTG — Testing for OAuth Weaknesses | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/05-Testing_for_OAuth_Weaknesses
---

OpenID Connect 1.0 é definido na especificação oficial como "uma camada de
identidade simples sobre o OAuth 2.0". O próprio documento diz por que ela
existe: o OAuth 2.0 define como obter e usar access tokens, mas **não** define
método padrão para fornecer informação de identidade — sem um perfil, o OAuth
2.0 "não é capaz de fornecer informação sobre a autenticação de um End-User".

Esse é o ponto que separa os dois protocolos, e é onde nasce a maior parte dos
erros de pentest: **OAuth 2.0 é autorização; OIDC é autenticação**. Testar login
SSO exige entender OIDC, não só "JWT bem formado".

## O que o OIDC adiciona

- O scope `openid` na Authorization Request. Segundo a especificação, se ele não
  estiver presente, **o comportamento é totalmente não especificado**.
- Um **ID Token**: um JWT com as claims sobre o evento de autenticação.
- O **UserInfo Endpoint**: recurso protegido que devolve claims sobre o usuário
  quando recebe um access token.
- Terms: o servidor que autentica é **OpenID Provider (OP)**; o cliente que
  confia é **Relying Party (RP)**.

## Os fluxos

A especificação define três, selecionados pelo `response_type`:

| `response_type` | Fluxo |
| --- | --- |
| `code` | Authorization Code Flow |
| `id_token` | Implicit Flow |
| `id_token token` | Implicit Flow |
| `code id_token` | Hybrid Flow |
| `code token` | Hybrid Flow |
| `code id_token token` | Hybrid Flow |

A tabela normativa da spec descreve as propriedades. Para segurança, o Code Flow
é o único em que "tokens não são revelados ao User Agent" e "o cliente pode ser
autenticado". O Implicit Flow não tem essa propriedade e não permite refresh
token. A RFC 9700 (OAuth 2.0 Security BCP) desencoraja o Implicit Flow, e a
especificação do OIDC já o marca como legado de fato.

Na prática de teste, isso significa: uma aplicação que usa `response_type=token`
expõe o access token no fragmento da URL, no histórico do navegador e em logs de
referer. É uma observação de projeto, não necessariamente uma vulnerabilidade
explorável — mas com XSS ou com uma extensão maliciosa, o token vaza.

## Claims obrigatórias do ID Token

Segundo a seção 2 da spec:

| Claim | Obrigatória | Conteúdo |
| --- | --- | --- |
| `iss` | sim | Issuer Identifier, URL https case-sensitive, sem query/fragment |
| `sub` | sim | identificador do usuário, único e nunca reatribuído no Issuer, até 255 ASCII |
| `aud` | sim | precisa conter o `client_id` do RP |
| `exp` | sim | expiração; a spec exige que a data atual seja anterior |
| `iat` | sim | momento de emissão |
| `auth_time` | condicional | obrigatória quando `max_age` é pedido ou é Essential Claim |
| `nonce` | condicional | se veio na request, o OP **deve** devolver igual |
| `acr` | opcional | Authentication Context Class Reference |
| `amr` | opcional | métodos de autenticação usados |
| `azp` | opcional | authorized party, o client a quem o token foi emitido |

A spec também estabelece:

- ID Tokens **devem** ser assinados com JWS, e podem ser assinados e depois
  cifrados com JWE (Nested JWT).
- `alg: none` em ID Token **não deve** ser usado, exceto no caso específico de
  Response Type que não retorna ID Token e o cliente pediu `none` no registro.
- ID Tokens **não devem** usar `x5u`, `x5c`, `jku` ou `jwk` no header; chaves
  são combinadas antes via Discovery e Registration.

## O que o RP precisa validar (e o que acontece se não validar)

A lista de validação está na seção 3.1.3.7 (Code Flow) e é o roteiro de teste:

1. **Assinatura.** Validar com a chave do OP vinda do JWKS. Um RP que confia no
   `alg` do header e aceita `none`, HS256 com chave pública como segredo, ou
   chave de `jku` externa, permite forjar identidade. Esse é o mesmo defeito da
   trilha de JWT, aplicado a OIDC.
2. **`iss`.** Se o RP aceita token de qualquer issuer, você registra um OP próprio
   e emite token para o e-mail da vítima. O SSO "funciona", mas você autentica.
3. **`aud`.** Se o RP não checa que `aud` contém seu `client_id`, um token
   emitido para outra aplicação do mesmo OP é aceito. É o clássico "token
   confusion" entre clientes do mesmo provedor.
4. **`exp` e `iat`.** Token expirado aceito é reuso indefinido. A spec permite
   pequena tolerância de clock, não zero validação.
5. **`nonce`.** Se o cliente enviou `nonce` e não confere o retorno, o ID Token
   vira reutilizável. O `nonce` é o mecanismo anti-replay do ID Token.
6. **`state`.** É recomendado, não obrigatório, e serve a CSRF. Junto com PKCE,
   é o que impede login CSRF e troca de código por atacante.

Falhas em 1–4 são de **autenticação**. Falhas em 5–6 são de **integridade de
sessão**. Trate como classes diferentes no relatório.

## Falhas comuns do lado do OP e da configuração

- **`redirect_uri` com matching frouxo.** A spec exige que o `redirect_uri` da
  request **case exatamente** um dos redirecionamentos registrados (Simple
  String Comparison, RFC 3986 §6.2.1). Curingas, `/callback*`, ou validação por
  prefixo permitem desvio de código para domínio do atacante. Teste: registrar
  (mentalmente) as variações de path, subdomínio, `@`, `%2f`, `//`, porta e
  fragmento que "passam" no cliente.
- **`prompt=none` e `prompt` combinados incorretamente.** A spec diz que `none`
  com qualquer outro valor é erro. Se o OP aceita `prompt=none login`, o fluxo
  silencioso pode ser forçado em contexto inesperado.
- **Token de acesso sem audience.** Access token opaco que vale para todo mundo.
- **Session fixation no callback.** O código é trocado mas a sessão pré-existente
  não é rotacionada.
- **Discovery público expondo endpoints internos.** `/jwks.json` é público por
  natureza; mas `authorization_endpoint` apontando para host interno ou HTTP é
  sinal de configuração errada.

## Como testar, sem inventar

1. Capture a request de autorização: `client_id`, `redirect_uri`, `scope`,
   `state`, `nonce`, `response_type`, `response_mode`.
2. Verifique se o `state` muda por login e se é ligado ao cookie. Repita o
   mesmo `state` e veja o comportamento.
3. Capture o ID Token do callback e decodifique o header e as claims (sem
   validar assinatura no início: só para ler). Compare `aud` com o `client_id`,
   `iss` com o issuer do Discovery, `nonce` com o enviado.
4. Teste `redirect_uri` variantes e registre quais mudam o destino do `code`.
5. Teste reuso: pegue um token válido e use após `exp`.
6. Teste troca de issuer/audience: se houver dois clients registrados no mesmo
   OP, tente o token do outro.

O teste só vira achado quando você prova o efeito: sessão de outro usuário,
acesso a recurso protegido, ou bypass de consentimento.

## Correção

- Validação estrita no RP, usando biblioteca mantida, com lista de algoritmos
  permitidos fixa.
- `redirect_uri` exato, sem curinga; recusar no servidor, não no front.
- Obrigatoriedade de `nonce` e `state`, com correlação em cookie de sessão.
- Usar Code Flow com PKCE; evitar Implicit e Hybrid.
- Rotacionar a sessão no callback e no logout.

## O que este documento não cobre

Detalhes de cada OP comercial (Okta, Entra ID, Keycloak), SAML (protocolo
diferente, com suas próprias armadilhas como XSW), e configuração de
frameworks de RP. As fontes utilizadas aqui estão todas listadas e são a
referência viva.