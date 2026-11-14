---
slug: own-yara-regras-deteccao
title: "YARA: escrever regras de detecção que não geram falso positivo"
category: malware-detection
summary: "Regras YARA são padrões de bytes e strings combinados por lógica booleana, aplicados a arquivos e processos. Este artigo cobre a gramática real (seções meta, strings, condition), os modificadores que evitam custo desnecessário, as armadilhas de falso positivo — strings curtas, ausência de âncora estrutural, uso de texto genérico — e a diferença entre assinatura estática e indicador comportamental. Explica como validar uma regra contra um conjunto benigno antes de confiar nela."
tags: "malware yara deteccao assinatura regra indicador falso positivo ioc"
severity: info
references:
  - YARA — Writing YARA rules | https://yara.readthedocs.io/en/stable/writingrules.html
  - YARA — Time module (functions that detect static timestamps) | https://yara.readthedocs.io/en/stable/modules/time.html
  - VirusTotal — YARA repository and CLI | https://github.com/VirusTotal/yara
  - MITRE ATT&CK — Software/Technique knowledge base for naming behaviour | https://attack.mitre.org/
  - SigmaHQ — Sigma rules for log-based detection | https://github.com/SigmaHQ/sigma
---

YARA descreve **o que um arquivo é** por meio de padrões. Uma regra não prova
malícia: ela afirma "este arquivo contém esta combinação de evidências". A
diferença entre uma regra útil e uma regra que destrói a operação é a taxa de
falso positivo, e ela é decidida pelo desenho da regra, não pelo motor.

## Anatomia de uma regra

Toda regra tem três seções:

```
rule exemplo_indicador
{
    meta:
        author = "analista"
        description = "Descrição do que a regra detecta"
        reference = "https://attack.mitre.org/techniques/T1055/"

    strings:
        $a = "trecho_distintivo"
        $b = { 4D 5A }
        $c = /regex\/[0-9]{4}/

    condition:
        $a and $b
}
```

A seção `meta` é metadado livre — ela não participa da avaliação. É o lugar
para registrar autor, data, referência à técnica do MITRE ATT&CK e a razão de
cada string existir. Uma regra sem `meta` em seis meses é indocumentável.

A seção `strings` declara os padrões. Três tipos são aceitos: texto ASCII/UTF-16
(`"..."`), hexadecimal com máscaras (`{ 4D 5A ?? 00 }`) e expressão regular.

A seção `condition` combina as strings por lógica booleana: `and`, `or`, `not`,
comparações de contagem (`#a > 2`), offsets (`$a at 0`) e funções de módulo.

## Como escolher uma string

A decisão de projeto mais importante é a string. Segundo a documentação do
próprio YARA, strings curtas aumentam a chance de falso positivo, e o motor
pode até recusar padrões considerados excessivamente genéricos.

Boas strings em análise de malware têm três características:

1. **Distintividade estrutural** — não um nome de função comum (`CreateProcess`)
   mas a combinação que só aquele binário produz.
2. **Contexto** — duas strings presentes na mesma região do arquivo
   (`$a at 0x200 and $b at 0x204`).
3. **Comprimento** — prefira trechos longos o suficiente para não aparecer por
   acaso; quando o padrão é curto por natureza, exija uma segunda condição.

## Modificadores que economizam trabalho

- `nocase` — comparação insensível a caixa. Útil para texto de usuário; inútil
  para bytes de código, que são sensíveis por natureza.
- `wide` — interpreta a string como UTF-16 (dois bytes por caractere). É a
  forma normal de strings em binários Windows compilados com Unicode.
- `ascii` — força a busca ASCII quando `wide` também foi declarado; declarar
  ambos amplia a detecção ao custo de mais trabalho.
- `fullword` — exige que o padrão esteja cercado por caracteres que não sejam
  alfanuméricos. Evita que `cmd` case dentro de `command`.
- `xor` / `xor(N)` — busca a string transformada por XOR. Amplia a detecção para
  strings levemente ofuscadas, ao custo de aumento proporcional de trabalho.
- `base64` / `base64wide` — busca a string em Base64, útil para IOCs que
  aparecem codificados em scripts. A própria documentação alerta que estas
  podem produzir falsos positivos porque o alfabeto Base64 é pequeno.
- `private` — a string participa da condição mas não é reportada. Serve para
  âncoras estruturais que não interessam ao analista.
- `filesize` na condição — limita a regra por tamanho, evitando avaliar um
  binário de 1 GB com um padrão que só aparece em executáveis pequenos.

## A armadilha do timestamp e de outras constantes

Compiladores gravam a data de compilação no binário. Uma regra que compara um
timestamp fixo detecta exatamente aqueles artefatos conhecidos e nada mais.
Esse é um uso legítimo, e o YARA tem até um módulo dedicado a funções de tempo
para tornar a intenção explícita.

O uso ilegítimo é o contrário: concluir que "tem timestamp de 2019, logo é
malicioso". Isso descreve um empacotador ou uma build antiga, não um
comportamento.

## Regra não é indicador comportamental

YARA examina bytes. Quando o malware é de memória, escrito em PowerShell, ou
carregado por injeção, os bytes que importam não estão no disco de forma
legível. Para esse caso a detecção é por log e comportamento, e a linguagem
adequada é outra — por exemplo Sigma, que é genérica para sistemas de logs.

Regra prática: **YARA para artefato, Sigma para evento, telemetria de EDR para
sequência**. Misturar os três gera cobertura imaginária.

## Validar antes de confiar

Uma regra só é "pronta" depois de testada contra três conjuntos:

1. **Positivos conhecidos** — amostras da família descrita.
2. **Negativos legítimos** — arquivos do mesmo tipo (todos os `.exe` de uma
   instalação limpa, todos os documentos do Office da mesma versão).
3. **Negativos adversariais** — módulos do próprio sistema operacional, que são
   o primeiro lugar onde um padrão genérico dispara.

O procedimento é o mesmo de qualquer assinatura: rode a regra com `yara -r`
sobre o diretório do conjunto negativo e conte os disparos. Um único falso
positivo em `C:\Windows\System32` invalida a regra para produção, porque ela
passa a exigir triagem manual de cada host limpo.

## O que dizer num laudo

Uma assinatura detectada sustenta a afirmação "este arquivo contém a sequência
X". Não sustenta "este arquivo é o malware Y". Para chegar à segunda afirmação
é preciso correlacionar com comportamento observado, hash publicado ou análise
manual do código — e citar a fonte de cada um.