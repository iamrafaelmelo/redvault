---
slug: own-forense-cadeia-custodia
title: "Cadeia de custódia e linha do tempo: a parte do laudo que se contesta em juízo"
category: forensics-timeline
summary: "Explica por que a evidência forense vale o que vale a sua cadeia de custódia: aquisição antes da análise, hash de integridade, registro de quem tocou o quê e quando, e a distinção entre linha do tempo obtida de metadados (com risco de manipulação) e linha do tempo de eventos. Usa os termos técnicos do NIST e a separação entre artefato, cópia de trabalho e relatório."
tags: "forense cadeia de custodia hash linha do tempo evidencia integridade acquisição"
severity: info
references:
  - HackTricks — Aquisição de Imagem e Montagem | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — Partições/Sistemas de arquivos/Carving | https://github.com/HackTricks-wiki/hacktricks
  - plaso — parser de linhas do tempo | https://github.com/log2timeline/plaso
  - Timesketch — análise colaborativa de linhas do tempo | https://github.com/google/timesketch
  - Sleuth Kit — ferramentas de aquisição e análise | https://github.com/sleuthkit/sleuthkit
---

A análise forense tem duas perguntas diferentes, e confundi-las é o erro mais
comum de um laudo amador:

1. **O que aconteceu?** — pergunta técnica, respondida pela análise.
2. **Como sabemos que o que analisamos era aquilo?** — pergunta de custódia,
   respondida pelo processo.

Um laudo com a primeira resolvida e a segunda ignorada é tecnicamente atraente
e processualmente inútil.

## Custódia em quatro atos

### 1. Aquisição antes de qualquer análise

Coletar imagem — do disco, da partição, do dump de memória — antes de rodar
qualquer ferramenta no sistema original. Cada comando executado no host vivo
altera o estado: acesso a arquivo muda `atime`, log é rotacionado, cache é
rescrito.

O documento de aquisição de imagem do HackTricks traz o procedimento com
`dd`/`dcfldd` e montagem somente leitura. O ponto essencial é a montagem em
modo somente leitura (`-o ro`), sem a qual a análise modifica a própria prova.

### 2. Hash de integridade

Calcule o hash da imagem **durante** a aquisição, não depois. Guarde o valor em
local separado. Todo relatório começa citando:

```
SHA-256 da imagem: <valor>
Calculado em: <data/hora>
Comando: dcfldd if=/dev/sdX of=evidencia.img hash=sha256
```

Se o hash da cópia de trabalho não bate com o da aquisição, a cadeia está
quebrada e qualquer conclusão posterior é inadmissível.

### 3. Registro de posse

O mínimo exigível: quem coletou, quando, onde, de qual dispositivo, com qual
ferramenta e qual hash resultou. Cada vez que a evidência é copiada ou aberta
por outra ferramenta, registra-se a nova ação. O registro é um documento, não
um comentário em memória.

### 4. Cópia de trabalho separada

Nunca analise a imagem original. Trabalhe numa cópia, e guarde a original
lacrada. O laudo cita os dois hashes.

## Linha do tempo: dois tipos que não se misturam

A ferramenta de timeline mais usada, `plaso`, extrai eventos de fontes
heterogêneas e os normaliza — e essa normalização é justamente o motivo de
precisar de cautela.

**Linha do tempo de metadados** — construída a partir de `MACB`
(modification, access, change, birth). É fácil de gerar e fácil de manipular:
qualquer ferramenta, inclusive `touch`, altera `mtime`. Um atacante com
privilégio altera todos os timestamps de um arquivo.

**Linha do tempo de eventos** — construída a partir de registros gerados pelo
próprio sistema: log de eventos, journal, log de acesso de servidor, telemetria
de EDR. É mais difícil de forjar porque exige comprometer também o coletor, e
sua ausência pode ser detectada (lacunas de log).

A regra: **uma conclusão sustentada apenas por `mtime` é uma hipótese, não um
fato**. Para afirmar "arquivo X foi criado depois do login em Y" é preciso um
evento — entrada de log, criação de processo, escrita em journal — não um
timestamp de metadado isolado.

## Montagem do laudo

Uma estrutura que funciona:

1. **Escopo** — quais sistemas, qual janela de tempo, qual hipótese.
2. **Evidência** — origem, hash, método de aquisição.
3. **Linha do tempo** — tabela com coluna de **fonte** por evento. Um evento de
   log e um evento de metadado não têm o mesmo peso; a coluna torna isso
   visível.
4. **Achados** — o que a linha do tempo sustenta e o que não sustenta.
5. **Limitações** — lacunas de log, tempo não sincronizado, artefato ausente.

A seção 5 é o que diferencia um laudo útil de uma ficção plausível. Um analista
sênior lê primeiro a seção de limitações.

## Erros recorrentes

- Confundir "não encontrei" com "não ocorreu". Ausência de evidência num
  sistema sem telemetria não é evidência de ausência.
- Apresentar o hash da cópia de trabalho como se fosse o da original.
- Rodar ferramenta no host comprometido e depois coletar a imagem — a análise
  alterou o objeto.
- Montar imagem em modo leitura/escrita "só para conferir".
- Citar horário sem declarar o fuso e se o relógio do host estava sincronizado
  (NTP). Um host com 4 minutos de desvio desloca toda a correlação.