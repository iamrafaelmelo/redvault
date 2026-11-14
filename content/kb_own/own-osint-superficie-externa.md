---
slug: own-osint-superficie-externa
title: "Superfície externa: certificate transparency, Shodan e o que cada um realmente mostra"
category: osint-infra
summary: "Explica o que a transparência de certificação registra e por que ela revela nomes que a busca não revela, o que um buscador de serviços expostos indexa e suas limitações de cobertura, e como cruzar as duas fontes com DNS e WHOIS sem concluir mais do que os dados sustentam. Destaca a diferença entre um nome listado e um serviço ativo."
tags: "osint shodan crt certificate transparency dns whois reconhecimento superficie"
severity: info
references:
  - Certificate Transparency — crt.sh | https://crt.sh/
  - Shodan — buscador de serviços expostos | https://www.shodan.io/
  - HackTricks — Metodologia de Reconhecimento Externo | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — 43 - Pentesting WHOIS | https://github.com/HackTricks-wiki/hacktricks
  - bbot — motor de reconhecimento externo | https://github.com/blacklanternsecurity/bbot
---

Reconhecimento externo é a etapa em que se descobre **o que existe**, antes de
tocar em qualquer coisa. Três fontes cobrem a maior parte e cada uma responde
pergunta diferente.

## Transparência de certificação (Certificate Transparency)

Autoridades certificadoras registram os certificados que emitem em logs
públicos e apenas acrescentáveis. O registro existe para detectar emissão
indevida — e, como efeito colateral, é um inventário de **nomes de host para os
quais alguém pediu certificado**.

O que ele revela: nomes de host, datas de emissão, a autoridade emissora.

O que ele **não** revela: se o serviço está ativo hoje, o que roda nele, ou se
o nome pertence à organização atual.

É a fonte mais subutilizada e a de maior retorno na etapa seguinte: um
subdomínio de ambiente de teste que nunca apareceu em busca costuma aparecer no
log, porque pedir certificado é obrigatório para HTTPS.

Em `crt.sh`, a consulta é por domínio e a saída é uma lista de registros.
Deduplicar nomes é parte do trabalho — o mesmo host aparece várias vezes.

## Buscador de serviços (Shodan)

Buscadores desse tipo mantêm índice de serviços encontrados por varredura
própria: porta, banner, produto, versão, certificado, e metadados de rede.

O que ele revela: se um endereço respondeu, em que porta, com que banner, em
que data.

O que ele **não** revela: cobertura completa. O índice reflete quando o
serviço foi visto pela última vez, não o estado atual. Um serviço que aparece
pode ter sido removido; um que não aparece pode estar ativo e não ter sido
varrido naquele intervalo.

Consequência para o laudo: um resultado de buscador de serviços é
**indicativo**, não prova de exposição. A prova é conexão direta ao alvo
autorizado, na data do teste.

## DNS e WHOIS

- **DNS** responde "para onde o nome aponta agora": endereço, servidor de nome,
  e-mail de registro. Registros de nome podem estar delegados a provedor de
  cloud, o que dissocia o nome do endereço.
- **WHOIS** responde "quem registrou": titular, datas, servidor de nome. A
  resposta costuma vir com dados de privacidade mascarados, que não
  necessariamente indicam ocultação — é o padrão de serviços de registro.

Cruzar as três fontes é o que dá valor: um nome no log de certificado, que
resolve para um endereço, que aparece no buscador com banner, sustenta a
afirmação "existe serviço exposto, com este produto, nesta data".
Isoladamente, nenhuma das três sustenta nada.

## Erros recorrentes

- **Tratar subdomínio como serviço.** Muito ambiente de teste aponta para
  nome sem host por trás. Confirme resolução e conexão antes de listar.
- **Tratar um resultado de buscador como estado atual.** Cite a data de
  observação.
- **Usar varredura de buscador como varredura feita pelo analista.** O laudo
  descreve o que o analista confirmou.
- **Confundir ASN ou provedor com dono.** O endereço pode ser de provedor de
  nuvem compartilhado.
- **Escanear o que se encontrou sem autorização.** Encontrar não é autorizar.
  Escopo do exercício é o que define o que pode ser tocado.

## Checklist

1. Liste nomes por log de certificado, filtrando wildcard e deduplicando.
2. Resolva cada nome e registre o que responderia a DNS.
3. Consulte o buscador para os endereços do escopo; anote data e banner.
4. Para cada nome ainda desconhecido, tente resolver por busca e DNS.
5. Registre cada linha com fonte, data e o que a confirma.

O produto final é uma tabela de superfície com data. É o que permite comparação
futura — e é isso que torna o reconhecimento útil além daquele dia.