---
slug: methodology
title: "Um loop repetível de avaliação web"
category: methods
difficulty: beginner
summary: "Um loop prático para escopo, mapeamento, teste, prova de impacto e escrita de achados sem transformar o engajamento em uma lista de payloads."
tags: [methodology, scoping, evidence, reporting]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 1
---

# Um loop repetível de avaliação web

Um bom teste não é uma corrida até o primeiro payload. É um loop controlado: entenda o alvo, formule uma hipótese, teste a menor sonda útil, preserve a evidência e então aprofunde o achado ou siga em frente. O loop abaixo é deliberadamente tedioso. Isso é uma qualidade.

## 1. Defina a fronteira antes de enviar tráfego

Anote as origens, portas, contas, janelas de teste e ações proibidas exatas. Para um lab local, o escopo é uma porta em loopback. Para um engajamento real, é um contrato, não uma sugestão.

Uma nota de escopo útil responde:

- Quais hostnames, IPs e portas estão no escopo?
- Quais contas e papéis podem ser usados?
- Negação de serviço, engenharia social, phishing ou acesso físico estão excluídos?
- Onde os dados de teste podem ser armazenados e como são destruídos?
- Quem é notificado quando aparece um achado crítico?

O NIST SP 800-115 descreve o processo de avaliação em fases de planejamento, descoberta, ataque e pós-teste. A fase de planejamento é o que torna o resto defensável. [NIST SP 800-115](https://csrc.nist.gov/pubs/sp/800/115/final)

## 2. Mapeie a aplicação como usuário e depois como sistema

Use a aplicação normalmente. Registre toda rota, parâmetro, cookie, header, upload, redirect e transição de estado que observar. Depois repita com um proxy e faça perguntas de sistema:

- O que é gerado server-side e o que é refletido da request?
- Quais identificadores são opacos e quais são sequenciais?
- Onde o app confia em um header (`Host`, `X-Forwarded-*`, `Origin`)?
- Quais respostas são cacheáveis? Quais contêm dados privados?
- O que acontece em erros, parâmetros ausentes e tipos inesperados?

O capítulo de informação do OWASP Web Security Testing Guide é uma base sólida para esse mapeamento. [OWASP WSTG — Information Gathering](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/)

## 3. Transforme observações em hipóteses testáveis

Uma hipótese tem três partes: **entrada**, **mecanismo** e **impacto esperado**.

> Se o parâmetro `next` chega a um header `Location` sem validação, então um atacante pode redirecionar a vítima depois do login, o que pode facilitar phishing ou vazamento de token.

Hipóteses fracas soam como "testar XSS". Hipóteses fortes nomeiam o source, o sink, o contexto e a evidência que provaria a execução. Isso importa porque a maioria dos payloads falha por razões de contexto, não porque a classe de vulnerabilidade esteja ausente.

## 4. Use a sonda mínima que distingue resultados

Prefira uma sonda que produza um de dois estados claramente diferentes:

- `'` versus `''` para erros de contexto SQL ou mudanças de resultado.
- Um marcador inofensivo como `rvt0ken` para reflexão e encoding.
- Uma URL canário em um host que você controla para SSRF e injeção cega.
- Duas contas, A e B, com IDs de objeto para checagens de autorização.

Evite payloads destrutivos quando existe prova somente leitura. Para SQL injection, um diferencial booleano ou baseado em tempo costuma bastar para provar a falha; extrair uma tabela de produção não é necessário para escrever o achado.

## 5. Preserve a evidência enquanto avança

Capture request, response, timestamp, conta, alvo e uma explicação curta de por que o resultado importa. Redija cookies e segredos das capturas de tela. Guarde o HTTP bruto em texto para que um revisor possa reproduzir.

Um achado precisa de:

1. Um título que nomeie a fraqueza e a função afetada.
2. Pré-condições (papel, feature flag, configuração).
3. Passos de reprodução com as requests exatas.
4. Evidência de impacto, não só uma resposta suspeita.
5. Causa raiz no código ou no design.
6. Uma correção que remova a causa, mais controles compensatórios.

A calculadora CVSS é útil para severidade consistente, mas uma nota não substitui uma narrativa clara. [Especificação CVSS v4.0](https://www.first.org/cvss/v4.0/specification-document)

## 6. Pare e reavalie em cada trust boundary

Quando uma request passa do navegador para a API, da API para o worker, do worker para o banco ou de serviço para serviço, pergunte qual autoridade muda. A maioria das cadeias de alto impacto é feita de pequenos erros de fronteira: um header interno em que um proxy confia, uma fila de jobs que aceita URLs arbitrárias, uma ferramenta de suporte que reseta qualquer conta.

O MITRE ATT&CK é organizado em torno do comportamento do adversário, não de nomes de payload; use-o para checar se sua cadeia tem um objetivo realista. [MITRE ATT&CK](https://attack.mitre.org/)

## 7. Feche o loop com um reteste

Uma correção não é provada por um pull request mesclado. Rode a request original de novo e depois tente as variantes adjacentes que a correção pode ter esquecido:

- Codificações e content types diferentes.
- Rotas alternativas ou versões legadas de API.
- Uma conta com menos privilégios.
- Acesso direto ao serviço de backend, contornando o proxy corrigido.

Documente o resultado do reteste e a data. Se a correção for parcial, diga isso claramente.

## Checklist compacto de engajamento

- [ ] Escopo e regras de engajamento registrados
- [ ] Contas e papéis enumerados
- [ ] Rotas, parâmetros e fluxos de dados mapeados
- [ ] Autenticação e ciclo de vida da sessão testados
- [ ] Autorização de objeto e de função testada com duas identidades
- [ ] Contextos de injeção testados com sondas diferenciais mínimas
- [ ] Entradas de arquivo, URL e template tratadas como hostis
- [ ] Sources e sinks client-side revisados
- [ ] Comportamento de cache e proxy inspecionado
- [ ] Achados reproduzidos a partir de um estado limpo
- [ ] Evidências redigidas e armazenadas com segurança
- [ ] Correção retestada, incluindo variantes de bypass

## Referências

- [NIST SP 800-115 — Technical Guide to Information Security Testing and Assessment](https://csrc.nist.gov/pubs/sp/800/115/final)
- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/latest/)
- [OWASP Top 10:2025](https://owasp.org/Top10/)
- [MITRE ATT&CK](https://attack.mitre.org/)
- [CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document)