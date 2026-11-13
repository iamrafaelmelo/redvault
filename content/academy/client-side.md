---
slug: client-side
title: "Segurança Client-Side: o navegador como trust boundary"
category: client
difficulty: medium
summary: "Audite confiança no DOM, postMessage, storage e políticas do navegador partindo do princípio de que todo cliente pode ser modificado."
tags: [dom, postmessage, cors, storage, browser-security]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 130
---

# Segurança Client-Side: o navegador como trust boundary

O navegador não é uma trust boundary que você controla. Usuários podem modificar o JavaScript, editar o storage, reenviar requests e rodar as próprias extensões. Toda decisão tomada apenas no código client-side é uma sugestão. O trabalho de segurança client-side faz duas perguntas:

1. Que autoridade o navegador detém?
2. Como outra origem pode influenciar essa autoridade?

## Confiança no DOM e sinks

Revise todo lugar onde a aplicação escreve dados no DOM. Os sinks perigosos estão cobertos no artigo de XSS, mas a questão maior é confiança: um valor de `localStorage`, de um fragmento de URL, de um evento `postMessage` ou de uma resposta de API continua não confiável quando chega a `innerHTML`.

Prefira:

```js
element.textContent = value;             // texto, não markup
element.setAttribute("data-id", value);  // atributo que não é de evento
```

Evite:

```js
element.innerHTML = value;               // interpreta markup
location.href = value;                   // URLs javascript:
eval(value);                             // executa código
```

Sanitização é o último recurso. Use um sanitizador mantido, como o DOMPurify, com configuração explícita, e ainda faça o encoding no contexto de saída. [DOMPurify](https://github.com/cure53/DOMPurify)

## postMessage

`postMessage` viabiliza comunicação entre origens, mas só com segurança quando o receptor verifica:

- `event.origin` contra uma allowlist exata.
- `event.source` contra a janela esperada.
- O formato da mensagem e os tipos de dado.
- A ação solicitada.

Um receptor vulnerável:

```js
window.addEventListener("message", (event) => {
  document.getElementById("preview").innerHTML = event.data;
});
```

Uma página do atacante consegue embutir o alvo em um iframe e enviar uma mensagem forjada. Se o receptor checa `event.origin` apenas com `includes()` ou substring, uma origem parecida pode passar. Use comparações exatas.

A MDN documenta a API e suas ressalvas de segurança. [MDN — Window.postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)

## CORS não é autorização

CORS controla quais origens podem ler respostas a partir de um navegador. Ele não protege o endpoint de clientes que não são navegadores e não substitui autenticação ou autorização.

Configurações perigosas:

- `Access-Control-Allow-Origin: *` com credenciais (navegadores rejeitam a combinação, mas más configurações continuam por aí).
- Refletir o header `Origin` sem allowlist.
- `Access-Control-Allow-Origin: null` em endpoints sensíveis.
- Confiar em subdomínios que podem ser sequestrados.

Teste com um header `Origin` que não seja o da própria aplicação e inspecione a resposta. Uma política CORS permissiva em uma API privada pode permitir que um site malicioso leia dados com os cookies da vítima.

## Storage e posicionamento de tokens

`localStorage` e `sessionStorage` são legíveis por qualquer script rodando na origem, incluindo XSS injetado. Cookies com `HttpOnly` não são legíveis por JavaScript, mas continuam sendo enviados nas requests e estão sujeitos a CSRF a menos que protegidos.

Orientações:

- Cookies de sessão de alto valor: `HttpOnly`, `Secure`, `SameSite=Lax` ou `Strict`.
- Evite bearer tokens de longa duração em `localStorage`.
- Se os tokens forem obrigatoriamente client-side, mantenha-os de vida curta e com escopo estreito.
- Limpe o storage no logout e na mudança de privilégio.

## Clickjacking e framing

Framing permite que outro site sobreponha ou disfarce a aplicação. Defenda com:

```http
Content-Security-Policy: frame-ancestors 'none';
X-Frame-Options: DENY
```

Teste se ações sensíveis podem ser enquadradas e se a ação exige interação do usuário que possa ser enganada. `frame-ancestors` é o controle moderno.

## Open redirects e tratamento de URL

Um endpoint de redirect que aceita URL arbitrária pode viabilizar phishing, vazamento de token OAuth e bypass de filtro SSRF. Valide os destinos de redirect contra uma allowlist de paths relativos ou hosts confiáveis. Rejeite `//evil.example`, variantes com barra invertida e schemes codificados.

Para links, evite URLs `javascript:` e `data:`. Use `rel="noopener noreferrer"` em links externos abertos em nova aba.

## Scripts de terceiros

Todo script de terceiros roda com a autoridade da página. Inventarie:

- Analytics, widgets de chat, tag managers e testes A/B.
- CDNs sem Subresource Integrity.
- Bibliotecas depreciadas com vulnerabilidades conhecidas.
- Scripts carregados de paths controlados pelo usuário.

Use CSP com nonces/hashes, Subresource Integrity e uma allowlist estrita. Um comprometimento de supply chain em um host de script vira um comprometimento da sua origem.

## Checklist de teste

- [ ] Enumere sources e sinks do DOM
- [ ] Teste validação de origin/source/type em `postMessage`
- [ ] Inspecione CORS com valores de `Origin` estrangeiros
- [ ] Revise flags de cookie e armazenamento de tokens
- [ ] Teste defesas contra framing e clickjacking
- [ ] Teste redirects e URLs `javascript:`
- [ ] Inventarie scripts de terceiros e SRI
- [ ] Revise a CSP em busca de bypasses e diretivas ausentes

## Referências

- [OWASP HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [OWASP Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [MDN — Window.postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)
- [MDN — CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [CWE-346 — Origin Validation Error](https://cwe.mitre.org/data/definitions/346.html)
- [DOMPurify](https://github.com/cure53/DOMPurify)