---
slug: own-pki-cadeia-confianca
title: "PKI na prática: cadeia, validação e os erros que transformam certificado em teatro"
category: crypto-pki
summary: "Explica o que um certificado X.509 afirma (RFC 5280), como a cadeia de confiança é construída, o que o cliente valida além da assinatura (nome, validade, extensões, revogação), e os erros recorrentes — certificado aceito sem validação de cadeia, hostname não conferido, autoridade instalada manualmente. Baseia-se na RFC 5280, na RFC 8446 e na documentação do HackTricks sobre TLS."
tags: "pki certificado x509 tls cadeia confianca rfc5280 revogacao"
severity: info
references:
  - RFC 5280 — Internet X.509 Public Key Infrastructure | https://www.rfc-editor.org/rfc/rfc5280
  - RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3 | https://www.rfc-editor.org/rfc/rfc8446
  - HackTricks — TLS e Certificados | https://github.com/HackTricks-wiki/hacktricks
  - OWASP — Cheat Sheet Series (TLS e transporte seguro) | https://github.com/OWASP/CheatSheetSeries
  - NIST — projeto de funções de hash criptográficas | https://csrc.nist.gov/projects/hash-functions
---

Um certificado X.509, conforme a RFC 5280, é uma declaração assinada por uma
autoridade: "esta chave pública pertence a esta entidade". Ele não é a chave,
não é o segredo e não estabelece confiança por si. Confiança é o resultado de
uma cadeia que termina numa autoridade em que o cliente já acredita.

## O que o certificado contém

- **Nome do titular** — o `subject`, no formato do RFC 5280. Para TLS, o nome
  relevante está em uma extensão, não necessariamente no `subject` legado.
- **Chave pública** — a chave da entidade, não a chave privada.
- **Validade** — início e fim. Fora do intervalo, o certificado é inválido.
- **Emitente** — `issuer`, a autoridade que assinou.
- **Extensões** — usos permitidos (`keyUsage`, `extendedKeyUsage`), nomes
  alternativos (`subjectAltName`), restrições de caminho, políticas.
- **Assinatura** — feita pela chave privada da autoridade emitente.

## A cadeia

O cliente valida do certificado do servidor até uma raiz em que confia:

```
certificado do servidor          (emitido por) →
autoridade intermediária        (emitida por) →
autoridade raiz                 (na store de confiança do cliente)
```

Cada elo é validado pela assinatura do anterior. A cadeia só se completa se
cada certificado na sequência estiver válido **na data de verificação**, com a
extensão de uso compatível, e se o servidor enviar os certificados
intermediários — motivo frequente de falha de handshake.

Ponto contratual da RFC 8446: a validação em TLS 1.3 inclui conferir, no
certificado, a chave pública para a qual o servidor provou possuir a chave
privada. A cadeia, sozinha, não basta.

## O que o cliente precisa conferir — e frequentemente esquece

1. **Nome do host.** O nome esperado precisa constar nos nomes alternativos do
   certificado. Um certificado legítimo de `example.com` não autoriza `evil.com`.
2. **Validade no momento da conexão**, incluindo horário do cliente. Um relógio
   errado invalida toda a cadeia.
3. **Extensões de uso** — certificado emitido somente para assinatura não serve
   para TLS de servidor.
4. **Cadeia completa até raiz confiável** — não até uma raiz qualquer.

O erro mais comum em desenvolvimento é desabilitar a verificação de hostname
para "resolver o problema de certificado de teste". O efeito não é deixar o
ambiente menos seguro: é transformar a aplicação inteira em alvo de
interceptação, porque a chave que ela aceita pode ser qualquer uma.

## Autoridade instalada manualmente

Em ambientes de teste, é comum instalar uma autoridade própria na store do
cliente. Isso é legítimo — e tem duas consequências que precisam ser explícitas:

- todo certificado emitido por aquela autoridade passa a ser aceito, **para
  qualquer nome**, enquanto ela estiver instalada;
- se a chave privada da autoridade vazar, o vazamento é de toda a confiança
  instalada.

Por isso a autoridade de teste é escopo de laboratório. Nunca é a autoridade
usada em máquina de produção, e a remoção faz parte do procedimento de encerrar
o exercício.

## Revogação

O certificado deixa de ser válido antes do vencimento quando a autoridade
revoga. O cliente descobre por CRL (lista) ou por OCSP (consulta). A
complexidade operacional é alta, e a cobertura é incompleta por projeto: um
cliente que não verifica revogação aceita um certificado revogado.

Isso não é um defeito a "corrigir no cliente": é um limite do modelo, e é o
motivo pelo qual a expiração curta de certificado ganhou popularidade. Um
certificado que dura 90 dias limita a janela de um vazamento.

## Checklist de avaliação de uma configuração TLS

1. Qual é a cadeia apresentada pelo servidor? Está completa?
2. Os nomes alternativos cobrem todos os nomes necessários, e somente eles?
3. Qual é a validade, e quando foi renovada pela última vez?
4. Quais versões de protocolo são aceitas? Versões obsoletas estão desligadas?
5. Quais conjuntos de cifra são aceitos? Existe opção sem forward secrecy?
6. O certificado é de uma autoridade pública ou de uma autoridade interna?
   Se interna, ela está distribuída corretamente?
7. Existe monitoramento de expiração?

Cada resposta é um item de evidência. A frase "usa HTTPS" não é nenhuma delas —
o certificado pode ser autoassinado, o hostname pode não ser verificado e a
versão do protocolo pode ser obsoleta.