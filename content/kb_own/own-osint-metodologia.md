---
slug: own-osint-metodologia
title: "OSINT: da pergunta ao registro, sem transformar dado público em assédio"
category: osint
summary: "Define OSINT pelo processo (pergunta, fonte, registro, verificação) e não pelo volume de ferramentas. Separa coleta de verificação, explica por que atribuição apressada é o erro dominante, e estabelece os limites: escopo autorizado, dado pessoal, e a regra de que página pública não torna a coleta legítima. Referencia fontes primárias de verificação e registro."
tags: "osint reconhecimento fonte verificacao registro escopo dados pessoais"
severity: info
references:
  - HackTricks — Metodologia de Reconhecimento Externo | https://github.com/HackTricks-wiki/hacktricks
  - OSINT Framework | https://osintframework.com/
  - MITRE ATT&CK — Reconnaissance (TA0043) | https://attack.mitre.org/
  - bbot — motor de reconhecimento externo | https://github.com/blacklanternsecurity/bbot
  - theHarvester — coleta de e-mails e nomes | https://github.com/laramies/theHarvester
---

OSINT é produção de conhecimento a partir de fonte aberta. A definição que
importa é a última palavra: **conhecimento**. Reunir cem resultados de busca e
chamá-los de informação é coleta; conhecimento é o que sobrevive a verificação e
pode ser citado.

## O processo em quatro etapas

### 1. A pergunta

Toda investigação começa com uma pergunta formulável em uma frase e
respondível com dado público. Exemplos:

- "Quais serviços desta organização expõem interface de administração?"
- "Este domínio pertence à mesma organização que aquele, hoje?"
- "Existe conta corporativa que vaza credencial em repositório público?"

Pergunta vaga ("fazer um dossiê da empresa") produz relatório vago e, pior,
coleta sem limite. A pergunta é também o que define o escopo: o que está fora
dela não se coleta.

### 2. A fonte

Cada resposta precisa de fonte identificável. Não é "vi no Google": é o
registro específico, com URL, data de consulta e o trecho citado. Sites mudam,
posts são excluídos, páginas saem do ar. Sem o trecho, a fonte evaporou.

Fontes se dividem em:

| Tipo | Exemplo | Confiabilidade |
| --- | --- | --- |
| Registro oficial | base de registro de domínio, dados de empresa | alta, mas pode estar desatualizada |
| Publicação da própria organização | site, comunicado, repositório | alta para intenção, não para configuração |
| Agregador | mecanismo de busca, diretório | média, sempre confirmar na origem |
| Conteúdo de terceiro | post, fórum, vazamento | baixa, tratar como hipótese |

### 3. O registro

O registro é o produto. Uma planilha ou tabela com as colunas abaixo é o mínimo:

```
pergunta | afirmação | fonte (URL) | data de consulta | evidência (trecho) | confiança
```

Preencher a coluna "confiança" obriga a distinguir fato de inferência. Nessa
mesma linha, "o domínio resolve para um provedor de nuvem" é fato; "a empresa
está migrando para nuvem" é inferência, e precisa de mais de uma evidência.

### 4. A verificação

Toda afirmação publicável passa por três testes:

1. **Pode ser falsificada?** Se não há nenhum dado que a contradiga, ela não é
   uma afirmação testável.
2. **Tem segunda fonte independente?** Não a mesma fonte republicada. Duas
   páginas que copiam a mesma nota de imprensa são uma fonte.
3. **A conclusão é proporcional à fonte?** Uma listagem de subdomínio não
   prova que o serviço existe, e muito menos que está vulnerável.

## O erro dominante: atribuição apressada

Endereço IP, ASN, certificado ou registro de quem apontam para determinado
provedor não identificam **pessoa**. Apontam para uma infraestrutura, que pode
ser compartilhada, revendida, ou alugada por um tempo.

A regra operacional: **atribuição é a última conclusão, nunca a primeira
hipótese**. E deve aparecer no relatório com o nível de confiança explícito.

## Limites que não se negociam

Não é porque os dados são públicos que a coleta é legítima ou apropriada.

- **Escopo** — o exercício tem alvo declarado. Coletar além dele é coletar sem
  autorização, mesmo de fonte pública.
- **Assédio por agregação** — juntar telefone, endereço, rotina e vínculos de
  uma pessoa produz dano real, ainda que cada dado esteja público. Não pertence
  a um exercício técnico.
- **Dados sensíveis de terceiros** — em relatório, citar o mínimo necessário.
  Quando o dado é irrelevante para a conclusão, ele não entra.
- **Credencial encontrada** — se a coleta encontra senha ou token real, o
  procedimento é notificar e documentar, não usar. Usar transforma o exercício
  em acesso não autorizado, com consequência jurídica própria.

## Fluxo técnico mínimo

1. **Domínio e DNS** — registro, servidores de nome, histórico de resolução.
2. **Certificados** — transparência de certificação lista nomes já emitidos,
   que frequentemente revelam subdomínios que não aparecem em busca.
3. **Repositórios públicos** — busca por nome da organização e por credenciais
   em arquivo de configuração.
4. **Superfície exposta** — serviços visíveis na internet, classificados por
   tipo.
5. **Consolidação** — a tabela de registro, com confiança por linha.

A automação acelera as etapas 1 a 4 — `bbot` e `theHarvester` fazem isso — e
não substitui a etapa 5. Ferramenta produz lista; analista produz laudo.

## O que um laudo de OSINT deve conter

- a pergunta e o escopo;
- cada afirmação com fonte, data e trecho;
- a distinção explícita entre fato e inferência;
- o que não foi possível confirmar;
- a data de corte: a internet muda, e o relatório é válido naquela data.