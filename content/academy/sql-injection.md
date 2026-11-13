---
slug: sql-injection
title: "SQL Injection: contexto, prova e fronteiras"
category: sqli
difficulty: medium
summary: "Identifique o contexto da query, prove a execução com um diferencial mínimo e entenda por que a parametrização corrige a causa, não o sintoma."
tags: [sqli, union, blind, parameterized-queries, database]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 50
---

# SQL Injection: contexto, prova e fronteiras

SQL injection acontece quando um dado é concatenado em uma query e o banco interpreta parte desse dado como código. A vulnerabilidade não é "uma aspa quebra a página"; é uma fronteira de parser sendo cruzada. Testar é a arte de localizar essa fronteira e provar controle sem causar dano desnecessário.

## Encontre o contexto primeiro

A mesma string tem efeitos diferentes dependendo de onde cai:

```sql
-- String literal
SELECT * FROM users WHERE username = '<input>'

-- Posição numérica
SELECT * FROM invoices WHERE id = <input>

-- Identificador (tabela/coluna/order)
SELECT * FROM products ORDER BY <input>

-- LIMIT / OFFSET
SELECT * FROM posts LIMIT <input>
```

Teste com sondas adequadas ao contexto:

| Contexto | Sonda | Procurar |
| --- | --- | --- |
| String literal | `'`, `''`, `\'` | Erro, escaping, mudança de resultado |
| Numérico | `1`, `1-0`, `1 AND 1=1` | Mesma/diferente linha, erro |
| ORDER BY | `1`, `2`, `name` | Mudança de ordem ou erro |
| LIMIT | `1`, `1,2` | Mudança na quantidade de linhas |

Uma aspa que gera erro é um sinal, não uma prova. O erro pode ser genérico, o parâmetro pode ser sanitizado em um caminho, ou a query pode usar prepared statement e falhar em outro ponto. Sempre confirme com um diferencial.

## Confirmação por erro

Se a aplicação expõe erros do banco, identifique o engine pela mensagem e use uma expressão inofensiva que deveria avaliar verdadeiro/falso:

```sql
' AND 1=1 -- 
' AND 1=2 -- 
```

Se a primeira retorna dados normais e a segunda não retorna nada, a entrada está influenciando a query. Comentários (`-- `, `#`, `/* */`) variam por banco e precisam ser adaptados.

Evite extrair schemas ou credenciais em um primeiro teste. Prova de controle basta para demonstrar o achado; a extração depende das regras do engajamento.

## Extração com UNION

Um `UNION SELECT` exige quantidade de colunas compatível e tipos compatíveis. Determine a contagem de colunas com `ORDER BY`:

```sql
' ORDER BY 1 -- 
' ORDER BY 2 -- 
' ORDER BY 3 -- 
```

Quando a query erra em `ORDER BY 4`, o conjunto de resultados tem três colunas. Depois alinhe os tipos:

```sql
' UNION SELECT 1, 'marker', 3 -- 
```

Se o marcador aparecer, a injeção está no conjunto de resultados. A partir daí, selecione dados reais:

```sql
' UNION SELECT 1, username, password FROM users -- 
```

Os catálogos do sistema do banco (`information_schema`, `pg_catalog`, `sqlite_master`) descrevem tabelas e colunas. Consulte apenas o que o engajamento exige. Os labs de SQL injection do PortSwigger são um caminho de prática estruturado. [PortSwigger — SQL injection](https://portswigger.net/web-security/sql-injection)

## Confirmação cega e baseada em tempo

Quando as respostas não refletem dados, use diferenças booleanas ou de tempo:

```sql
' AND SUBSTR((SELECT secret FROM vault),1,1)='R' -- 
```

```sql
' AND (SELECT 1 FROM (SELECT SLEEP(3))x) -- 
```

Payloads baseados em tempo são específicos do engine e podem ser instáveis sob carga. Repita o teste e compare com uma baseline. Para extração em volume, use um script com limites de concorrência e uma condição de parada clara.

## Injeção de segunda ordem

Dados armazenados podem ser executados depois, em outra query. Um nome de usuário contendo SQL injetado pode ser inofensivo no cadastro mas perigoso quando um relatório de admin monta uma query com ele.

Teste armazenando um marcador e depois disparando todo consumidor: página de perfil, exportação, busca de admin, job agendado, resposta de API. O sink vulnerável é onde o valor armazenado é concatenado, não onde foi digitado.

## SQL injection em ORMs

ORMs reduzem, mas não eliminam, o risco. Padrões perigosos incluem:

- SQL bruto com f-strings ou concatenação.
- `ORDER BY` montado a partir de entrada do usuário (identificadores não podem ser parametrizados em muitos bancos).
- `extra()`/`whereRaw()` com interpolação.
- Nomes dinâmicos de tabela ou coluna.
- Uso incorreto de query builders que tratam uma string como SQL.

Parametrização liga valores, não identificadores. Para identificadores, use uma allowlist.

## Por que queries parametrizadas funcionam

Um prepared statement envia a estrutura da query e os dados separadamente. O banco compila a instrução antes de os valores chegarem, então um valor como `' OR 1=1 --` é tratado como string, não como sintaxe.

```python
cursor.execute(
    "SELECT id, name FROM products WHERE name LIKE ?",
    (f"%{term}%",),
)
```

Isso é diferente de escapar aspas manualmente. Escapar é propenso a erro entre codificações e modos do banco; parametrização é a fronteira correta.

## Defesas que de fato funcionam

1. **Queries parametrizadas em todo lugar**, incluindo relatórios, jobs e ferramentas de admin.
2. **Allowlist de identificadores** usados em `ORDER BY`, nomes de tabela e nomes de coluna.
3. **Contas de banco com menor privilégio**: sem `FILE`, sem acesso entre bancos, sem alterações de schema para o usuário do app.
4. **Tratamento genérico de erros** e logging centralizado com request IDs.
5. **WAF como detecção**, não como a correção principal.
6. **Testes que verificam o formato da query**, incluindo casos negativos.

O OWASP SQL Injection Prevention Cheat Sheet é a referência de implementação. [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

## Checklist de teste

- [ ] Identifique todo parâmetro que chega a uma query
- [ ] Determine se o contexto é string, numérico, identificador ou LIMIT
- [ ] Confirme com um diferencial booleano ou de erro
- [ ] Determine contagem e tipos de coluna para UNION
- [ ] Teste sinks de segunda ordem e jobs em background
- [ ] Revise SQL bruto e escape hatches de ORM no código
- [ ] Verifique o menor privilégio da conta de banco
- [ ] Evite extração destrutiva; preserve prova mínima

## Referências

- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [PortSwigger — SQL injection](https://portswigger.net/web-security/sql-injection)
- [CWE-89 — SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [OWASP WSTG — Testing for SQL Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection)
- [MITRE ATT&CK — Exploitation of Remote Services](https://attack.mitre.org/techniques/T1210/)