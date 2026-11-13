---
slug: jwt
title: "Segurança de JWT: assinaturas, claims e gestão de chaves"
category: auth
difficulty: medium
summary: "Entenda o que um JWT de fato prova, teste o tratamento de algoritmo e chave, e evite tratar claims decodificadas como dados confiáveis."
tags: [jwt, jws, hmac, algorithm-confusion, key-management]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 110
---

# Segurança de JWT: assinaturas, claims e gestão de chaves

Um JSON Web Token é um contêiner de claims. Na forma JWS comum, ele tem três partes base64url:

```text
header.payload.signature
```

O header nomeia o algoritmo e o key ID; o payload carrega as claims; a assinatura liga o header e o payload codificados a uma chave. Um JWT **não é criptografado** por padrão. Qualquer um que o possua consegue ler as claims.

## O que o servidor precisa verificar

Um servidor que aceita um JWT precisa:

1. Interpretar a serialização compacta com segurança.
2. Selecionar a chave de verificação a partir de configuração confiável, não de valores `jku`, `x5u` ou `kid` controlados pelo atacante.
3. Impor o algoritmo esperado; nunca deixar o token escolhê-lo.
4. Verificar a assinatura sobre o header e o payload codificados exatos.
5. Validar `exp`, `nbf`, `iat`, `iss`, `aud` e quaisquer claims da aplicação.
6. Rejeitar tokens com tipos inesperados ou claims obrigatórias ausentes.
7. Checar revogação ou estado de sessão para ações de alto valor.

A RFC 7519 define as claims; a RFC 7515 define o JWS. [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519) [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515)

## Modos de falha comuns

### `alg: none`

Algumas bibliotecas aceitavam tokens sem assinatura com `"alg":"none"`. Bibliotecas modernas rejeitam, mas parsers customizados talvez não. Teste apenas se a implementação parecer customizada; um token decodificado não é evidência.

### Segredo HMAC fraco

HS256 usa um segredo compartilhado. Se o segredo é uma palavra de dicionário ou está no código, um atacante assina claims arbitrárias. Um lab local pode usar uma chave deliberadamente fraca; sistemas reais devem usar um segredo de alta entropia vindo de um secret manager.

Testar uma chave fraca conhecida é um exercício legítimo de lab. Não assuma que uma chave é fraca porque "parece curta"; verifique assinando e observando a aceitação.

### Confusão de algoritmo

Um servidor configurado para RS256 pode aceitar HS256 e verificar com a chave pública como segredo HMAC. A chave pública é pública, então o atacante assina. A correção é fixar o algoritmo e usar tipos de chave separados.

### Injeção em `kid`

Se `kid` seleciona um arquivo ou uma chave no banco, valores controlados pelo atacante podem causar path traversal, SQL injection ou seleção de uma chave previsível. Trate `kid` como índice em um conjunto confiável de chaves, nunca como um path.

### `jku` / `x5u`

Esses headers apontam para key sets. Se o servidor os busca sem allowlist, um atacante pode fornecer o próprio JWKS e assinar um token válido. Também é um vetor de SSRF.

### Confiança nas claims

Uma assinatura válida só prova que o emissor assinou as claims. Ela não prova:

- Que o usuário ainda tem o papel da claim.
- Que o token não foi roubado.
- Que o `sub` aponta para uma conta ativa.
- Que o `aud` corresponde a este serviço.

Para ações privilegiadas, cheque a autorização atual server-side.

## Decodificar versus verificar

Decodificar é trivial:

```bash
python3 - <<'PY'
import base64, json
token = "eyJ..."
payload = token.split(".")[1]
print(json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))))
PY
```

Nunca confunda isso com verificação. Um payload que diz `"role":"admin"` é apenas dado até a assinatura ser checada com uma chave confiável.

## Fluxo de teste

1. Capture um token e decodifique header/payload.
2. Identifique o algoritmo, a origem da chave e a validação de claims.
3. Teste expiração e tratamento de `nbf` com um token de vida curta.
4. Teste adulteração da assinatura: mude uma claim e mantenha a assinatura. Espere rejeição.
5. Se a chave for conhecida/fraca no lab, forje um token e confirme a aceitação.
6. Teste `kid`, `jku`, `x5u` apenas contra o lab; eles podem disparar requests de saída.
7. Verifique se logout/troca de senha revoga o token.
8. Verifique validação de audience e issuer entre serviços.

O material de JWT do PortSwigger cobre confusão de algoritmo e tratamento de `kid`. [PortSwigger — JSON Web Token attacks](https://portswigger.net/web-security/jwt)

## Recomendações de design

- Use uma biblioteca mantida com padrões seguros.
- Fixe algoritmos por emissor; não aceite um algoritmo escolhido pelo token.
- Use chaves assimétricas para verificação distribuída; proteja as chaves privadas.
- Mantenha tokens de vida curta e rotacione refresh tokens.
- Armazene tokens em cookies `HttpOnly` quando possível; evite `localStorage` para sessões de alto valor.
- Valide todas as claims e mapeie `sub` para um principal ativo e autorizado.
- Mantenha uma estratégia de revogação (session ID, denylist ou TTL curto).
- Nunca coloque segredos em claims; elas são legíveis.

## Checklist de teste

- [ ] Decodifique header e payload; identifique algoritmo e claims
- [ ] Verifique que a adulteração da assinatura é rejeitada
- [ ] Teste `alg: none` apenas se suspeitar de parsing customizado
- [ ] Teste segredo HMAC fraco no lab
- [ ] Verifique fixação de algoritmo e separação de tipos de chave
- [ ] Revise o tratamento de `kid`, `jku`, `x5u`
- [ ] Valide `exp`, `nbf`, `iss`, `aud`, `sub`
- [ ] Verifique revogação em logout/troca de senha
- [ ] Confirme que tokens não ficam em storage legível sem necessidade

## Referências

- [RFC 7519 — JSON Web Token (JWT)](https://www.rfc-editor.org/rfc/rfc7519)
- [RFC 7515 — JSON Web Signature (JWS)](https://www.rfc-editor.org/rfc/rfc7515)
- [RFC 8725 — JSON Web Token Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [PortSwigger — JWT attacks](https://portswigger.net/web-security/jwt)
- [CWE-347 — Improper Verification of Cryptographic Signature](https://cwe.mitre.org/data/definitions/347.html)