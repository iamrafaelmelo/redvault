---
slug: own-reversing-anti-depuracao
title: "Anti-depuração e anti-análise: reconhecer antes de contornar"
category: reversing
summary: "Técnicas usadas por binários para dificultar a análise — detecção de depurador, temporização, exceções como fluxo de controle, checagem de ambiente — agrupadas pelo mecanismo real. Para cada família: como se manifesta, como confirmar e como registrar que foi contornada, distinguindo ofuscação de defeito de análise."
tags: "reversing anti-debug depurador ofuscacao excecao temporizacao analise"
severity: info
references:
  - HackTricks — Fluxo de controle baseado em exceções do Windows e anti-debug | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — Ferramentas de reversing e métodos básicos | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — Ferramentas de exploração (pwntools, gdb) | https://github.com/HackTricks-wiki/hacktricks
  - Ghidra — repositório e notas de versão | https://github.com/NationalSecurityAgency/ghidra
  - Detection of native anti-debugging in Windows (exceções e flags) — ATT&CK | https://attack.mitre.org/
---

Um binário pode se comportar de três maneiras, e elas não são a mesma coisa:

1. **Defeito** — bug de compilação ou dado inválido.
2. **Ofuscação** — o código foi transformado para esconder lógica de leitura
   estática.
3. **Anti-análise** — o código mudou de comportamento **porque está sendo
   analisado**.

Confundir 2 e 3 leva a desistir de um binário que funciona normalmente em
produção. Confundir 3 com 1 leva a concluir "binário corrompido" quando na
verdade a análise foi detectada.

## Família 1 — Detectar o depurador

O binário pergunta, por uma API ou por uma estrutura do sistema, se há
depurador anexado. Se sim, encerra ou entra em caminho falso.

Sintoma de laboratório: o binário roda normalmente fora do depurador e para na
primeira execução, ou produz saída diferente.

Como confirmar: executar sem depurador e comparar. Depois, com o depurador,
localizar a chamada e registrar o valor retornado — o ponto onde o
comportamento diverge.

Registro correto no laudo: "presença da chamada de checagem no endereço X,
retorno controlado durante a análise". Não é "o binário está quebrado".

## Família 2 — Temporização

O código mede o tempo entre duas operações. Sob depurador, o intervalo é maior
devido a pausas humanas. Se o intervalo exceder um limite, o binário assume
depuração.

Sintoma: a primeira execução passa, a segunda — com o analista pausando —
falha.

É importante não confundir com detecção de virtualização ou de ambiente
sandbox — um binário pode medir a mesma coisa para renderizar de forma
diferente em ambiente de análise.

## Família 3 — Exceções como fluxo de controle

O binário provoca uma exceção intencional e trata-a internamente, usando o
tratamento para desviar para a lógica real. Quem executa sem entender o fluxo
vê uma exceção "não tratada" que, na verdade, é o caminho previsto.

No Windows, o HackTricks documenta o uso de exceções e o fluxo de controle
baseado em exceções como técnica de anti-debug. Uma consequência prática é que
a ferramenta de análise precisa tratar exceções de forma idêntica ao runtime
real; um depurador que para na exceção impede o binário de avançar.

Esse é o tipo mais mal diagnosticado: o analista vê a exceção e conclui que o
binário está corrompido.

## Família 4 — Verificação do ambiente

O binário inspeciona variáveis de ambiente, presença de arquivo, nome do
processo pai, ferramentas conhecidas no caminho. Se o ambiente parece ser o de
análise, escolhe caminho alternativo.

Sintoma: funcionamento diferente entre máquina de análise e máquina de teste
limpa.

A correção é ambiental, não de depurador: rodar num ambiente com a mesma
composição do alvo — mesma versão de sistema, mesmos serviços — em vez de tentar
adivinhar a variável que precisa ser escondida.

## Família 5 — Detecção de virtualização

O binário verifica se está em máquina virtual e muda de comportamento. Frequente
em malware que quer evitar execução em laboratório.

Sintoma: o mesmo binário se comporta de modo diferente em VM e em ferro.

Registro correto: "comportamento condicional a virtualização, observado em X".
Sem essa observação, o laudo afirma que o binário "não faz nada" quando, de
fato, ele decide não fazer nada **ali**.

## Ordem de investigação

1. Execute o binário num ambiente limpo e registre a referência de comportamento.
2. Execute sob depurador e compare — só a diferença importa.
3. Localize a divergência: chame-a pelo endereço, não por aproximação.
4. Identifique a família e contorne apenas o necessário.
5. Registre o contorno: o que foi alterado, onde, e o efeito no comportamento.

O item 5 é o que torna a análise auditável. Um analista que contorna sem
registrar produz uma conclusão irreproduzível — e irreproduzível, em laudo, é
indistinguível de inventada.

## O que não se faz

- Patchar o binário até ele agir como se espera e depois afirmar que "este era
  o comportamento".
- Confundir "não consegui analisar" com "não tem nada".
- Chamar ofuscação de anti-análise ou vice-versa sem evidência do mecanismo.

A diferença entre as três classificações acima é exatamente a evidência que se
coleta: se o comportamento só muda sob análise, é anti-análise.