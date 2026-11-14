---
slug: own-execucao-fileless-analise
title: "Execução fileless: por que não há arquivo para analisar"
category: malware-analysis
summary: "Execução fileless significa que o código malicioso existe apenas em memória ou em artefatos do próprio sistema — registro, tarefas agendadas, WMI. Este artigo separa as quatro formas reais (script em memória, injeção de processo, armazenamento em registro/WMI, uso de binários legítimos) e explica por que a análise começa por telemetria de processo e logs, não por um arquivo. Baseia-se na documentação do HackTricks sobre execução fileless no Linux e em Linux persistence, e em ATT&CK para nomear as técnicas."
tags: "malware fileless memoria injecao wmi registrador persistencia edr"
severity: info
references:
  - HackTricks — Execução fileless no Linux | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — Linux - Persistence | https://github.com/HackTricks-wiki/hacktricks
  - MITRE ATT&CK — técnicas de defesa evasiva e execução | https://attack.mitre.org/
  - Microsoft Learn — WMI e Windows Management Instrumentation | https://learn.microsoft.com/en-us/windows/win32/wmisdk/wmi-start-page
  - SigmaHQ — regras de detecção baseadas em log | https://github.com/SigmaHQ/sigma
---

Existe uma confusão comum em torno do termo. "Fileless" não significa "não há
artefato". Significa que **o código executado nunca existiu como arquivo
executável em disco**. O conteúdo malicioso ou está na memória de um processo
legítimo, ou está armazenado num contêiner que não é um executável — chave de
registro, repositório WMI, tarefa agendada, variável de ambiente.

A consequência prática é direta: qualquer plano de resposta baseado em "coletar
o binário e submeter ao motor de antivírus" não funciona aqui.

## As quatro formas

### 1. Script carregado em memória

PowerShell, Python ou bash recebem comando de um servidor e o interpretam
diretamente. O processo pai é legítimo. Não há arquivo do payload; existe no
máximo o histórico do interpretador, e apenas se ele foi habilitado.

Em Linux, o equivalente é uma combinação de `curl | sh`, `eval` de string vinda
da rede e uso de `memfd` — descritores de arquivo anônimos que existem sem
caminho no sistema de arquivos. O documento de execução fileless no Linux
descreve justamente o mecanismo `memfd`, onde o binário é criado em memória e
executado a partir de `/proc/<pid>/exe`, sem nome em `/tmp`.

### 2. Injeção em processo legítimo

O código é escrito no espaço de endereçamento de um processo que já roda
(regraves, `lsass`, `svchost`). O processo aparece na lista com o nome
correto — e é isso que engana o analista que só lê a lista de tarefas. As
técnicas de injeção estão mapeadas em ATT&CK sob a família de execução/injeção
de processo.

### 3. Armazenamento fora do executável

- **Registro do Windows** — valores que contêm script, carregados por
  `mshta`, `rundll32` ou `wmic`.
- **Repositório WMI** — classes de eventos que disparam código agendado; a
  administração remota via WMI é documentada pela Microsoft e é legítima por
  natureza, o que torna o uso malicioso indistinguível pelo nome.
- **Tarefas agendadas**, **serviços** e **chaves de persistência** descritas na
  página de persistência do HackTricks.

### 4. Binário legítimo como primeiro estágio

O "malware" é o argumento passado a uma ferramenta assinada. Nada no binário é
malicioso; a linha de comando é. É o caso de `certutil` baixando um arquivo ou
`bitsadmin` transferindo conteúdo.

## Onde olhar

Sem um arquivo, o objeto de análise passa a ser o **evento**:

| Fonte (Linux) | O que responde |
| --- | --- |
| `/proc/<pid>/maps` | quais bibliotecas e regiões anônimas o processo mapeou |
| `/proc/<pid>/fd` | descritores abertos, incluindo `memfd` sem nome |
| `/proc/<pid>/cmdline` | composição exata da linha de comando |
| `auditd` | execução, acesso a arquivo e chamadas relevantes |
| `journalctl` | sequência temporal de serviços e logins |

| Fonte (Windows) | O que responde |
| --- | --- |
| Event ID 4688 | criação de processo com linha de comando |
| Event ID 4104 | bloco de script PowerShell registrado (quando habilitado) |
| Sysmon | injeção, carregamento de imagem e acesso a rede do processo |
| Log do WMI | assinatura e consumo de eventos |

A lição operacional: **habilite a telemetria antes de precisar dela**. Em um
host sem `auditd`, sem log de script do PowerShell e sem Sysmon, não existe
análise fileless possível — existe apenas suposição.

## Reconstruir a sequência

A investigação é uma montagem de linha do tempo, não uma leitura de código:

1. Qual processo criou o processo suspeito, com que linha de comando e em que
   horário.
2. Que conexões de rede esse PID abriu, para qual destino.
3. Que arquivos ele abriu, mesmo que nenhum tenha sido executado de disco.
4. Que persistência foi criada depois — chave, tarefa, serviço, cron.

Só a etapa 4 dá o que remover. Desligar o host antes de documentá-la apaga a
única evidência de como a infecção voltaria.

## O que não se pode afirmar

Sem arquivo, não há hash para consultar em repositório público. Portanto:

- não se afirma família de malware a partir de um nome de processo;
- não se afirma "limpo" após remover a persistência sem revisar a memória dos
  processos já injetados;
- não se atribui o comportamento a uma linha de comando legítima específica sem
  comparar com o uso esperado dela naquele ambiente.

Essas três frases são o que separa um laudo honesto de uma narrativa.