---
slug: api-security
title: "Segurança de API: contratos, objetos e versões"
category: api
difficulty: medium
summary: "Teste APIs como sistemas distribuídos: autorização por objeto, função e tenant, além de deriva de versão, dados excessivos e abuso de schema."
tags: [api, bola, bfla, graphql, versioning, data-exposure]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 100
---

# Segurança de API: contratos, objetos e versões

APIs expõem as mesmas perguntas de autorização que páginas web, mas com mais pontos de entrada e menos feedback da UI. Um único endpoint JSON pode servir clientes mobile, parceiros e internos, cada um com expectativas diferentes. Teste o contrato, não as capturas de tela.

## Inventarie a superfície da API

Colete:

- Paths base e versões (`/api/v1`, `/api/v2`, `/graphql`).
- Métodos por rota (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`).
- Mecanismos de autenticação (cookie, bearer, API key, mTLS).
- Identificadores de objeto e seu escopo.
- Paginação, filtros, ordenação e operações de batch.
- Content types aceitos (`application/json`, form, XML, multipart).
- Formato dos erros e rate limits.

Documentos OpenAPI/Swagger são úteis mas costumam estar desatualizados. Compare a spec com o comportamento observado; endpoints não documentados são comuns.

## Autorização é por objeto, por função, por tenant

O OWASP API Security Top 10 2023 coloca BOLA em primeiro por um motivo. Teste com duas contas de mesmo papel e uma de menor privilégio:

- Troque IDs de objeto em paths, corpos e query strings.
- Tente recursos aninhados (`/teams/1/members/2`).
- Teste endpoints em lote (`POST /users/batch`).
- Teste Node IDs de GraphQL e acesso por campo.
- Teste versões alternativas com checagens mais fracas.

BFLA testa se um usuário sem privilégio de admin consegue chamar uma função de admin diretamente. O servidor precisa impor o papel na função, não só esconder o item de menu.

[OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)

## Exposição excessiva de dados

APIs costumam devolver objetos completos e deixar o cliente esconder campos. Inspecione o JSON em busca de:

- Hashes de senha, tokens de reset, API keys.
- IDs internos, tenant IDs e flags de papel.
- E-mails, telefones e endereços.
- Metadados de debug e stack traces.
- Campos que a UI nunca exibe.

Filtrar no cliente não é proteção. Use schemas/DTOs de resposta que incluam apenas os campos que quem chama pode ver. A entrada A3 do OWASP cobre essa classe. [API3:2023 — Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/)

## Mass assignment em JSON

Um bug comum em APIs: o endpoint de atualização liga todos os campos do JSON.

```http
PATCH /api/users/me
Content-Type: application/json

{"display_name":"Alice","role":"admin","verified":true}
```

Defesas: allowlists explícitas, campos imutáveis, validação de schema que rejeita propriedades desconhecidas e checagens de autorização após o binding. Não confie em um campo só porque a UI nunca o envia.

## Deriva de versão

Versões legadas são uma fonte confiável de controles ausentes:

- `/api/v1/users/{id}` pode omitir a checagem de propriedade adicionada na v2.
- A v2 pode aceitar um header `tenant` que a v1 ignora (ou o contrário).
- Endpoints depreciados podem não ter rate limit nem validação de schema.
- Clientes mobile ainda podem usar uma rota sem manutenção.

Enumere versões a partir do JavaScript, da configuração mobile, da documentação e das mensagens de erro. Teste o mesmo objeto em todas as versões.

## Confusão de content-type e parser

Um endpoint que aceita JSON também pode interpretar form data, XML ou multipart. Teste:

- Enviar JSON para um endpoint de form e vice-versa.
- XML external entities (XXE) onde XML é aceito.
- Chaves duplicadas (`{"role":"user","role":"admin"}`).
- Confusão de tipos (`"1"` vs `1`, arrays vs escalares).
- Chaves de prototype pollution em merges de JSON (`__proto__`, `constructor`).

Parsers diferem; a checagem de segurança pode rodar sobre uma representação enquanto o sink usa outra.

## Rate limits e abuso de recursos

APIs são atrativas para enumeração e força bruta. Verifique:

- Limites por token, IP, conta e endpoint.
- Se os limites se aplicam a operações caras (busca, exportação, redimensionamento de imagem).
- Abuso de paginação (`limit` enorme, offsets profundos).
- Limites de profundidade e complexidade de queries GraphQL.
- Amplificação em endpoints de batch.

Um limite ausente não é sempre uma vulnerabilidade por si, mas pode viabilizar credential stuffing, coleta de dados ou negação de serviço.

## Especificidades de GraphQL

- Introspecção pode revelar o schema; isso não é inerentemente falha, mas ajuda a mirar.
- Teste autorização por campo, não só acesso à query.
- Teste aliases e fragments para agrupar muitos objetos em uma request.
- Teste mutations com IDs de outros usuários.
- Imponha limites de profundidade/complexidade e desabilite introspecção em produção quando apropriado.

## Checklist de teste

- [ ] Monte um inventário de rota/método/auth
- [ ] Testes de autorização de objeto com dois usuários
- [ ] Testes de função com baixo privilégio
- [ ] Revisão de campos de resposta em busca de dados sensíveis
- [ ] Mass assignment na criação/atualização
- [ ] Comparação de versões e rotas depreciadas
- [ ] Confusão de content-type/parser
- [ ] Rate limits, paginação e complexidade de GraphQL
- [ ] Tratamento de erros e vazamento de debug

## Referências

- [OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
- [OWASP API Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/API_Security_Cheat_Sheet.html)
- [PortSwigger — API testing](https://portswigger.net/web-security/api-testing)
- [CWE-639 — Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)
- [RFC 9457 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457)