---
slug: own-forense-memoria-volatility
title: "Forense de memória com Volatility 3: símbolos, plugins e o que a RAM prova"
category: forensics-memory
summary: "Dump de memória só é analisável com a tabela de símbolos do kernel exato. Este artigo explica o modelo de símbolos do Volatility 3, a ordem em que se executam os plugins (informação do sistema, processos, rede, injeção), o que cada família de plugin responde e o que a memória NÃO prova — porque páginas ausentes ou paginadas em disco geram conclusões falsas."
tags: "forense memoria volatility dump ram simbolos processos injecao"
severity: info
references:
  - Volatility 3 — documentação oficial | https://volatility3.readthedocs.io/en/latest/
  - Volatility 3 — repositório e plugins | https://github.com/volatilityfoundation/volatility3
  - HackTricks — Análise de dump de memória | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — Dump de Memória do macOS | https://github.com/HackTricks-wiki/hacktricks
  - Velociraptor — coleta de memória e artefatos em escala | https://github.com/Velocidex/velociraptor
---

A memória de um sistema é o único lugar onde processos em execução, conexões
abertas e código injetado aparecem juntos. Um arquivo em disco diz o que poderia
rodar; a RAM diz o que estava rodando. Por isso o dump de memória é, em
incidente com suspeita de execução fileless ou injeção, a primeira aquisição.

O problema é que a RAM isolada é ilegível. Ela é uma sequência de bytes sem
significado até se descobrir **onde cada estrutura do kernel começa**.

## O modelo de símbolos do Volatility 3

O Volatility 3 organiza a análise em duas camadas:

- **camada de dados** — move bytes: converte um arquivo cru, um dump de
  hibernação ou um crash dump em espaço de endereçamento.
- **camada de tradução** — interpreta esses bytes com a definição das estruturas
  do sistema operacional, obtida de uma **tabela de símbolos**.

Sem a tabela correta, a tradução falha e os plugins retornam vazio. Isso não
significa "memória limpa"; significa "memória não interpretada". Antes de
concluir qualquer coisa, é preciso ver:

```
vol -f dump.raw windows.info
```

A saída informa a versão do kernel e se o símbolo foi carregado. Se o símbolo
não estiver disponível, o Volatility tenta obter a tabela por download para a
versão de kernel detectada. Em ambiente offline, é preciso baixar a tabela
previamente e apontá-la. Rode essa etapa **antes** de qualquer plugin de
análise: um plugin que "não encontra nada" por falta de símbolo é confundido
facilmente com ausência de comprometimento.

## Ordem dos plugins

A sequência importa porque cada etapa orienta a próxima.

### 1. Informação do sistema

`windows.info` ou `linux.pslist` básico: versão, arquitetura, uptime
aproximado, fuso. Toda hora citada no laudo é relativa a isso.

### 2. Processos

`windows.pslist` lista processos a partir das listas encadeadas do kernel.
`windows.pstree` monta a hierarquia pai/filho — é a comparação com a árvore
esperada que revela um processo legítimo cujo pai deveria ser `services.exe`
e é, na verdade, `winword.exe`.

### 3. Processos ocultos

A comparação entre o que o kernel lista e o que o sistema "sabe" que existe é o
teste clássico de rootkit. `windows.psscan` varre a memória em busca de
estruturas de processo sem usar a lista encadeada; o que aparece nele e falta
em `pslist` é um processo **desvinculado** — escondido de ferramentas que usam
a lista.

Ressalva importante: processo desvinculado também aparece em término de
execução normal, quando a estrutura ainda não foi liberada. Um único
desvinculado não é prova; o conjunto, sim.

### 4. Rede

`windows.netscan` cruza conexões com o processo dono. Este é o plugin que
converte "havia tráfego" em "o processo X falava com o endereço Y", e é o que
sustenta atribuição. Sem ele, uma conexão de saída anômala é um fato sem autor.

### 5. Código em memória

`windows.malfind` procura regiões de memória com permissão de execução e
conteúdo não mapeado a um arquivo — o padrão de injeção. Ele aponta, não
condena: JIT (Java, .NET, navegadores) também gera regiões executáveis
anônimas. A triagem é manual.

### 6. Extração

Depois de localizar o processo, extrai-se o executável da memória
(`windows.dumpfiles`, ou o dump de região). Esse dump é o artefato que se
submete a YARA e a análise estática — e é o único caminho quando não existe
arquivo em disco.

## O que a memória não prova

- **Páginas ausentes.** Partes da memória podem ter sido paginadas para disco.
  Um padrão que "não aparece" pode estar na página que não foi capturada. A
  conclusão correta é "não observado neste dump", não "não existia".
- **Ordem exata.** A memória não guarda tempo por evento. Ela guarda estado.
  Reconstruir sequência requer logs e artefatos de disco.
- **Autoria.** Saber qual processo enviou dados não diz quem o operou. A
  atribuição a uma pessoa exige evento de login, sessão, console — não memória.
- **Estado anterior.** Um dump é uma fotografia. O que aconteceu antes daquela
  foto está em outro lugar.

## Coleta que vale a pena

O dump só serve se for inteiro. Coletar memória de host comprometido com
ferramenta executada no próprio host tem risco: o malware pode alterar o
resultado. Quando possível, colete por agente externo ou hypervisor. Registre a
ferramenta, a versão e o hash do arquivo gerado, sob as mesmas regras de cadeia
de custódia de qualquer evidência.