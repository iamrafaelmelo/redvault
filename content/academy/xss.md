---
slug: xss
title: "Cross-Site Scripting: sources, sinks e contexto"
category: xss
difficulty: medium
summary: "Siga o dado controlado pelo atacante de um source até um sink de execução, escolha o contexto certo e valide com um navegador real, não com uma string refletida."
tags: [xss, dom, csp, browser, encoding]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 60
---

# Cross-Site Scripting: sources, sinks e contexto

XSS é uma confusão entre dado e código no contexto do navegador. O payload importa menos que o caminho: qual **source** fornece o dado, qual **sink** o consome e qual encoding ou parsing acontece entre eles.

## As três classes de entrega

**XSS refletido** aparece na resposta imediata. O servidor ecoa um valor da request em HTML, atributo, bloco de script ou URL sem o encoding correto.

**XSS armazenado** persiste o payload em um banco, arquivo ou log e o serve a outro usuário depois. O impacto costuma ser maior porque pode alcançar administradores e não exige link forjado.

**DOM XSS** ocorre inteiramente no navegador. O servidor pode devolver uma página inofensiva, mas o código client-side lê um source e o escreve em um sink perigoso.

O OWASP XSS Prevention Cheat Sheet organiza as defesas por contexto de saída. [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

## Sources e sinks

Sources comuns:

- `location.search`, `location.hash`, `location.pathname`
- `document.referrer`
- `window.name`
- Eventos `postMessage`
- `localStorage`, `sessionStorage`, `IndexedDB`
- Respostas de Fetch/XHR
- Valores renderizados pelo servidor no HTML

Sinks perigosos:

| Sink | Risco |
| --- | --- |
| `innerHTML`, `outerHTML` | Interpreta markup e executa event handlers |
| `document.write` | Interpreta markup no contexto atual |
| `eval`, `Function` | Executa strings como código |
| `setTimeout(string)` | Executa strings como código |
| `element.setAttribute("onclick", ...)` | Execução de event handler |
| `href="javascript:..."` | Navegação executa script |
| jQuery `html()`, `append()` | Parsing de markup |
| Bypasses de framework (`bypassSecurityTrustHtml`) | Desabilita sanitização explicitamente |

Alternativas seguras incluem `textContent`, `createElement`, `setAttribute` com atributos que não são de evento e templates cientes de contexto.

## O contexto determina o payload

Um payload válido em texto HTML não é válido dentro de um atributo entre aspas, de uma string JavaScript, de um bloco CSS ou de uma URL.

```html
<!-- Texto HTML -->
<img src=x onerror=alert(1)>

<!-- Valor de atributo -->
" autofocus onfocus=alert(1) x="

<!-- String JavaScript -->
'; alert(1); //

<!-- URL -->
javascript:alert(1)
```

Navegadores e frameworks modernos adicionam camadas (CSP, Trusted Types, sanitizadores), mas o encoding ainda precisa estar correto no ponto de saída. Duplo encoding e "sanitizar na entrada" criam bypasses quando o mesmo dado é usado em múltiplos contextos.

## Prove execução, não reflexão

Ver seu payload na resposta prova reflexão, não execução. Use um navegador ou um bot headless e observe:

- Um callback para um listener que você controla.
- Uma mudança no DOM que só script consegue criar.
- Leitura de cookie ou uma request `fetch` carregando um marcador.
- O erro no console do navegador ou o report de violação de CSP.

Para um lab local, um endpoint simples de exfiltração basta:

```html
<script>
fetch('/collect?c=' + encodeURIComponent(document.cookie))
</script>
```

Se a página usa uma CSP estrita, script inline é bloqueado. Procure um sink que permita uma origem autorizada, ou registre a mitigação como efetiva em vez de alegar execução.

## Rastreamento de DOM XSS

Abra o DevTools e busque sinks no código. Depois rastreie para trás:

1. Coloque um breakpoint no sink.
2. Recarregue com um marcador único em cada source (`?q=marker`, `#marker`).
3. Inspecione a call stack e o valor no sink.
4. Confirme se o valor é interpretado como markup, script ou URL.

Um fluxo de source para sink pode ser assíncrono (`postMessage`, `fetch().then`), então reproduza com a mesma ordem da aplicação.

## postMessage e confiança entre origens

`postMessage` só é seguro quando o receptor verifica `event.origin` e valida o formato da mensagem. Teste:

```js
window.addEventListener("message", (event) => {
  // falta checagem de origin
  document.getElementById("out").innerHTML = event.data;
});
```

Uma origem maliciosa consegue enviar uma mensagem forjada se obtiver uma referência de janela (iframe, popup, opener). A MDN documenta as propriedades origin e source. [MDN — Window.postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)

## Cookies, HttpOnly e impacto

`HttpOnly` impede que JavaScript leia um cookie, o que reduz o roubo de sessão mas não impede:

- Ações feitas como a vítima via `fetch`.
- Leitura do conteúdo da página e exfiltração.
- Bypass de proteções CSRF que dependem de um token no DOM.
- Ataques a gerenciadores de senha ou injeção de formulários de login falsos.

Trate XSS como comprometimento total da autoridade client-side da origem, não apenas "roubo de cookie".

## CSP e defesas

Uma Content Security Policy pode bloquear script inline e de terceiros, mas só se for estrita e implantada corretamente. Diretivas úteis:

```http
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-random';
  object-src 'none';
  base-uri 'self';
  frame-ancestors 'none'
```

Evite `unsafe-inline` e `unsafe-eval` amplos. Use nonces ou hashes e implante Trusted Types onde houver suporte. CSP é defesa em profundidade; encoding de saída e sinks seguros continuam obrigatórios.

## Checklist de teste

- [ ] Todo ponto de reflexão testado no contexto real
- [ ] Payloads armazenados disparados em views de admin e secundárias
- [ ] Sources de DOM rastreados até os sinks com breakpoints
- [ ] Validação de origin e schema de `postMessage` revisada
- [ ] CSP interpretada e testada em busca de bypasses
- [ ] Interação entre `HttpOnly`, `SameSite` e CSRF avaliada
- [ ] Execução provada em navegador real, não só reflexão

## Referências

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [PortSwigger — Cross-site scripting](https://portswigger.net/web-security/cross-site-scripting)
- [MDN — Window.postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)
- [MDN — Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [CWE-79 — Improper Neutralization of Input During Web Page Generation](https://cwe.mitre.org/data/definitions/79.html)
- [W3C — Trusted Types](https://www.w3.org/TR/trusted-types/)