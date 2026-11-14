---
slug: own-hardware-firmware-ghidra
title: "Análise de binário de firmware com Ghidra: método, não magia"
category: hardware-firmware
summary: "Fluxo de engenharia reversa de binários extraídos de firmware com Ghidra: escolha de arquitetura e base de carga, reconstrução de tabela de strings, análise de funções e modo headless para automatizar. Inclui o que roda sem nenhum hardware e onde a análise para."
tags: "hardware firmware ghidra engenharia reversa binario decompilador headless"
severity: info
references:
  - Ghidra — Getting Started | https://raw.githubusercontent.com/NationalSecurityAgency/ghidra/master/GhidraDocs/GettingStarted.md
  - Ghidra — repositório oficial | https://github.com/NationalSecurityAgency/ghidra
  - Ghidra — API javadoc | https://github.com/NationalSecurityAgency/ghidra/wiki/GhidraAPI_javadoc
  - radare2 — livro oficial | https://book.rada.re/
  - NationalSecurityAgency/ghidra — releases | https://github.com/NationalSecurityAgency/ghidra/releases
---

Depois que a análise de firmware extrai um sistema de arquivos, o que sobra são
binários: um kernel, um `busybox`, serviços proprietários e, frequentemente,
um único executável que faz tudo. Abrir isso num decompilador é a etapa em que
a vulnerabilidade deixa de ser hipótese e vira função, endereço e argumento.
Este documento é sobre o **método** dessa etapa com Ghidra — e sobre por que a
maioria das análises automaticamente "completas" está errada no início.

O Ghidra é um *framework* de engenharia reversa de software mantido pela
National Security Agency, distribuído sob Apache 2.0, com desmontagem,
decompilação, grafos e scripting em Java ou Python. A análise de firmware é
uma das aplicações de engenharia reversa de software — sem ela é impossível
entender como o binário toma decisões.

## 1. O que você precisa saber antes de abrir o binário

Três informações, todas obtidas fora do Ghidra:

1. **Arquitetura e ordem de bytes.** `file binário` no Linux normalmente
   responde, por exemplo, "ELF 32-bit LSB executable, ARM, EABI5". Se o
   firmware é um bloco sem cabeçalho (uma imagem de flash crua), é preciso
   descobrir o *entry point* e o endereço de carga — normalmente no datasheet
   do SoC ou no layout da flash.
2. **Endereço base (*image base*).** Firmware é frequentemente linkado para
   rodar num endereço de memória específico. Carregar no endereço errado
   desalinha todos os ponteiros: strings aparecem fragmentadas e as chamadas
   indiretas viram lixo. Esse é o erro número um.
3. **Endianness do alvo.** Um ARM big-endian carregado como little-endian
   produz um binário que "quase" faz sentido — o pior tipo de erro.

A documentação do Ghidra é explícita sobre um detalhe que morde em firmware
embarcado: *the image base may not be changed to an address which falls within
an existing memory block*. Ou seja: acerte o endereço no momento da importação
ou remova/reimporte o bloco — não tente "corrigir depois".

## 2. Importação: escolher a linguagem certa

No Ghidra, o *processor/language* é identificado durante a importação. Para o
firmware que não é ELF/Mach-O/PE, o Ghidra oferece a opção de importar como
**Raw Binary** e pedir a arquitetura manualmente. Nessa tela você declara:

- a família de processador (ARM Cortex, MIPS, Xtensa, AVR...);
- a variante e o tamanho do endianness;
- o endereço base.

Prefira sempre importar o ELF quando ele existe. O ELF carrega tabela de
símbolos, seções e o endereço correto — três coisas que você teria de
reconstruir à mão.

## 3. A primeira hora: fazer o Ghidra "entender" o binário

Binário de firmware chega sem símbolos, com funções reconhecidas apenas por
padrão de código. O objetivo da primeira hora não é entender a lógica: é
reduzir o ruído.

Ordem que funciona:

1. **Deixe a autoanálise rodar** e abra a janela de *Functions*. Se o número de
   funções for absurdo (milhares num binário de 200 KB), a arquitetura ou o
   endereço base estão errados. Pare e volte ao passo 1.
2. **Localize o ponto de entrada.** `entry` normalmente está na lista. A partir
   dele, siga até a função de inicialização.
3. **Reconstrua as strings.** Em firmware, string é quase sempre a melhor pista:
   caminhos de arquivo, comandos de shell, nomes de campos de configuração,
   URLs de atualização. Use a janela de *Defined Strings* e siga a referência
   de cada string até a função que a usa. Funções que referenciam
   `system`, `popen`, `execve`, `sprintf` e `memcpy` são candidatas naturais.
