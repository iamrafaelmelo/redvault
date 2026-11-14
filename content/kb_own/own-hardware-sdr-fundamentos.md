---
slug: own-hardware-sdr-fundamentos
title: "SDR: fundamentos de rádio definido por software e prática sem transmissor"
category: hardware-rf
summary: "Como um rádio definido por software funciona: front-end de RF, amostragem em quadratura (I/Q), taxa de amostragem e as modulações que aparecem em dispositivos de consumo. Inclui exercícios que rodam só com software e a separação explícita do que exige um receptor físico."
tags: "hardware sdr radio iq amostragem modulacao goertzel rtl-sdr gnuradio"
severity: info
references:
  - Wikipedia — Software-defined radio | https://en.wikipedia.org/wiki/Software-defined_radio
  - RTL-SDR — Quick Start Guide | https://www.rtl-sdr.com/rtl-sdr-quick-start-guide/
  - GNU Radio Manual — Usage | https://www.gnuradio.org/doc/doxygen/page_usage.html
  - osmocom/rtl-sdr — código-fonte das ferramentas | https://github.com/osmocom/rtl-sdr
  - Wikipedia — Quadrature amplitude modulation | https://en.wikipedia.org/wiki/Quadrature_amplitude_modulation
---

Rádio definido por software (SDR) é o rádio em que os componentes que
normalmente são analógicos — mixer, filtro, amplificador, modulador,
demodulador, detector — passam a ser implementados em software, rodando num
computador ou sistema embarcado. Praticamente todo dispositivo sem fio de
consumo (fone Bluetooth, sensor de porta, controle de garagem, medidor de
energia) transmite por modulações que podem ser analisadas com um receptor SDR
barato e software livre.

Este documento cobre o modelo mental e a prática que **não depende de
transmitir nada**. Transmissão é outro problema, com outro risco legal.

## 1. A cadeia de recepção

Um receptor SDR básico é: antena → front-end de RF → amostragem → processamento
em software.

- **Antena** — converte campo eletromagnético em tensão. A banda de operação
  depende do comprimento e da geometria; não existe antena que seja boa em
  tudo, e a antena é, na prática, o componente que mais limita o resultado.
- **Amplificador de baixo ruído (LNA)** — o sinal chega na ordem de
  sub-microvolt, e o conversor analógico-digital real não tem faixa dinâmica
  para isso. O LNA vem antes, e é ele que define o piso de ruído.
- **Filtro passa-banda** — sinais espúrios competem com o sinal desejado
  dentro da faixa dinâmica do amplificador. Filtrar antes reduz distorção, ao
  custo de flexibilidade.
- **Conversor analógico-digital (ADC)** — amostra o sinal. A faixa dinâmica
  do ADC é o limite físico de tudo o que vem depois.
- **Software** — faz o resto: filtragem, demodulação, decodificação.

A divisão de responsabilidade é a lição central: **o software só melhora o que
o ADC entregou**. Nenhum processamento recupera informação que ficou abaixo do
piso de ruído.

## 2. I/Q: por que dois canais e não um

O ADC não amostra o sinal de RF diretamente na maioria dos rádios baratos. Ele
amostra duas versões do sinal, defasadas de 90°: **I** (em fase) e **Q**
(quadratura). Juntas, elas formam um número complexo por amostra.

Isso permite representar **amplitude e fase ao mesmo tempo**, e é o que torna
possível distinguir frequências acima e abaixo da frequência central do
receptor. Um único canal real não distingue as duas — e é por isso que rádios
de conversão direta têm o artefato de espelho em torno do centro. O RTL-SDR,
por exemplo, tem um *spike* permanente no meio do espectro, e a correção disso
é feita por software (a opção "Correct IQ").

Consequências práticas de I/Q:

- a banda observável é `taxa_de_amostragem`, e ela é dividida entre metade
  acima e metade abaixo da frequência central;
- toda a matemática que se aplica é a de números complexos;
- um arquivo de captura bruta de RTL-SDR é uma sequência de pares de bytes
  `I,Q` sem cabeçalho — o formato é 8 bits sem sinal por componente, e a taxa
  de amostragem não está dentro do arquivo: você a declara ao abrir.

## 3. Taxa de amostragem, largura de banda e duração

Um valor só significa três coisas dependentes:

| Você quer | Você controla | Consequência |
| --- | --- | --- |
| Largura de banda maior | taxa de amostragem maior | mais CPU, arquivo maior |
| Gravação mais longa | taxa menor ou mais disco | banda menor |
| Melhor relação sinal/ruído | ganho e filtro | risco de saturação |

Um rádio típico entrega 2,048 MSPS (mega-amostras por segundo), o que
corresponde a cerca de 2 MHz de banda de observação. Aumentar a taxa além do
que o aparelho suporta de forma estável produz perda de amostras, e perda de
amostras em protocolo síncrono significa **decodificação silenciosamente
errada** — o mesmo problema que um analisador lógico com taxa baixa.

