---
slug: chaining
title: "Encadeamento de vulnerabilidades: do achado ao objetivo"
category: chain
difficulty: hard
summary: "Combine fraquezas de baixa severidade em um caminho de ataque realista, documente cada elo e evite exagerar o impacto."
tags: [chaining, privilege-escalation, attack-path, evidence]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 160
---

# Encadeamento de vulnerabilidades: do achado ao objetivo

Vazamentos reais raramente vêm de um único bug perfeito. Eles vêm de uma sequência: um vazamento dá um identificador, uma falha de autorização expõe um token, um fluxo de recuperação fraco transforma o token em uma conta, e um console com privilégio excessivo entrega o objetivo.

Uma cadeia não é uma lista de achados não relacionados. Cada elo precisa consumir a saída do anterior e aumentar a autoridade do atacante.

## Modele a cadeia como um grafo

Nós são fatos ou capacidades:

```text
bundle JS público
  -> endpoint de API interno
  -> chave de serviço
  -> diretório de usuários
  -> token de reset de admin
  -> sessão de admin
  -> exportação contendo a flag do vault
```

Arestas são ações que transformam uma capacidade em outra. Desenhe o grafo antes de explorar. Ele expõe elos ausentes e evita spray cego de payloads.

## Tipos de elo comuns

- **Information disclosure → mira:** source maps, stack traces, arquivos de backup, listagens de diretório.
- **IDOR → material de credencial:** um objeto que você consegue ler contém um token, API key ou link de recuperação.
- **Recuperação fraca → account takeover:** token não vinculado a usuário/propósito, envenenamento de host header, token previsível.
- **Mass assignment → escalada de privilégio:** definir `role`, `verified`, `owner` ou `plan`.
- **SSRF → serviço interno:** alcançar um admin em loopback ou endpoint de metadata.
- **LFI → código/config → segredo:** ler um arquivo de config que desbloqueia outro serviço.
- **XSS → bypass de CSRF / ação de admin:** executar em um contexto de navegador privilegiado.
- **Race condition → manipulação de saldo:** saque ou resgate de cupom repetido.
- **Cache deception → roubo de dados:** resposta privada armazenada sob uma URL que parece pública.

## Construa de forma incremental, verifique cada elo

Não pule para o payload final. Em cada passo:

1. Registre a request e a resposta exatas.
2. Confirme que a capacidade é real (não uma string refletida).
3. Guarde a saída em um formato reutilizável (token, cookie, ID).
4. Anote pressupostos e pré-condições.
5. Avance apenas quando o próximo elo estiver provado.

Exemplo: um IDOR devolve um token de reset de admin. Antes de usá-lo, verifique se o token é aceito para a conta de admin e não para uma isca. Depois resete a senha, faça login e acesse o console. Se o reset exigir um segredo adicional, a cadeia está incompleta.

## Escopo e ética

Uma cadeia pode causar mudanças de estado reais. Em um lab, reinicie o ambiente depois. Em produção, use contas de teste, evite ações destrutivas e pare antes de exfiltrar mais dados do que o necessário para provar impacto.

Não encadeie para sistemas de terceiros, outros tenants ou infraestrutura fora do escopo acordado. Uma vulnerabilidade que só funciona atacando um serviço fora do escopo não é um achado válido.

## Severidade e narrativa

Encadear muda a severidade. Um IDOR médio mais uma falha de reset média podem virar um account takeover crítico. Métricas ambientais de CVSS podem refletir isso, mas o relatório precisa explicar a sequência.

Escreva o achado como:

- **Pré-condições:** conta de suporte, e-mail conhecido, feature habilitada.
- **Cadeia:** passos numerados com requests e saídas.
- **Impacto:** o que o atacante controla ou lê no fim.
- **Causas raiz:** cada controle quebrado, não só o sintoma final.
- **Correção:** corrija cada elo; remover um elo quebra a cadeia, mas todos devem ser corrigidos.
- **Detecção:** logs que revelariam a sequência.

## Lições defensivas

- A autorização precisa ser imposta em cada objeto e função.
- Tokens de recuperação precisam ser vinculados a um usuário, propósito e TTL curto.
- Serviços internos não devem confiar apenas na rede.
- Campos sensíveis não devem aparecer em respostas "por conveniência".
- Ações privilegiadas deveriam exigir reautenticação ou step-up.
- Monitore sequências incomuns: enumeração de diretórios, uso de token, mudanças de papel.

As páginas de técnicas do MITRE ATT&CK são úteis para mapear cada elo ao comportamento do adversário. [MITRE ATT&CK](https://attack.mitre.org/)

## Checklist de teste

- [ ] Mapeie capacidades e transições
- [ ] Prove cada elo com uma request reproduzível
- [ ] Preserve tokens/IDs com segurança e redija-os nas anotações
- [ ] Teste caminhos alternativos se um elo falhar
- [ ] Verifique o escopo em cada passo
- [ ] Reinicie o estado do lab depois da cadeia
- [ ] Reporte cada causa raiz e o impacto combinado
- [ ] Reteste depois das correções, incluindo correções parciais

## Referências

- [MITRE ATT&CK](https://attack.mitre.org/)
- [OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/latest/)
- [OWASP Top 10:2025](https://owasp.org/Top10/)
- [CWE-639 — Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)
- [NIST SP 800-115](https://csrc.nist.gov/pubs/sp/800/115/final)