4. **Resolva as chamadas externas.** Em firmware estático, `system` e `printf`
   aparecem sem nome. Renomeie as funções cujos corpos você reconhece; cada
   renomeação propaga o entendimento para as chamadas.
5. **Escreva o mapa de dados globais.** Endereço de configuração, tabela de
   comandos, buffers fixos: identificá-los agora economiza horas depois.

## 4. Ler o decompilador com ceticismo

O decompilador do Ghidra produz C que **parece** compilável e frequentemente
não é. Ele é um resumo, não a verdade. Sinais de que a interpretação está
errada:

- `undefined4` e `in_FP` aparecendo em assinaturas;
- variáveis com nomes como `uVar12` que nunca fazem sentido no contexto;
- chamadas cujo número de argumentos não fecha;
- `switch` com casos que caem todos no mesmo bloco.

Antes de concluir uma vulnerabilidade a partir do decompilador, confirme na
**listagem de assembly**. Um `strcpy` seguido de buffer de tamanho fixo é
suficiente para suspeita; para afirmar exploração, você precisa do tamanho
real na pilha, que vem do assembly e da convenção de chamada.

## 5. Fluxo de análise de firmware, na prática

Um padrão que se repete em roteadores, câmeras e dispositivos IoT:

1. achar a função que trata a requisição HTTP ou o protocolo proprietário;
2. seguir até o *parser* do campo;
3. medir os limites do `memcpy`/`strcpy`;
4. verificar se há verificação de tamanho em qualquer camada;
5. localizar a *stack canary* (se houver) e o estado de NX/PIE no binário.

Esse parâmetro final — NX, PIE, canary — decide se a falha é explorável. Em
firmware embarcado é comum encontrar binários compilados sem canary e sem ASLR,
o que transforma um overflow simples numa exploração direta. Verificar isso é
parte da análise, não um detalhe posterior.

## 6. Automatizar: o modo headless

O Ghidra roda em modo *headless* (lote), controlado por
`<GhidraInstallDir>/support/analyzeHeadless`. A documentação oficial aponta o
arquivo `analyzeHeadlessREADME.html` como referência completa. É o modo
indicado quando você tem dezenas de binários de um mesmo firmware e quer um
resultado consistente e repetível, sem abrir GUI para cada um.

Vantagens reais:

- a mesma análise, com os mesmos passos, em todos os binários;
- scripts (Java ou Python via PyGhidra) podem exportar strings, funções e
  referências para CSV, alimentando uma base comparável;
- permite rodar em servidor sem interface gráfica.

Limite: análise automática **não substitui** a leitura humana. Ela reduz o
trabalho de triagem; a conclusão sobre explorabilidade continua exigindo que
alguém leia o fluxo.

## 7. Quando não é Ghidra

`radare2` (e a GUI Cutter) é a alternativa de linha de comando, com o livro
oficial em `book.rada.re` documentando o modelo de comandos. Vantagens: leve,
scriptável em shell, rápido para triagem. Desvantagem: o decompilador não tem
a mesma profundidade do Ghidra na versão livre.

Para binários grandes, comparar o resultado dos dois é uma forma barata de
detectar interpretação errada — se as duas ferramentas discordam sobre o
tamanho de um buffer, uma delas está com o endereço base errado.

## 8. O que roda sem hardware

**Tudo neste documento roda sem hardware.** Análise de binário é a parte da
trilha de hardware que é 100% software: o firmware é um arquivo, o Ghidra é um
programa, e nenhum dos dois exige que você tenha o aparelho na mesa.

Requisito de máquina, segundo a documentação do Ghidra: 4 GB de RAM, 1 GB de
disco para a instalação, um JDK 64-bit suportado (JDK 25 na versão 12.x) e,
para PyGhidra, Python 3.9 a 3.15. Um binário de 4 MB de firmware é analisável
numa máquina modesta.

## 9. Limites

Este documento não cobre emulação dinâmica (rodar o binário do firmware no
host), que exige uma etapa própria com `qemu-user` e bibliotecas do sistema de
arquivos extraído. Não cobre escrita de *exploit* para o alvo — a exploração
depende do alvo e da cadeia primitiva, e não é o mesmo problema em todas as
arquiteturas. E não cobre descompilação de código ofuscado de forma
deliberada, que é um problema aberto mesmo com as melhores ferramentas.