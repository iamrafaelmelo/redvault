---
slug: access-control
title: "Controle de acesso: objetos, funções e tenants"
category: access
difficulty: easy
summary: "Use duas identidades para provar checagens de propriedade ausentes, quebra de autorização em nível de função e escalada de privilégio via mass assignment."
tags: [access-control, idor, bola, bfla, mass-assignment]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 40
---

# Controle de acesso: objetos, funções e tenants

Autorização é a decisão sobre o que um ator autenticado pode fazer. Ela falha em duas dimensões:

- **Nível de objeto (BOLA/IDOR):** este ator pode acessar *este registro*?
- **Nível de função (BFLA):** este ator pode invocar *esta operação*?

Uma terceira dimensão é o isolamento de tenant ou organização: este ator pode ver dados de outro cliente? Teste as três com duas contas, não com uma.

## O método das duas contas

Crie a conta A e a conta B com o mesmo papel. Execute cada ação como A e capture as requests. Repita cada request como B, trocando a sessão pela de B mas mantendo os identificadores de objeto de A.

| Teste | Esperado | Comportamento vulnerável |
| --- | --- | --- |
| B pede a fatura de A | 403/404 | 200 com os dados de A |
| B atualiza o perfil de A | 403/404 | o perfil de A muda |
| B apaga o arquivo de A | 403/404 | arquivo apagado |
| B lista registros do tenant A | só o tenant B | os dois tenants retornam |

Depois crie uma conta de baixo privilégio e tente funções de admin diretamente. A UI esconder um botão não é autorização.

O OWASP API Security Top 10 2023 classifica BOLA como A1 e BFLA como A5. [OWASP API Security Top 10 — A1 BOLA](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/) [A5 BFLA](https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/)

## Padrões de identificador

Identificadores de objeto aparecem como números, UUIDs, slugs, chaves compostas e valores codificados. IDs numéricos são fáceis de enumerar; UUIDs não são autorização. Teste:

- IDs sequenciais e valores negativos/zero.
- UUIDs colhidos de outra resposta.
- Rotas aninhadas: `/users/7/invoices/42`.
- Filtros de query: `?account_id=2`, `?tenant=other`.
- Corpos JSON que aceitam `owner_id` ou `account_id`.
- Node IDs de GraphQL e endpoints de batch.

Se o servidor usa o identificador da URL mas autoriza apenas "está logado", o objeto está exposto.

## Mass assignment

Mass assignment acontece quando um framework liga campos arbitrários da request a um modelo. O atacante acrescenta campos que a UI nunca envia:

```http
POST /profile HTTP/1.1
Content-Type: application/x-www-form-urlencoded

display=Alice&department=Research&role=admin
```

Padrões defensivos:

- Allowlists explícitas (DTOs) por operação.
- `readOnly`/`readOnlyProperties` nos serializers.
- Rejeitar campos desconhecidos em vez de ignorá-los silenciosamente.
- Revalidar autorização depois do binding, especialmente para campos de papel, dono e status.

Spring4Shell (CVE-2022-22965) é um exemplo de alto impacto de data binding alcançando propriedades perigosas do class-loader. [CVE-2022-22965](https://www.cve.org/CVERecord?id=CVE-2022-22965)

## Forced browsing e endpoints escondidos

Rotas de admin costumam depender de route guards no cliente. Teste requests diretas para:

- `/admin`, `/admin/users`, `/internal`, `/debug`.
- Versões de API e prefixos alternativos: `/api/v1/admin`, `/api/internal`.
- Métodos HTTP: `GET` bloqueado mas `POST`, `PUT` ou `PATCH` permitidos.
- Extensões de arquivo e normalização de path: `/admin/..;/admin`, slashes codificadas.

O material de access control do PortSwigger cobre bypasses verticais e horizontais, incluindo discrepâncias de correspondência de URL. [PortSwigger — Access control vulnerabilities](https://portswigger.net/web-security/access-control)

## Autorização dependente de contexto

O mesmo objeto pode ter regras diferentes por estado:

- Uma fatura é legível pelo dono *até* ser paga.
- Um agente de suporte pode ver o registro de um cliente *somente com ticket ativo*.
- Um usuário pode editar um rascunho mas não um post publicado.
- Um gerente pode aprovar despesas abaixo de um limite.

Teste transições, não apenas papéis estáticos. Reproduza uma request depois de mudar o estado do objeto, depois de remover um relacionamento e depois que o dono mudar.

## Armadilhas multi-tenant

O isolamento de tenant falha quando:

- O tenant ID vem da request e não é checado contra a sessão.
- Uma cache key compartilhada omite o tenant.
- Jobs em background processam registros sem escopo de tenant.
- A busca de admin atravessa tenants sem autorização explícita.
- Um link de compartilhamento "público" contorna as checagens de tenant.

Use dois tenants e teste endpoints de listagem, busca, exportação e notificação. Vazamentos de dados costumam aparecer no endpoint menos glamouroso.

## Padrões de correção

Autorização pertence perto da camada de acesso a dados:

```python
def get_invoice(db, user, invoice_id):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.owner_id != user.id:
        raise NotFound
    return invoice
```

Prefira uma política deny-by-default, centralize as consultas de objeto e teste com casos automatizados de dois usuários. Não confie em:

- Esconder IDs ou usar UUIDs.
- Route guards client-side.
- Endpoints obscuros.
- Checagens de papel só no controller, enquanto a camada de serviço confia em quem chama.

## Checklist de teste

- [ ] Duas contas de mesmo papel para testes horizontais
- [ ] Uma conta de baixo privilégio para testes verticais
- [ ] IDs de objeto em URLs, corpos, headers e GraphQL
- [ ] Endpoints de listagem, busca, exportação e batch
- [ ] Transições de estado e relacionamentos revogados
- [ ] Mass assignment na criação e na atualização
- [ ] Bypasses por método e por normalização de path
- [ ] Isolamento de tenant em toda resposta que carrega dados

## Referências

- [OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
- [OWASP WSTG — Authorization Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/)
- [PortSwigger — Access control vulnerabilities](https://portswigger.net/web-security/access-control)
- [CWE-639 — Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)
- [CWE-915 — Improperly Controlled Modification of Dynamically-Determined Object Attributes](https://cwe.mitre.org/data/definitions/915.html)