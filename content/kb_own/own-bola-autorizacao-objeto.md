---
slug: own-bola-autorizacao-objeto
title: "BOLA: autorização em nível de objeto em APIs"
category: api-security
summary: "Por que comparar o user_id do token com o id pedido não resolve BOLA, como diferenciar BOLA de BFLA, como testar com duas contas e o que a OWASP recomenda como correção."
tags: "bola idor api authorization owasp api1 mass-assignment multi-tenant"
cwe: "CWE-639, CWE-285"
owasp: "API1:2023, API5:2023"
severity: high
references:
  - OWASP API Security Top 10 — API1:2023 Broken Object Level Authorization | https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
  - OWASP API Security Top 10 — API5:2023 Broken Function Level Authorization | https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/
  - OWASP Cheat Sheet — Authorization | https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
  - OWASP Cheat Sheet — Authorization Testing Automation | https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Testing_Automation_Cheat_Sheet.html
  - CWE-639: Authorization Bypass Through User-Controlled Key | https://cwe.mitre.org/data/definitions/639.html
  - CWE-285: Improper Authorization | https://cwe.mitre.org/data/definitions/285.html
---

BOLA (*Broken Object Level Authorization*) é a API1:2023 no OWASP API Security
Top 10 — o risco mais prevalente da lista. A definição do OWASP é precisa:
a falha ocorre em endpoints que **recebem um ID de objeto** e não validam se o
usuário autenticado tem permissão sobre aquele objeto específico. O ID pode ser
inteiro sequencial, UUID, nome ou qualquer string.

## O erro conceitual mais comum

O texto da OWASP é explícito ao afirmar que **comparar o user ID da sessão com
o parâmetro de ID vulnerável não é uma solução suficiente**. Isso cobre só um
subconjunto dos casos. As razões:

1. Objetos raramente pertencem a um usuário só. Uma fatura pertence à empresa, e
   a empresa tem vários usuários com papéis diferentes.
2. Hierarquia existe: gerente vê tudo do time, analista vê o próprio. Comparar
   `token.sub == obj.owner_id` erra quando o objeto é de outro membro e você é o
   gerente.
3. Delegação e compartilhamento existem: um documento pode ter sido compartilhado
   com seu grupo, e a comparação simples o bloqueia (falso positivo) enquanto
   outra rota mais permissiva o libera (o furo real).
4. O ID pode estar num campo diferente do `owner_id`: `tenant_id`, `org_id`,
   `parent_id`, `account_no`, header `X-Tenant`.

A correção correta é consultar a **política de autorização** sobre
`(sujeito, ação, objeto)`, centralizada no servidor, e aplicar em toda função que
use entrada do cliente para acessar registro no banco.

## BOLA não é BFLA

A confusão é frequente e muda o relatório:

| | BOLA (API1) | BFLA (API5) |
| --- | --- | --- |
| O que falha | permissão sobre **o objeto** | permissão sobre **a função/rota** |
| Como aparece | você acessa a rota normalmente, mas informa o id de outro | você acessa uma rota que não deveria existir para seu papel |
| Exemplo | `GET /api/invoices/1042` devolve fatura de outro | `DELETE /api/admin/users/7` chamado por usuário comum |
| Correção | checagem por objeto (policy) | controle de função por papel/escopo na rota |

Segundo a OWASP, se o atacante consegue acessar um endpoint ou função a que não
deveria ter acesso, o caso é BFLA, não BOLA. Nos dois, o teste é pareado: duas
contas com o **mesmo papel** para BOLA, dois papéis diferentes para BFLA.

## Como testar

O método das duas contas, descrito também no artigo de Controle de Acesso da
Academy:

1. Crie o usuário A e o usuário B com o mesmo papel.
2. Execute a ação como A e capture a request completa (método, caminho, headers,
   corpo).
3. Repita exatamente a mesma request, mantendo os IDs de A, mas com a sessão de
   B.
4. Compare status e corpo.

O que conta como vulnerável:

- `200` com os dados de A em vez de `403`/`404`.
- `200` com corpo vazio mas efeito colateral aplicado (ex.: `DELETE` de A
  retorna `204` para B).
- `200` com dados parciais de A: também é BOLA, e a severidade depende do campo.

Onde procurar o ID além da URL:

- query string (`?id=`, `?invoice=`), caminho (`/v1/orders/12345/items`),
  corpo JSON (`{"accountId": 7}`), formulário;
- headers de tenant (`X-Tenant-ID`), que muitas vezes são tratados como
  "confiáveis" porque vêm do front;
- IDs compostos em GraphQL (`reportKeys: [...]`) e mutations em lote
  (`/api/batch`).

Para cada endpoint, o reporte precisa de: request como A, request como B, e a
prova de que os dados são de A. Sem isso é hipótese, não achado.

## Variantes que o teste de duas contas não pega

- **IDs previsíveis e enumeráveis.** Testar o objeto de A pelo B já cobre o IDOR
  direto. O que falta é testar objeto que **não pertence a ninguém**: id
  negativo, id 0, id acima do máximo. Respostas diferentes (`404` vs `200`)
  revelam se a checagem é de existência ou de autorização.
- **Troca de recurso aninhado.** `/orgs/1/users/99`: a checagem pode ser feita
  em `org 1` (que é sua) e não em `user 99` (que não é).
- **Novos campos após update.** `PUT /profile` que aceita `role` é
  object-property (API3:2023) combinado com BOLA quando o objeto é de outro
  usuário.
- **GraphQL.** Uma mutation que recebe lista de IDs pode validar apenas o
  primeiro elemento. O exemplo do OWASP para delete de documento usa exatamente
  esse formato.

## Multi-tenant

Em API multi-tenant, o isolamento é tão crítico quanto o objeto. Teste:

- header de tenant trocado com sessão válida de outro tenant;
- subdomínio trocado mantendo sessão;
- tenant inferido do e-mail, do `client_id` OAuth ou de um path base;
- `403` de um ID de outro tenant vs `404`: a diferença de código revela
  existência de objetos de outro cliente.

## Como corrigir

O que a OWASP recomenda, na ordem:

1. Mecanismo de autorização baseado em **políticas e hierarquia**, não em
   comparação campo-a-campo.
2. Checar em **toda** função que usa entrada do cliente para acessar registro.
3. Preferir GUIDs imprevisíveis como ID — reduz enumeração, mas **não
   substitui** a checagem.
4. Escrever testes de autorização que falham no build. Não publicar mudança que
   quebra o teste.

O item 3 merece ênfase: GUID não é correção de BOLA. Um ID que você obtém por
outro vazamento continua funcionando. A correção real é a checagem server-side.

## Impacto e severidade

A própria OWASP classifica a exploração como **fácil** e a detecção como
**fácil**, com persistência *widespread*. O impacto técnico é *moderate*, mas o
impacto de negócio é variável: exposição de dados de cliente, manipulação de
dados financeiros, e em alguns casos tomada de conta completa quando o objeto
manipulado é credencial ou reset token.

No relatório, ligue o objeto exposto ao dado de negócio: "IDOR em fatura" é
menos convincente que "o IDOR expõe CPF, endereço e histórico de 12 mil faturas
de clientes".

## O que este documento não cobre

As outras nove categorias do OWASP API Top 10 têm documento próprio, exceto
BFLA, que é tratado no artigo de Controle de Acesso. A implementação em
frameworks específicos (DRF, Spring, Nest) depende de cada stack e não é
generalizável.