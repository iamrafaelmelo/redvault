---
slug: own-hmac-e-integridade
title: "HMAC, hash e MAC: por que \"hash de senha\" não é prova de integridade"
category: crypto-primitives
summary: "Separa função de hash (digest), MAC (autenticação) e KDF (derivação de chave) pelo que cada um garante. Explica HMAC sobre a RFC 2104, a diferença entre comparar hash e comparar MAC, o ataque de extensão de comprimento que invalida a construção hash(chave || mensagem), e por que password e integridade de mensagem exigem primitivas diferentes."
tags: "criptografia hmac hash mac kdf integridade senha rfc2104"
severity: info
references:
  - RFC 2104 — HMAC: Keyed-Hashing for Message Authentication | https://www.rfc-editor.org/rfc/rfc2104
  - NIST — projeto de funções de hash criptográficas | https://csrc.nist.gov/projects/hash-functions
  - OWASP — Cryptographic Storage Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
  - CrackStation — Salted Password Hashing: Doing it Right | https://crackstation.net/hashing-security.htm
  - HackTricks — Hashes, MACs e KDFs | https://github.com/HackTricks-wiki/hacktricks
---

As três siglas aparecem juntas e são usadas de forma trocável. Elas não fazem
a mesma coisa:

| Primitiva | Pergunta | Requer segredo |
| --- | --- | --- |
| Hash (`SHA-256`) | "o conteúdo é este?" | não |
| MAC (`HMAC`) | "quem enviou é quem diz ser, e o conteúdo não mudou?" | sim, chave |
| KDF (`scrypt`, `argon2`) | "qual chave deriva desta senha, com custo alto?" | não, mas custo |

Confundir hash com MAC é o erro que permite forjar mensagem. Confundir KDF
com hash é o erro que permite quebrar senha por força bruta.

## Hash é público por natureza

`SHA-256(mensagem)` pode ser calculado por qualquer pessoa. Ele demonstra que
duas partes **viram o mesmo conteúdo**. Não demonstra que a mensagem veio de
alguém. Se o canal de transporte é público, qualquer um pode truncar e
recalcular o hash.

Conclusão imediata: um "checksum" de download publicado numa página é uma
defesa contra corrupção, não contra adulteração — se a página e o arquivo
vierem do mesmo lugar.

## HMAC e a razão de existir

A construção intuitiva é `hash(chave || mensagem)`. Ela falha por um motivo
não óbvio: funções de hash como SHA-256 são construídas sobre compressão
iterada, e o estado interno após processar a mensagem é conhecido pelo atacante
que conhece `hash(chave || mensagem)`. Tendo esse valor, ele consegue calcular
`hash(chave || mensagem || extensão)` sem conhecer a chave. É o **ataque de
extensão de comprimento**.

A RFC 2104 define a construção que resolve isso:

```
HMAC(K, m) = H( (K' ⊕ opad) || H( (K' ⊕ ipad) || m ) )
```

Duas propriedades importantes:

1. **A chave afeta o estado interno em dois pontos**, não um. Por isso a
   extensão não funciona.
2. **A chave é normalizada a um bloco de 64 bytes** antes do XOR. Consequência
   prática: uma chave de 8 bytes é tão segura quanto o tamanho do hash permite,
   mas não mais — o segredo continua sendo a entropia da chave.

## Comparar MAC e comparar hash

Há uma armadilha independente da primitiva: **comparar os valores com tempo
constante**. Uma comparação que para no primeiro byte divergente revela, pelo
tempo de resposta, quantos bytes estão corretos. Com um oráculo de tempo, um
atacante reconstrói o MAC byte a byte.

O padrão é a comparação de tempo constante (`hmac.compare_digest` em Python,
equivalente em outras linguagens), não `==` sobre string.

## Hash de senha: KDF, não hash

Um hash rápido é ruim mesmo que salgado. A razão é custo: o salt impede ataque
por tabela pré-computada, mas não impede dicionário. O que impede é **trabalho
por tentativa**.

Por isso KDFs de senha — PBKDF2 com fator alto, `scrypt`, `argon2` — gastam
memória, CPU ou ambos por tentativa. O OWASP Cryptographic Storage Cheat Sheet
e a explicação clássica do CrackStation descrevem o mesmo princípio: o salt é
por usuário e armazenado com o hash; o fator de custo é ajustado ao hardware
atual.

## Onde o token se encaixa

Um JWT assinado com HMAC carrega integridade: quem tem a chave não pode ser
falsificado. Mas a chave não é "a senha"; é o segredo do servidor. Se a chave é
fraca ou vazada, a assinatura perde valor.

## Resumo operacional

- **Contra corrupção:** hash, público, sem segredo.
- **Contra adulteração:** MAC com chave, comparação de tempo constante.
- **Armazenar senha:** KDF com salt e custo calibrado, nunca hash simples.
- **Trocar mensagem:** cifrar e **depois** requiperar (encrypt-then-MAC); a
  ordem inversa permite manipular o texto cifrado.

Essas quatro linhas resolvem a maior parte das confusões de implementação — e
cada uma delas, quando errada, transforma uma primitiva forte em falsa
sensação de segurança.