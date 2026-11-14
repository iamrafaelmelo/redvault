---
slug: own-hardware-analisador-logico-sigrok
title: "Analisador lógico com sigrok: do sinal bruto à mensagem decodificada"
category: hardware-signals
summary: "Fluxo de trabalho com analisador lógico e sigrok/PulseView: taxa de amostragem, trigger, captura binária, decodificadores empilhados e exportação. Explica por que capturar primeiro e decodificar depois, e como usar a saída decodificada como evidência. Inclui o que exige hardware e o que roda sobre arquivos de amostra."
tags: "hardware sigrok pulseview analisador logico uart spi i2c decodificador"
severity: info
references:
  - sigrok — sigrok-cli manual | https://sigrok.org/wiki/Sigrok-cli
  - sigrok — Protocol decoders | https://sigrok.org/wiki/Protocol_decoders
  - sigrok — Input/output formats | https://sigrok.org/wiki/Input_output_formats
  - sigrok — Supported hardware | https://sigrok.org/wiki/Supported_hardware
  - PulseView | https://sigrok.org/wiki/PulseView
---

Um analisador lógico registra o estado de pinos digitais ao longo do tempo. O
valor dele não está em "ver o sinal": está em transformar uma sequência de
níveis em **mensagens decodificadas** que podem ser citadas num relatório e
comparadas entre capturas.

O sigrok é a pilha de software livre que faz essa transformação, e ela é
dividida em três camadas bem separadas:

- **libsigrok** — fala com o hardware e com formatos de arquivo;
- **libsigrokdecode** — contém os decodificadores de protocolo (Python);
- **front-ends** — `sigrok-cli` (linha de comando) e PulseView (gráfico).

Essa separação é a razão pela qual o trabalho pode ser feito em duas etapas:
capturar com o hardware e decodificar depois, offline.

## 1. Por que capturar primeiro

A documentação do `sigrok-cli` é explícita: ele é uma aplicação de thread
única, e carga demais durante a captura faz a sessão terminar cedo. A
recomendação oficial é **capturar em formato binário e processar depois**,
porque os outros formatos geram sobrecarga grande na escrita.

Para capturas de alta taxa, a documentação sugere ainda usar buffer e
compressão no meio do caminho:

```bash
sigrok-cli --driver saleae-logic-pro \
  --channels 0=Vcc,1=CS,2=MISO,3=MOSI,4=CLK \
  --output-format binary --config samplerate=50m --continuous \
  | mbuffer | lz4 | pv > data.lz4
```

O que essa linha ensina, independente do modelo de aparelho:

- cada canal é nomeado (`0=Vcc`), e o nome é o que o decodificador vai usar;
- a taxa é declarada (`samplerate=50m`);
- a saída é binária e contínua;
- a captura pode ser comprimida em tempo real.

## 2. A taxa de amostragem é uma decisão, não um padrão

Regra prática, confirmada pela teoria de amostragem: a taxa precisa ser
**várias vezes** o clock do barramento — não o dobro. Guias de "Nyquist" valem
para reconstruir senoidal, não para identificar bordas em protocolo síncrono.

Ordem de grandeza que serve como ponto de partida:

| Barramento | Clock típico | Taxa de captura razoável |
| --- | --- | --- |
| UART | 9.600–921.600 baud | 4–10× a taxa de símbolo |
| I²C (padrão) | 100 kHz | ≥ 1 MHz |
| I²C (fast) | 400 kHz | ≥ 4 MHz |
| SPI (padrão) | 10–25 MHz | ≥ 50 MHz |
| JTAG/SWD | 1–20 MHz | ≥ 4× o TCK/SWCLK |

Se a taxa for baixa demais, o decodificador **não erra com aviso**: ele
constrói uma interpretação plausível e errada. Por isso, ao ver dados
inesperados, a primeira hipótese é "a taxa de amostragem foi baixa", não
"o firmware está estranho".

## 3. Descoberta de dispositivos e de canais

```bash
sigrok-cli --scan
sigrok-cli --driver fx2lafw --show
```

`--scan` lista o que foi detectado automaticamente. Dispositivos que falam por
porta serial **não** são detectados assim: eles precisam da opção `conn`, por
exemplo `--driver=ols:conn=/dev/ttyACM0`. Dispositivos USB que compartilham
VID/PID também aceitam `conn` no formato `vendor.product` ou `barramento.endereço`.

`sigrok-cli --show` mostra os canais e as opções do aparelho escolhido — e é
assim que você descobre o *nome* dos canais, porque `--channels` usa os nomes
como aparecem no invólucro do hardware, não uma numeração inventada.

## 4. Trigger: capturar o evento, não o silêncio

Um trigger por canal inteiro (`0=1`) gasta memória esperando um estado que pode
nunca chegar. Triggers por borda são o que faz a captura ficar útil:

- `r` — borda de subida (equivalente a `0` → `1`);
- `f` — borda de descida;
- `e` — qualquer transição.

Exemplo de captura curta esperando a borda de subida do clock com chip select
ativo:

