---
slug: business-logic
title: "Lógica de negócio: abuse das regras, não do parser"
category: logic
difficulty: medium
summary: "Encontre pressupostos sobre ordem, quantidade, propriedade e estado, e prove impacto financeiro ou de autorização com a menor manipulação possível."
tags: [business-logic, race-condition, coupons, workflow, state-machine]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 120
---

# Lógica de negócio: abuse das regras, não do parser

Falhas de lógica de negócio são comportamento válido usado em uma sequência inválida. A aplicação pode interpretar perfeitamente toda entrada e ainda permitir que você compre um produto por menos de zero, reutilize um cupom para sempre, aprove a própria despesa ou saque o mesmo saldo duas vezes.

Não existe payload universal. O método é modelar as regras pretendidas e então violar um pressuposto de cada vez.

## Modele a máquina de estados

Anote estados e transições:

```text
cart -> pending_payment -> paid -> fulfilled
                  |            |
                  v            v
               cancelled     refunded
```

Para cada transição, pergunte:

- Quem pode dispará-la?
- O que precisa ser verdade antes dela?
- A transição é idempotente?
- O que acontece se ela for reproduzida?
- Ela pode rodar em paralelo com outra transição?

Muitas falhas são lacunas de "checar, depois agir": a aplicação valida uma condição, executa uma operação lenta e nunca recheca antes de confirmar.

## Padrões comuns

### Quantidades e preços negativos

Se o servidor confia em totais, quantidade ou preço enviados pelo cliente:

```json
{"item":"license","quantity":-1,"price":499}
```

Uma quantidade negativa pode gerar um crédito, reduzir o total abaixo de zero ou inverter um reembolso. O cliente deveria enviar apenas ID do item e quantidade; o servidor deveria consultar o preço e impor limites.

### Empilhamento e reutilização de cupons

Teste:

- Aplicar o mesmo cupom várias vezes.
- Combinar cupons mutuamente exclusivos.
- Aplicar um cupom depois que o total mudou.
- Reutilizar um cupom de uso único entre contas ou sessões.
- Variantes de caixa/espaços nos códigos de cupom.
- Cupons aplicados a itens não elegíveis.

Se o desconto é calculado client-side ou aplicado antes das checagens de elegibilidade, a ordem das operações importa.

### Condições de corrida

Requests concorrentes podem contornar um limite:

```
balance = 100
request A: check balance >= 80 -> true
request B: check balance >= 80 -> true
request A: withdraw 80 -> balance 20
request B: withdraw 80 -> balance -60
```

Teste com concorrência controlada contra um lab. Use poucas requests paralelas e capture todas as respostas. Chaves de idempotência e constraints no banco são as correções duráveis; locks de aplicação precisam cobrir toda a seção crítica.

### Pular etapas do fluxo

Você consegue ir de `cart` para `fulfilled` sem `paid`? Tente:

- Chamar diretamente o endpoint de fulfillment.
- Mudar um campo de status na request.
- Reproduzir uma aprovação de admin com outro ID de objeto.
- Usar outro content type ou versão de API.
- Enviar um parâmetro escondido `next_state`.

### Abuso de reembolso e cancelamento

- Reembolsar mais do que foi pago.
- Reembolsar um pedido já reembolsado.
- Cancelar depois do fulfillment.
- Transferir saldo para outra conta.
- Reutilizar um token de saque de uso único.

## Teste com invariantes

Defina invariantes que sempre precisam valer:

- Total pago >= 0.
- Soma dos reembolsos <= valor pago.
- Um cupom é usado no máximo uma vez por conta.
- Estoque nunca fica negativo.
- Um pedido não pode ser cumprido antes do pagamento.
- Um usuário não pode aprovar a própria solicitação.

Depois tente violar cada invariante com a menor sequência de requests. Guarde o estado antes e depois para que o impacto não seja ambíguo.

## Confiança no cliente

Se o preço, desconto, papel ou flag de aprovação é enviado pelo cliente e usado sem verificação server-side, a regra de negócio é decorativa. Recalcule todos os valores críticos server-side a partir de dados confiáveis.

## Correção

1. Centralize as regras de negócio na camada de serviço.
2. Imponha invariantes no banco (unique constraints, check constraints, transações).
3. Use chaves de idempotência para operações que podem ser reprocessadas.
4. Serialize seções críticas ou use optimistic locking com checagem de versão.
5. Recalcule preços, totais e permissões server-side.
6. Deixe as transições de estado explícitas e rejeite transições desconhecidas.
7. Adicione logs de auditoria para operações financeiras e de privilégio.
8. Teste concorrência e replay, não só caminhos felizes.

A orientação de lógica de negócio da OWASP enfatiza casos de abuso e teste de fluxo em vez de validação de entrada. [OWASP WSTG — Business Logic Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/)

## Checklist de teste

- [ ] Mapeie estados, atores e transições permitidas
- [ ] Teste quantidades e preços negativos/zero/enormes
- [ ] Reutilize e empilhe cupons
- [ ] Reproduza tokens de uso único e reembolsos
- [ ] Rode requests concorrentes controladas
- [ ] Pule etapas e chame endpoints de estágios posteriores diretamente
- [ ] Altere campos de status/papel enviados pelo cliente
- [ ] Verifique constraints e transações no banco
- [ ] Confirme as invariantes depois de cada tentativa

## Referências

- [OWASP WSTG — Business Logic Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/)
- [OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)
- [CWE-840 — Business Logic Errors](https://cwe.mitre.org/data/definitions/840.html)
- [CWE-362 — Concurrent Execution Using Shared Resource with Improper Synchronization](https://cwe.mitre.org/data/definitions/362.html)
- [PortSwigger — Business logic vulnerabilities](https://portswigger.net/web-security/logic-flaws)