## 4. Modulações que aparecem em dispositivos de consumo

| Modulação | Como aparece | Onde se encontra |
| --- | --- | --- |
| OOK (on-off keying) | portadora ligando e desligando | controle de portão, sensor de porta |
| ASK | amplitude variável | etiquetas e sensores baratos |
| FSK / GFSK | frequência salta entre dois valores | Bluetooth, muitos sensores sub-GHz |
| PSK | fase muda | sistemas mais robustos |
| QAM | amplitude e fase combinadas | Wi-Fi, links digitais |
| CSS | chirp de frequência | LoRa |
| OFDM | muitas subportadoras | Wi-Fi, LTE, DVB |

A distinção que mais rende no começo: **ASK/OOK** se vê no domínio do tempo
(amplitude), **FSK** se vê no domínio da frequência (a frequência desloca), e
**PSK/QAM** exigem constelação I/Q para fazer sentido.

## 5. Prática que roda sem receptor

Esta é a parte que importa para quem não tem dongle: é possível aprender a
cadeia inteira com sinal **gerado em software**.

**Sintetizar um sinal conhecido.** Gere amostras I/Q de um tom em
`f = 1 kHz` a uma taxa de `48 kHz` por 1 segundo, grave como pares de floats
ou de bytes, e decodifique. O exercício obrigatório: implementar o **algoritmo
de Goertzel** — um detector de tom único, que calcula a energia em uma
frequência específica sem fazer FFT completa:

```
k = arredondar(N * f_alvo / taxa)
ω = 2π·k/N
coef = 2·cos(ω)
s_prev2 = 0; s_prev1 = 0
para cada amostra x:
    s = x + coef·s_prev1 - s_prev2
    s_prev2 = s_prev1; s_prev1 = s
potência = s_prev1² + s_prev2² - coef·s_prev1·s_prev2
```

Se o tom sintetizado em 1 kHz produzir um pico de potência em `k`
correspondente a 1 kHz e nada em 3 kHz, a cadeia está correta. Esse é o teste
de sanidade que separa "eu entendi I/Q" de "eu copiei um comando".

**Sintetizar um sinal modulado.** Gere uma sequência OOK: portadora ligada por
`T` amostras, desligada por `T` amostras, formando os bits `1010...`. Tente
recuperá-la por detecção de envelope (magnitude de I/Q). O que você vai
descobrir sozinho: sem a taxa de símbolo correta, o envelope "funciona" pra
qualquer coisa, e o resultado é convincente e errado. Isso é exatamente o que
acontece com capturas reais.

**Analisar arquivos de amostra.** GNU Radio é a pilha de blocos de
processamento de sinal usada em SDR; a documentação de uso está no manual e na
wiki do projeto, e ele pode ler de arquivo em vez de hardware. Com ele, um
grafo *source de arquivo → bloco de demodulação → sink* roda sem nenhuma
antena.

**Captura real (exige equipamento).** A partir daqui é preciso um receptor
físico. Um RTL-SDR é a opção mais barata; ele é um conversor DVB-T reaproveitado
e, no Linux, exige que o driver de TV seja removido de serviço (os modos
`dvb_usb_rtl28xxu`). As ferramentas oficiais do projeto Osmocom têm semântica
verificável no código-fonte:

```bash
rtl_test                                  # testa o dispositivo
rtl_sdr -f 433920000 -s 2048000 -n 2048000 saida.iq
rtl_power -f 433M:435M:100k -i 10 sweep.csv
rtl_fm -f 433920000 -M am -s 48k -g 40 -
```

Os nomes de modulação aceitos por `rtl_fm` são `fm`, `wbfm`, `raw`, `am`,
`usb` e `lsb`; `raw` devolve pares I/Q de 16 bits. `rtl_power` produz CSV com
`data, hora, Hz baixo, Hz alto, passo, amostras, dBm...` — que é a base de um
gráfico de ocupação de espectro.

## 6. Limites legais e éticos

Recepção de sinais que trafegam no ar é uma coisa; **interferir** é outra.
Transmitir em banda licenciada sem autorização é ilegal na maioria das
jurisdições, e "só por um segundo" não muda isso. Mesmo recepção pode ser
restrita quando o conteúdo é protegido (comunicação privada de terceiros).

Para prática com transmissão, o caminho correto é ambiente isolado com
blindagem (gaiola de Faraday ou caixa blindada), potência mínima, e apenas
equipamento próprio. Nenhum exercício desta trilha exige transmissão.

## 7. O que este documento não cobre

Não cobre projeto de front-end de RF, nem escolha de antena por banda. Não
cobre protocolos proprietários específicos (Bluetooth, LoRa, Zigbee) — para
esses há documentos próprios nesta base. E não substitui o datasheet do
receptor: cada aparelho tem limites de ganho, de taxa e de faixa que precisam
ser consultados antes de concluir que "não há sinal".