```bash
sigrok-cli --driver ols:conn=/dev/ttyACM0 \
  --config samplerate=10m --channels 0-3 --wait-trigger \
  --triggers 0=1,1=r,2=0,3=1 --time 100 --output-format bits
```

`--wait-trigger` suprime os dados anteriores ao trigger. `--time 100` limita a
captura a 100 ms depois dele.

## 5. Decodificar: empilhar decodificadores

Esta é a parte que transforma amostra em mensagem. O `sigrok-cli` aceita:

- `-P decodificador` — um decodificador por opção; vários `-P` rodam em
  paralelo;
- `-P a,b` — empilha `a` alimentando `b` (o segundo consome a saída do
  primeiro);
- `-A` — filtra quais *anotações* aparecem;
- `-M` — mostra a saída de metadados do decodificador;
- `-B` — extrai dados brutos do decodificador (bytes, PCAP, WAV...) para
  stdout, para uso em outro programa.

Exemplos da documentação oficial, que mostram o padrão de uso:

```bash
sigrok-cli -i captura.sr -P i2c
sigrok-cli -i captura.sr -P uart:baudrate=115200:parity_type=odd
sigrok-cli -i captura.sr -P spi:wordsize=9:miso=1:mosi=5:clk=3:cs=0
sigrok-cli -i captura.sr -P i2c,eeprom24xx
sigrok-cli -i captura.sr -P uart:tx=D0:rx=D1 -P timing:data=D2
```

Detalhe importante do funcionamento: qualquer opção passada ao decodificador
que ele **não** reconhece é interpretada como atribuição de canal. É assim que
`spi:miso=1` funciona sem existir uma opção chamada `miso`. E, na linha de
comando, **não há correspondência por nome** de canal: as trilhas do arquivo
casam com a ordem dos sinais do decodificador, ou você mapeia explicitamente.

## 6. O que existe pronto

O sigrok mantém mais de uma centena de decodificadores, incluindo, entre os
relevantes para hardware:

| Protocolo | Entrada | Uso típico |
| --- | --- | --- |
| UART | lógica | console serial, mensagens de boot |
| SPI | lógica | flash, sensores, rádio |
| SPI flash/EEPROM | SPI | tráfego com chips 25xx |
| I²C | lógica | EEPROM, RTC, sensores, PD |
| 1-Wire | lógica | iButton, sensores |
| JTAG (1149.1) | lógica | cadeia de depuração |
| SWD | lógica | depuração ARM de dois fios |
| cJTAG | lógica | JTAG compacto (1149.7) |
| ARM ETMv3, ITM, TPIU | UART/lógica | trace de instrução |
| OOK | lógica | rádio com chaveamento on-off |
| EM4100, T55xx | lógica | RFID de 125 kHz |
| Wiegand | lógica | controle de acesso |
| CAN | lógica | barramento automotivo |

Empilhar é o que dá o salto de qualidade: decodificar `spi` e depois
`spiflash` mostra comando, endereço e dados; decodificar `i2c` e depois
`eeprom24xx` mostra o que a EEPROM devolveu em vez de bytes soltos.

## 7. Evidência: o que guardar

Uma captura vira evidência quando outra pessoa consegue refazê-la. O conjunto
mínimo:

- arquivo de sessão (`.sr`) ou o binário original **mais** os parâmetros de
  importação (`numchannels`, `samplerate`);
- taxa de amostragem, canais usados e seus nomes;
- trigger exato e duração da captura;
- a linha `-P` completa, com todas as opções do decodificador;
- versão do sigrok (`sigrok-cli --version`);
- para cada mensagem citada, o número de amostra (use
  `--protocol-decoder-samplenum`).

Sem a taxa e sem a linha `-P`, a interpretação não é reproduzível e não
serve como prova técnica.

## 8. Trabalhar sem o hardware

O que **exige equipamento físico**: qualquer captura real. Nenhum software
substitui a conexão elétrica.

O que **não exige**: toda a etapa de decodificação. O sigrok lê arquivos em vez
de dispositivos (`-i arquivo`), aceita formatos de entrada intercambiáveis
(`-I binary:numchannels=4:samplerate=1mhz`, VCD por stdin, WAV) e o
`sigrok-cli` aceita ainda o driver `demo`, um dispositivo virtual com canais
lógicos e analógicos que permite praticar a sintaxe e o fluxo de decodificação
sem nenhum aparelho ligado. Arquivos de amostra reais de diversos protocolos
são publicados no repositório `sigrok-dumps` do projeto.

Na prática: é possível aprender o fluxo inteiro, escrever o relatório e testar
todas as linhas de comando apenas com o driver `demo` e arquivos de amostra —
e só a aquisição em si depende de comprar ou emprestar um analisador.

## Limites

Este documento não cobre modelagem de sinal analógico, nem a escolha entre
analisador lógico e osciloscópio para uma medida específica (que depende de
banda e de amplitude). Também não cobre proteção elétrica do alvo: ligar um
analisador de 3,3 V num alvo de 5 V é problema de hardware, e a resposta está
no documento de JTAG/UART, no capítulo de níveis lógicos.