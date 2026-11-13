---
slug: cache-deception
title: "Cache Deception e Poisoning"
category: advanced
difficulty: hard
summary: "Explore divergências entre cache keys, normalização de path e roteamento da origem para armazenar ou recuperar a resposta errada."
tags: [cache, deception, poisoning, cdn, http]
updated: 2026-11-12
version: "1.0"
source_type: research
order: 140
---

# Cache Deception e Poisoning

Caches compartilhados ficam entre usuários e origens. Eles melhoram a latência armazenando respostas e reutilizando-as para requests que compartilham uma **cache key**. Problemas de segurança aparecem quando o cache e a origem discordam sobre o que uma request significa.

Duas classes relacionadas:

- **Cache deception:** uma resposta privada e autenticada é armazenada sob uma URL que parece pública e depois é recuperada por um usuário não autenticado.
- **Cache poisoning:** entrada controlada pelo atacante influencia uma resposta que o cache serve a outros usuários.

## Cache keys e entradas não chaveadas

Uma cache key tipicamente inclui scheme, host, path e parâmetros de query selecionados. Ela pode ignorar:

- Headers como `X-Forwarded-Host`, `X-Original-URL`, `X-Rewrite-URL`.
- Cookies (ou incluir todos eles, dependendo da configuração).
- Parâmetros de query excluídos por regras.
- Conteúdo do corpo.
- Diferenças de encoding no path.

Uma **entrada não chaveada** muda a resposta mas não a cache key. Se o atacante consegue controlá-la, a resposta envenenada pode ser servida a todos que pedirem a mesma chave.

## Mecânica de cache deception

Um fluxo típico:

1. A vítima requisita `/account/profile.css` estando autenticada.
2. A origem ignora o sufixo `.css` e devolve a página privada de perfil.
3. O cache trata `.css` como asset estático e armazena a resposta.
4. O atacante requisita `/account/profile.css` sem autenticação e recebe os dados da vítima.

Variantes usam path parameters, slashes codificadas, ponto e vírgula, pontos à direita, extensões duplas e diferenças de normalização:

```text
/account/profile/nonexistent.css
/account/profile%2f..%2fprofile.css
/account/profile;.css
/account/profile.css?cachebust=1
```

O bypass exato depende do cache e da origem. Teste com um marcador único na resposta autenticada e recupere-o de um cliente novo, não autenticado.

## Mecânica de cache poisoning

Vetores comuns:

- `X-Forwarded-Host` refletido em URLs absolutas, links de reset de senha ou redirects.
- `X-Forwarded-Scheme` causando redirect ou comportamento de mixed content.
- Parâmetros de query não chaveados usados pela origem (`?utm_source=`) mas excluídos da cache key.
- Fat GET requests com corpo que o cache ignora.
- Injeção de header via request smuggling.
- Web cache deception de respostas de API que parecem estáticas.

Um teste clássico:

```http
GET /?cb=random HTTP/1.1
Host: target
X-Forwarded-Host: attacker.example
```

Se a resposta contém `attacker.example` e o cache a armazena para `/?cb=random`, outros usuários podem receber a página envenenada.

## Normalização de path

Caches e origens discordam sobre:

- Segmentos `..` e `.`.
- Slashes codificadas (`%2f`) e barras invertidas.
- Path parameters com ponto e vírgula (`;jsessionid=`).
- Pontos, espaços e bytes nulos à direita.
- Sensibilidade a caixa.
- Duplo encoding.

Um cache pode normalizar `/static/../account` para `/account`, enquanto a origem roteia de outra forma. Ou a origem pode tratar `/account.css` como `/account`, enquanto o cache trata como arquivo estático.

## Testando com segurança

Use um canário único por teste. Para deception:

1. Autentique com seu usuário de teste.
2. Requisite a página privada com um sufixo que parece estático e um marcador de query único.
3. Faça logout ou use um cliente novo.
4. Requisite a mesma URL.
5. Se receber o marcador privado, o cache armazenou.

Para poisoning:

1. Envie uma request com um header/valor não chaveado único.
2. Requisite a mesma cache key de um cliente novo.
3. Verifique se o valor único aparece.

Evite envenenar caches compartilhados de produção com conteúdo malicioso. Nesta plataforma, todos os alvos são labs locais descartáveis; reinicie depois do teste.

## Defesas

- Configure os caches para chavear em toda entrada que afeta a resposta, ou remova headers não confiáveis na borda.
- Não cacheie respostas com `Set-Cookie` ou `Authorization`, a menos que seja explicitamente projetado.
- Use `Cache-Control: private, no-store` para páginas autenticadas.
- Normalize paths de forma consistente na borda e na origem; rejeite encodings ambíguos.
- Sirva assets estáticos de uma origem/path separado com roteamento estrito.
- Desabilite cache para páginas de erro e redirects.
- Use `Vary` para headers que influenciam o conteúdo, mas não confie nele como correção completa.
- Monitore taxa de cache hit e content types inesperados.

A RFC 9111 define a semântica de cache HTTP, incluindo `private`, `no-store` e `Vary`. [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)

## Checklist de teste

- [ ] Identifique camadas de cache e cache keys
- [ ] Encontre headers/parâmetros não chaveados refletidos nas respostas
- [ ] Teste sufixos estáticos em páginas autenticadas
- [ ] Teste discrepâncias de normalização de path
- [ ] Verifique tratamento de `Cache-Control`, `Vary` e `Set-Cookie`
- [ ] Use canários únicos e clientes novos
- [ ] Verifique o comportamento do cache após logout e mudança de privilégio
- [ ] Reinicie o estado do lab depois dos experimentos

## Referências

- [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)
- [PortSwigger — Web cache deception](https://portswigger.net/web-security/web-cache-deception)
- [PortSwigger — Web cache poisoning](https://portswigger.net/web-security/web-cache-poisoning)
- [OWASP WSTG — Testing for Web Cache Poisoning](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/17-Testing_for_Web_Cache_Poisoning)
- [CWE-525 — Use of Web Browser Cache Containing Sensitive Information](https://cwe.mitre.org/data/definitions/525.html)