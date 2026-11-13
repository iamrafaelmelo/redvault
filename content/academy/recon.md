---
slug: recon
title: "Recon e mapeamento de superfície de ataque"
category: recon
difficulty: beginner
summary: "Encontre as rotas, arquivos, metadados e relações de confiança que a aplicação esqueceu de esconder e transforme-os em alvos concretos de teste."
tags: [recon, robots.txt, javascript, content-discovery, information-disclosure]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 20
---

# Recon e mapeamento de superfície de ataque

Recon não é um campeonato de força bruta de diretórios. O trabalho dele é reduzir incerteza: o que existe, quem consegue alcançar, e quais partes nunca deveriam ser públicas. Em um lab local, o alvo inteiro é uma porta em loopback, então a disciplina é ler o que a aplicação já expõe.

## Leia o mapa da própria aplicação

Comece pelos recursos que descrevem o site para máquinas:

- `/robots.txt` — regras para crawlers, muitas vezes uma lista de paths interessantes.
- `/sitemap.xml` — URLs canônicas e timestamps de última modificação.
- `/.well-known/` — security.txt, change-password, OIDC e outros metadados.
- `/favicon.ico`, `/manifest.json`, `/service-worker.js` — pistas de framework e assets.
- Comentários HTML, source maps e configuração inline.

A RFC 9309 é explícita: `robots.txt` não é um mecanismo de controle de acesso; é um pedido público aos crawlers. Trate cada entrada `Disallow` como um path candidato, não como uma fronteira. [RFC 9309 — Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309)

## Inspecione o bundle client-side

Front ends modernos entregam tabelas de rotas, endpoints de API, feature flags e às vezes credenciais. Busque o JavaScript diretamente em vez de confiar só na página renderizada.

```bash
curl -s http://127.0.0.1:PORT/static/app.js | grep -Ei 'api|token|key|internal|debug'
```

Procure por:

- Paths de API absolutos e relativos, incluindo versões legadas.
- Headers que o cliente deve enviar (`X-API-Key`, tenant IDs).
- Feature gates que escondem a UI de admin mas não a rota no servidor.
- Source maps (`.map`) que reconstroem o código original.
- Segredos hard-coded. Um valor entregue ao navegador é público, independentemente do nome que tiver.

A revisão de conteúdo de página do OWASP WSTG é um bom checklist para este passo. [OWASP WSTG — Review Web Page Content for Information Leakage](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01_Information_Gathering/05-Review_Web_Page_Content_for_Information_Leakage)

## Enumere conteúdo com uma hipótese

A descoberta de conteúdo funciona melhor quando guiada por convenções de nomes que você observou. Se o app usa `/api/v1/invoices`, teste `/api/v1/`, `/api/v2/`, extensões de backup e variantes de caixa. Se as páginas usam `?file=`, procure o diretório que as alimenta.

Artefatos de alto valor comuns:

| Artefato | Por que importa |
| --- | --- |
| `.git/`, `.svn/` | Histórico do código e segredos removidos |
| `*.bak`, `*.old`, `*.zip`, `*.sql` | Dados e configuração exportados |
| `.env`, `config.php.bak` | Credenciais e feature flags |
| `/debug`, `/actuator`, `/metrics` | Estado em tempo de execução e internals |
| `/.DS_Store`, `Thumbs.db` | Nomes de arquivos e estrutura de diretórios |

Use uma wordlist que combine com a tecnologia. Uma lista genérica gera ruído; uma lista ciente do framework encontra os arquivos que de fato existem. O SecLists é uma coleção mantida. [SecLists](https://github.com/danielmiessler/SecLists)

## Faça fingerprint antes de explorar

Identifique servidor, framework e versão pelos headers, cookies e formato dos erros. Depois responda:

- Existe reverse proxy ou CDN? Quais headers ele adiciona ou em quais confia?
- O app é server-rendered, uma SPA, ou os dois?
- Existem múltiplas versões de API com regras de autorização diferentes?
- Quais endpoints devolvem JSON, HTML, redirects ou arquivos?

Uma versão sozinha não é uma vulnerabilidade. Use-a para escolher hipóteses e depois verifique o comportamento. O índice de CVE desta academia remete a registros oficiais de vulnerabilidades reais.

## Mapeie identidades e arestas de confiança

Recon inclui contas, não só URLs. Com duas contas de teste, observe:

- Quais identificadores são atribuídos e se são sequenciais.
- Quais cookies carregam autoridade e quais são apenas preferências.
- Se mudanças de papel são refletidas server-side ou só na UI.
- Quais headers internos o front end envia (`X-Forwarded-Host`, `X-Original-URL`).
- O que acontece quando uma request chega diretamente a um serviço interno.

É aqui que SSRF, ataques de host header e bugs de autorização ficam visíveis. O material de information disclosure do PortSwigger cobre as fontes de vazamento comuns. [PortSwigger — Information disclosure](https://portswigger.net/web-security/information-disclosure)

## Evite descoberta barulhenta e fora do escopo

Em um engajamento real, scans agressivos podem disparar rate limits, bloqueios de WAF ou indisponibilidade. Nesta plataforma, apenas a porta loopback atribuída está no escopo. Mantenha a taxa de requests baixa, use `GET` quando possível e nunca aponte um scanner para outros serviços locais.

Um throttle prático:

```bash
# Uma request por vez, lista pequena, sem recursão
while read -r path; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:PORT/$path")
  [ "$code" != "404" ] && printf '%s %s\n' "$code" "$path"
done < candidates.txt
```

## Documente a superfície

Mantenha um inventário simples:

| URL | Método | Auth | Entradas | Comportamento interessante |
| --- | --- | --- | --- | --- |
| `/api/users/{id}` | GET | user | id numérico | devolve registros de outros usuários |
| `/backups/` | GET | nenhuma | — | listagem de diretório |
| `/static/app.js` | GET | nenhuma | — | chave interna |

O inventário vira o seu plano de teste. Todo achado posterior deve remeter a uma entrada dele.

## Referências

- [RFC 9309 — Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309)
- [OWASP WSTG — Information Gathering](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01_Information_Gathering/)
- [PortSwigger — Information disclosure](https://portswigger.net/web-security/information-disclosure)
- [MDN — HTTP headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)
- [SecLists](https://github.com/danielmiessler/SecLists)