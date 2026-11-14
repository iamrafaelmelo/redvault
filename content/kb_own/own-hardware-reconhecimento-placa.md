---
slug: own-hardware-reconhecimento-placa
title: "Reconhecimento de placa: identificar componentes e pontos de teste antes de encostar num fio"
category: hardware-recon
summary: "Metodologia de inspeção de placa de circuito impresso: leitura de silk, identificação de encapsulamentos, localização de flash SPI/eMMC, procura de pontos de teste de UART e JTAG, e o registro que permite repetir o trabalho. Inclui o que dá para fazer só com foto e o que exige equipamento."
tags: "hardware pcb placa uart jtag spi eeprom encapsulamento reconhecimento datasheet"
severity: info
references:
  - Wikipedia — Printed circuit board | https://en.wikipedia.org/wiki/Printed_circuit_board
  - Wikipedia — Datasheet | https://en.wikipedia.org/wiki/Datasheet
  - sigrok — Protocol decoders | https://sigrok.org/wiki/Protocol_decoders
  - Wikipedia — Serial Peripheral Interface | https://en.wikipedia.org/wiki/Serial_Peripheral_Interface
  - KiCad — PCB design | https://www.kicad.org/discover/pcb-design/
---

O reconhecimento de placa é a etapa que decide se o resto do trabalho vai render
fruto ou danificar o alvo. Antes de soldar um fio, de girar um parafuso de
segurança ou de cortar uma trilha, o objetivo é responder a quatro perguntas:
**o que é esta placa**, **o que ela expõe**, **onde estão os pontos de teste** e
**o que eu arrisco perder se errar**.

Este documento é de metodologia. Os procedimentos técnicos de cada barramento
estão nos documentos JTAG, SPI, I2C e UART desta base de conhecimento; aqui o
assunto é como chegar até eles.

## 1. Sic transit: ler o que a placa já diz

Uma placa de circuito impresso carrega mais informação do que parece. A
serigrafia (o *silk screen*) normalmente traz designadores de componente —
`R12`, `C4`, `U7`, `J3` —, o nome de cada malha e a versão da revisão. As regras
de designação são razoavelmente estáveis entre fabricantes:

| Prefixo | Componente | Por que importa |
| --- | --- | --- |
| `U` | circuito integrado | o processador, a flash, o chip de rádio |
| `J`, `P`, `CN` | conector | onde existe contato físico acessível |
| `TP` | test point | o alvo ideal: cobre exposto, sem solda |
| `Y`, `X` | cristal/oscilador | indica onde está o clock e os sinais críticos |
| `Q` | transistor/MOSFET | chaves de alimentação e habilitadores |
| `F` | fusível | nunca é decorativo; indica a linha de energia |

Nem toda placa é rotulada. Placas baratas costumam ter apenas `U1`, `U2`, `U3`
em sequência. Nesse caso, o trabalho passa a ser por dedução: quem tem mais
trilhas conectadas, quem está perto do conector de alimentação, quem tem o maior
número de pinos.

**Só com foto:** boa parte desta etapa pode ser feita sobre fotografias em alta
resolução da placa (frente e verso, com boa iluminação lateral). Você consegue
listar designadores, ler marcações nos chips e mapear conectores sem tocar no
hardware.

**Exige equipamento:** confirmar continuidade, medir tensão de alimentação e
identificar pinos sem rótulo exige multímetro. Identificar trilhas sob a máscara
de solda exige microscópio ou lupa; em placas densas, contaminação entre pinos
é o erro mais comum do iniciante.

## 2. Identificar o encapsulamento antes de identificar o chip

O mesmo chip pode existir em encapsulamentos diferentes, e o encapsulamento
define o que é fisicamente possível fazer. Os que aparecem em equipamentos de
consumo:

- **SOIC/SOP** — pinos espaçados, soldáveis com ferro comum. É o melhor cenário.
- **TSSOP/MSOP** — mais estreito, mas ainda acessível com fluxo e ponta fina.
- **QFN/DFN** — pinos embaixo do corpo; na prática só com estação de ar quente.
- **BGA** — esferas sob o chip, invisíveis; sem raio-X não há acesso direto.
- **WSON/LGA** — corpo rente à placa, sem pinos laterais.
- **CSP** — o mais hostil: o passo é menor que a ponta de um ferro.

