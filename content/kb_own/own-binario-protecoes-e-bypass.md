---
slug: own-binario-protecoes-e-bypass
title: "Proteções de binário: ler o que está ligado antes de procurar o que explorar"
category: exploit-dev
summary: "Explica NX, stack canary, PIE/ASLR, RELRO e CET pelo que cada um impede e pelo que muda no processo de exploração. Ensina a inventariar as proteções de um binário (checksec e leitura do ELF), a interpretar a combinação delas e o erro comum de tratar proteção ausente como vulnerabilidade presente."
tags: "binexp exploit binario nx canary pie aslr relro protecao pwn"
severity: info
references:
  - HackTricks — Proteções e Bypasses Comuns de Binary Exploitation | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — Metodologia básica de exploração de binários | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — ELF: informações básicas | https://github.com/HackTricks-wiki/hacktricks
  - pwntools — documentação | https://docs.pwntools.com/en/stable/
  - how2heap — exemplos graduais de exploração de heap | https://github.com/shellphish/how2heap
---

A primeira etapa de qualquer exercício de exploração não é achar a falha: é ler
o que o binário tem ligado. A mesma falha de memória é trivial num binário sem
proteções e impraticável noutro com todas. A ausência de uma proteção não é uma
vulnerabilidade; ela apenas reduz a dificuldade de explorar uma que exista.

## As cinco proteções, pelo que impedem

### NX (No-Execute)

Impede que a pilha e o heap sejam executados. Antes de NX, a exploração clássica
era escrever shellcode no buffer e desviar a execução para ele.

**O que muda:** o atacante precisa de código **já** no espaço de endereçamento
(bibliotecas) ou de reorientação de chamadas — `ret2win`, `ret2libc`,
`ret2plt`, ROP. A técnica deixa de ser "executar bytes" e passa a ser "combinar
gadgets existentes".

### Stack canary

Um valor aleatório colocado entre o buffer e o endereço de retorno. Se o
escritor falhar o buffer, o canário é sobrescrito; a função compara e aborta.

**O que muda:** overflow linear ingênuo deixa de funcionar. O atacante precisa
vazar o canário antes de escrever, ou encontrar um caminho que não passe pela
checagem. Canário por thread e cópia para binário são variantes mais duras.

### PIE (Position-Independent Executable)

O binário é carregado em endereço aleatório a cada execução.

**O que muda:** endereços internos deixam de ser constantes. É preciso vazar um
endereço de base primeiro. Sem PIE, o atacante conhece os endereços do binário
de antemão — mas **as bibliotecas** continuam com ASLR.

PIE e ASLR são relacionados mas não idênticos: ASLR é do sistema operacional;
PIE é uma propriedade do binário que permite participar dele. Um binário sem
PIE ainda sofre ASLR na `libc`.

### RELRO (Relocation Read-Only)

Protege a tabela de relocação (GOT) depois que o carregador a resolveu. Sem
RELRO, escrever na GOT redireciona uma chamada de função.

- **Partial RELRO** — parte da tabela é protegida; a GOT continua gravável.
- **Full RELRO** — a GOT inteira passa a somente leitura, e o carregador
  resolve todas as relocações na inicialização.

**O que muda:** Full RELRO elimina sobrescrita direta de GOT. O alvo passa a ser
outras estruturas: `__malloc_hook`, ponteiros em heap, tabelas de função de
linguagem de alto nível.

### CET / Shadow Stack

O CET mantém uma cópia da pilha de retorno acessível apenas ao processador.
Desviar o retorno para outro endereço é detectado. Combinado com ROP, ele exige
que os gadgets mantenham a pilha de sombra coerente — o que restringe muito a
técnica.

## Como inventariar

Duas abordagens, ambas legítimas, ambas precisam ser cruzadas.

**Via ferramenta:**

```
checksec --file=./alvo
```

A saída lista NX, Canary, PIE, RELRO e símbolos. É rápido e é o que se cita
numa primeira triagem.

**Via leitura do ELF:**

- Program headers — procura `GNU_STACK` (NX) e `GNU_RELRO`.
- Elemento de cabeçalho `PT_GNU_STACK` com flag de execução.
- Entrada `DT_BIND_NOW` ou `DF_BIND_NOW` ligada (RELRO completo).

Para binário estático e para firmware, a ferramenta pode adivinhar errado. O
cabeçalho do ELF é a fonte primária.

## A combinação é o que define a técnica

| NX | Canário | PIE | RELRO | Técnica viável |
| --- | --- | --- | --- | --- |
| desligado | nenhum | nenhum | partial | shellcode no buffer |
| ligado | nenhum | nenhum | partial | `ret2win`, `ret2plt`, `ret2libc` |
| ligado | presente | desligado | partial | vazar canário e depois ROP |
| ligado | presente | ligado | full | vazamento de PIE + ROP com `libc` vazada |
| tudo ligado + CET | — | — | — | exploração de heap/lógica, não de pilha |

Note que a linha mais difícil não é "binário sem proteção": é a exploração em
que a técnica deixa de ser reorientação de retorno e passa a ser corrupção de
estado de heap ou de objeto.

## Erros que invalidam o exercício

- **Prototype o exploit contra o ambiente errado.** A `libc` muda os offsets.
  Um exploit que funciona local e falha no alvo é a diferença de *uma* versão
  de `libc`.
- **Dizer "tem canário" sem checar se a verificação é chamada.** Um canário
  presente numa função que nunca retorna normalmente não importa.
- **Assumir que ASLR está desligado porque os offsets coincidem.** Aleatoriedade
  pode coincidir numa primeira execução; a prova é executar várias vezes.
- **Usar exploit de terceiro sem entender o offset da versão.** Copiar offset
  é copiar o problema.

## Documentar

Para cada binário analisado, o registro mínimo é:

```
alvo: nome e hash
libc: versão e hash (quando dinâmico)
proteções: NX=..., Canary=..., PIE=..., RELRO=..., CET=...
kernel/aslr: estado real do ambiente
falha: tipo e endereço da função
técnica: descrição em uma linha
```

Sem isso, o resultado do exercício não é reproduzível e não serve de evidência
de competência — serve de anedota.