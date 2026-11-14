---
slug: own-ghidra-metodologia-reversing
title: "Ghidra na prática: importar, achar a lógica e registrar o que se provou"
category: reversing
summary: "Fluxo de trabalho com Ghidra: importação e escolha de processador, análise automática e seus limites, navegação por funções e referências cruzadas, diferença entre decompilação (recurso de leitura) e assembly (fonte da verdade), renomeação e tipagem como forma de documentação, e a verificação cruzada com outro desassemblador. Enfatiza o que a decompilação não garante."
tags: "reversing ghidra decompilador assembly disassembly binario analise"
severity: info
references:
  - Ghidra — site oficial | https://ghidra-sre.org/
  - Ghidra — repositório e versões | https://github.com/NationalSecurityAgency/ghidra
  - Ghidra — notas de versão (mudanças de API e plugins) | https://github.com/NationalSecurityAgency/ghidra/releases
  - radare2 — livro de referência | https://book.rada.re/
  - Rizin — desassemblador e depurador alternativo | https://rizin.re/
---

O Ghidra é um desassemblador e decompilador de código aberto. Ele lê um
binário, identifica funções, produz assembly e tenta reconstruir uma forma de
linguagem de alto nível. É a ferramenta mais usada para responder "o que este
binário faz", e também a mais mal compreendida.

## Importação

Na importação, a escolha central é o **processador e o formato**. Escolher o
errado produz um binário sem sentido — e o erro é silencioso: a análise roda,
o resultado parece código, e não é.

Casos comuns:

- ELF x86-64 (Linux) — formato ELF, processador `x86:LE:64:default`.
- PE x86 ou x86-64 (Windows) — formato PE, processador correspondente.
- Firmware cru (ARM, MIPS, RISC-V) — formato binário bruto e endereço base
  declarado manualmente. Sem o endereço base, as referências de ponteiro
  apontam para o lugar errado.

Registre no laudo com que opções o binário foi importado. Um resultado de
análise sem essa informação não é reproduzível.

## Análise automática e seus limites

Após a importação o Ghidra executa análise automática: descobre funções,
resolve referências, cria strings e tipos.

O que ela **faz** bem: localizar funções chamadas a partir de tabelas,
identificar strings impressas, mapear chamadas a APIs importadas.

O que ela **não** faz: identificar corretamente código gerado por compilador
otimizado ou por ofuscador. Funções "fantasma", blocos de código tratados como
dados e funções sem retorno são normais em binários reais. Quando o
decompilador produz uma expressão absurda, a causa quase sempre é análise
incompleta — não bug da ferramenta.

## Navegação

A navegação gira em torno de três coisas:

- **Árvore de funções** — entrada, funções exportadas, funções chamadas por
  cada função. Em malware, a entrada costuma ser um `main` que decodifica e
  chama a lógica real.
- **Referências cruzadas** — quantos lugares chamam esta função, quantos leem
  esta string. É o instrumento mais valioso. Uma string de erro única chamada de
  um lugar aponta para a função de validação correspondente.
- **Janela de decompilação** — o pseudocódigo de uma função.

A regra prática: **chegue à função pela string, não por varredura linear**. Em
binário grande, começar pela primeira função é perder horas.

## Decompilação é hipótese, assembly é evidência

Essa distinção precisa ser explícita no laudo:

| Afirmação | Fonte aceitável |
| --- | --- |
| "há uma chamada à função X" | referência cruzada ou chamada em assembly |
| "o argumento é a constante 0x1f" | instrução em assembly |
| "esta rotina implementa comparação de senha" | assinatura da função e fluxo, confirmados |
| "o autor usa a biblioteca Y" | símbolo ou string de versão confirmados |

A decompilação reescreve a lógica. Entre o pseudocódigo e a instrução existem
otimizações — inlining, reordenação, reutilização de registrador — que o
decompilador reconstrói de forma aproximada. Por isso toda conclusão que
sustenta um achado é confirmada no assembly.

## Documentar dentro da ferramenta

Renomear funções, renomear variáveis, definir tipos e comentar são **o
trabalho**, não um passo opcional depois. Um binário com 300 funções chamadas
`FUN_00401a20` é um binário não analisado.

O ganho é duplo: o próprio analista mantém o raciocínio, e o próximo — ou o
mesmo, em outra semana — retoma a análise. O projeto do Ghidra é persistente e
pode ser versionado, o que torna isso uma forma de documentação técnica.

## Verificação cruzada

Dois desassembladores concordando sobre o fluxo de controle é o padrão mínimo
de confiança em reversing. Discrepância entre Ghidra e radare2 na reconstrução
de uma função significa que pelo menos um perdeu referência; o assembly
resolve.

## Quando parar

A análise termina quando se pode responder, com evidência citável:

1. Qual é o ponto de entrada e o que ele faz primeiro?
2. De onde vêm os dados externos?
3. Existe decodificação, descriptografia ou descompressão — e como ela é
   acionada?
4. Existe comunicação de rede, e para qual destino (string, constante,
   configuração)?
5. Quais artefatos são criados ou modificados?

Se a resposta a qualquer item depende de "parece que", a análise não terminou.