A consequência prática é direta: se a flash SPI é um SOIC-8, a leitura pode ser
feita no lugar (in-circuit) ou removendo o chip com ar quente. Se é um BGA
empilhado no SoC, a leitura direta não existe — o caminho passa por
barramento exposto, porta de depuração ou modo de boot do fabricante.

## 3. Ler a marcação e chegar ao datasheet

Os chips trazem um código de topo (*top marking*) que raramente é o nome
comercial. `25Q64` é uma família de flash SPI de 64 Mbit; `W25Q64JVSSIQ` é o
part number completo. O datasheet é a fonte primária de pinagem, de tensão e de
comandos aceitos — e é ele que diz, por exemplo, se a flash responde a
`05h`/`03h` ou a `0Bh` para leitura rápida.

Fluxo de identificação, na ordem em que rende menos erro:

1. Leia o código inteiro com a lupa; anote linha por linha, inclusive o lote.
2. Procure o código de topo no site do fabricante e confira o *package
   marking* no datasheet de cada família.
3. Confirme o tamanho em bits e a tensão (3,3 V e 1,8 V não são
   intercambiáveis, e ligar 3,3 V num chip de 1,8 V o queima).
4. Confirme o datasheet **do encapsulamento certo**: a pinagem muda entre SOIC-8
   e WSON-8 na mesma família.

**Só com foto:** os passos 1 a 3.

**Exige equipamento:** medir a tensão real no pino `VCC` antes de energizar
qualquer adaptador. Sem essa medida, o adaptador é uma aposta.

## 4. Encontrar os pontos de teste

A ordem de busca que costuma funcionar, do menos invasivo ao mais:
conector exposto → pad de teste rotulado `TP` → pad sem rótulo → via →
pino de componente → trilha raspada.

Para UART, o ponto de partida é procurar pares de pads próximos a um conector
de serviço, a um botão de reset ou ao SoC, com trilhas curtas. Três pads em
linha com espaçamento uniforme e um quarto mais largo (terra) é o padrão mais
comum. Confirmar qual é `TX`, `RX` e `GND` exige multímetro e, idealmente,
osciloscópio ou analisador lógico — não se adivinha.

Para JTAG/SWD, o raciocínio é o mesmo, mas com quatro a seis linhas. O
documento JTAG desta base apresenta a abordagem de identificação por
resistência e por padrão de sinais; **ela exige multímetro e, na maioria dos
casos, equipamento de captura**.

Para flash SPI, o alvo é o chip de 8 pinos (ou 16) próximo ao SoC, com trilhas
que vão direto ao processador. O documento SPI cobre os detalhes elétricos.

## 5. Registrar para poder repetir

Um reconhecimento que não é registrado é trabalho perdido na segunda visita.
O registro mínimo:

- Fotos em alta resolução, frente e verso, com escala (uma régua no quadro).
- Lista de designadores com o código lido e o part number deduzido.
- Mapa de conectores com numeração de pino e função confirmada ou provável.
- Tabela de pontos de teste: posição, função hipótese, como foi confirmada
  (medida, datasheet ou suposição), e o risco de solda.
- Tensões medidas, com o ponto de referência (terra usado).
- O que **não** foi identificado. Isso evita que a próxima sessão repita a
  suposição como se fosse fato.

## 6. Limites e riscos

Reconhecimento de placa é a etapa com maior chance de dano permanente e a
menor chance de erro detectável depois. Vale a regra: tudo que é feito com o
alvo **energizado** exige confirmação de tensão e terra antes; tudo que é feito
**desenergizado** exige confirmar que a energia realmente saiu (capacitor
carregado ainda fornece corrente).

Nada aqui autoriza abrir equipamento que não é seu. Trabalhe em placa própria,
em placa de descarte que você comprou, ou em equipamento cujo dono autorizou
por escrito o escopo — e, nesse último caso, documente o escopo antes de tocar.

## O que este documento não cobre

Não cobre engenharia reversa de esquemático a partir de netlist, nem
ferramentas de CAD para reconstruir placa. Não cobre leitura em circuito de
eMMC/UFS, que tem procedimento próprio e risco maior. E não substitui o
datasheet: em conflito entre este texto e o datasheet do componente, o
datasheet vence.