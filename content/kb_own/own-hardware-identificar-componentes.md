---
slug: own-hardware-identificar-componentes
title: "Identificar componentes e ler datasheets sem inventar pinagem"
category: hardware-recon
summary: "Como ir do código impresso no chip ao part number, do part number ao datasheet correto e do datasheet à pinagem real. Inclui as armadilhas mais comuns (top marking abreviado, encapsulamento diferente, tensão errada) e a lista do que pode ser verificado só com documentação."
tags: "hardware datasheet componentes top marking part number pinagem encapsulamento"
severity: info
references:
  - Wikipedia — Datasheet | https://en.wikipedia.org/wiki/Datasheet
  - Wikipedia — Serial Peripheral Interface | https://en.wikipedia.org/wiki/Serial_Peripheral_Interface
  - Wikipedia — I²C | https://en.wikipedia.org/wiki/I%C2%B2C
  - KiCad — Schematic capture | https://www.kicad.org/discover/schematic-capture/
  - sigrok — Protocol decoders | https://sigrok.org/wiki/Protocol_decoders
---

Todo erro de hardware caro começa com uma identificação errada de componente:
o chip foi identificado como 3,3 V e era 1,8 V; o encapsulamento lido no
datasheet era o SOIC e a placa tinha WSON; o pino 1 foi contado no lado
errado. Este documento trata só da identificação — do código impresso no
componente até a tabela de pinos em que você pode confiar.

## 1. O que está impresso não é o part number

Fabricantes de semicondutores usam *top marking* curto porque o chip é
pequeno. `25Q32` diz família e capacidade, não o part number completo. Um
mesmo top marking pode corresponder a duas variantes com tensão ou velocidade
diferentes.

Consequências práticas:

- **Nunca pesquise só o código impresso.** Ele aponta a família; o part number
  completo aparece em catálogo do fabricante, em documentação de reparo ou em
  anúncio do próprio componente.
- **Confira o encapsulamento no *package marking*.** Os datasheets da mesma
  família trazem uma tabela separada que mapeia o top marking para o
  encapsulamento e para a temperatura de operação.
- **Anote o lote.** Em placas com chips remarcados (comuns em equipamento
  paralelo), o lote diferente do esperado é sinal de componente trocado.

## 2. Do part number ao datasheet certo

A ordem de confiança das fontes, da maior para a menor:

1. **Datasheet oficial no site do fabricante.** É a única fonte que você pode
   citar como primária.
2. **Nota de aplicação do fabricante** (*application note*), quando o
   comportamento depende de configuração.
3. **Errata / *silicon revision*.** Existe e é ignorada com frequência; corrige
   comportamentos que o datasheet não menciona.
4. **Repositórios de documentação de reparo.** Úteis para achar o datasheet de
   peça que saiu de linha, mas precisam ser conferidos contra o PDF oficial.
5. **Fóruns e vídeos.** Úteis como pista, nunca como fonte.

Regra de ouro: se você não abriu o PDF e não viu a figura de pinagem com os
olhos, você não sabe a pinagem.

## 3. O que o datasheet responde — e o que não responde

Um datasheet típico responde:

- tensão de alimentação e tolerância;
- pinagem por encapsulamento;
- níveis lógicos de entrada e saída;
- comandos aceitos, com o código de operação;
- tempos mínimos (setup, hold, tempo de resposta);
- estados de boot e de reset.

O datasheet **não** responde:

- como o fabricante do equipamento ligou o componente na placa;
- se o pino de *write protect* está preso a terra ou a `VCC`;
- se o barramento tem um buffer no meio;
- se o firmware depende de um modo de boot específico.

Essas respostas vêm da placa, não do papel. É por isso que identificação e
medição são etapas separadas.

## 4. As quatro armadilhas mais caras

**Tensão.** Famílias de flash SPI existem em 3,3 V e 1,8 V com nomes
parecidos. Aplicar 3,3 V num chip de 1,8 V não "às vezes funciona": danifica.
Medir a tensão no capacitor de desacoplamento do próprio chip, com o
equipamento energizado e antes de qualquer conexão, é o único jeito de saber.

**Contagem de pinos.** O pino 1 é marcado por um ponto, por um chanfro ou por
uma faixa na serigrafia — e a posição relativa muda entre SOIC e QFN. Contar
pelo canto errado inverte `VCC` e `GND`, que é o pior par possível.

**Componentes com função dupla.** Um chip de 8 pinos pode ser EEPROM I²C
(`24xx`) ou flash SPI (`25xx`). Os prefixos são próximos e o visual é igual.
Ler o datasheet antes de ligar um adaptador evita o constrangimento de
descobrir que o protocolo era outro.

**Chips empilhados (PoP).** Dois die no mesmo encapsulamento não aparecem na
marcação. Um pedaço do sistema pode existir fisicamente e não estar acessível
por pino nenhum.

## 5. Verificação que não exige equipamento

O que dá para fechar só com documentação e foto:

- família e part number provável de cada chip identificado;
- tensão nominal esperada, por família;
- pinagem esperada, por encapsulamento;
- protocolo esperado e comando de leitura de identificação;
- lista de hipóteses que precisam de medida para virar fato.

O que **exige equipamento**: confirmar a tensão real, confirmar qual pino da
placa corresponde a qual sinal do datasheet, e confirmar que o barramento está
ativo. Um analisador lógico é o instrumento natural para esta última parte —
o documento de fluxo de analisador lógico desta base cobre o processo.

## 6. Montar a sua ficha de componente

Para cada chip identificado, mantenha uma ficha curta e reutilizável:

```
Designador:  U7
Top marking: 25Q64JVSIQ  (lido com lupa, linha 2 = lote 2331)
Part number: W25Q64JVSSIQ
Família:     flash SPI NOR, 64 Mbit, 3,3 V
Encapsulamento: SOIC-8  (confirmado: pinos laterais visíveis)
Pinagem:     1=/CS 2=DO 3=/WP 4=GND 5=DI 6=CLK 7=/HOLD 8=VCC
Fonte:       datasheet oficial <link>, revisão <data>
Confirmado:  tensão medida 3,31 V em repouso
Não confirmado: se /WP e /HOLD estão presos a VCC na placa
```

Essa ficha é o que permite que outra pessoa (ou você, seis meses depois) repita
o trabalho sem refazer a pesquisa. Ela também evita o erro mais comum em
relatório técnico: apresentar suposição como medição.

## 7. Limites

Este documento não cobre identificação por raio-X nem por microscópio
eletrônico; não cobre leitura de chip com resina sobremoldada; e não cobre
validação elétrica de projeto. Também não autoriza abrir equipamento de
terceiro. Se a placa não é sua, a etapa de identificação termina na foto: sem
autorização escrita do dono, sem contato físico.