---
slug: ssrf
title: "Server-Side Request Forgery: posição confiável na rede"
category: server
difficulty: medium
summary: "Faça o servidor buscar um destino que você escolhe, contorne blocklists ingênuas e projete fetchers que não alcançam metadata interna."
tags: [ssrf, loopback, metadata, blocklist, allowlist]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 70
---

# Server-Side Request Forgery: posição confiável na rede

SSRF ocorre quando um atacante controla uma URL que o servidor busca. O servidor pode ter acesso de rede que o atacante não tem: serviços em loopback, faixas privadas, endpoints de metadata de cloud, APIs internas ou um console de administração ligado a `127.0.0.1`.

O impacto não é "o servidor consegue navegar na web". É que o servidor age com sua própria identidade e posição de rede.

## Encontre os fetchers

Procure por funcionalidades que buscam um recurso remoto:

- Pré-visualização de imagens, avatares ou PDFs.
- Importadores de URL, leitores RSS, webhooks e link unfurlers.
- Conversores de arquivo e serviços de screenshot.
- Health checks e botões de "testar conexão".
- Descoberta OAuth/OIDC e busca de JWKS.
- Parsers XML que resolvem entidades externas.
- Gerenciadores de pacotes, runners de CI e server-side rendering.

Nomes de parâmetro são pistas, não prova: `url`, `uri`, `target`, `src`, `image`, `feed`, `callback`, `webhook`, `next`, `host`, `port`.

## Confirme a request server-side

Use um listener em um host que você controla (ou uma rota de callback local no lab). Uma request vinda do servidor, e não do navegador, prova SSRF. Verifique:

- IP de origem e User-Agent.
- Resolução DNS: o servidor resolveu um hostname que você forneceu?
- Comportamento de redirect: ele segue um `302` para outro host?
- Suporte a scheme: `http`, `https`, `file`, `gopher`, `dict`.

Um fetch feito pelo navegador para um IP privado é bloqueado pelas regras modernas de private network access; um fetch server-side não tem essa proteção a menos que o código a implemente.

## Contorne filtros ingênuos

Blocklists que checam `localhost` ou `127.0.0.1` são incompletas. Teste representações com cuidado, só contra o seu lab:

| Representação | Exemplo |
| --- | --- |
| Loopback IPv4 | `127.0.0.1` |
| IPv4 como inteiro | `2130706433` |
| IPv4 hexadecimal | `0x7f000001` |
| IPv4 octal | `0177.0.0.1` |
| Loopback IPv6 | `[::1]` |
| IPv6 mapeado de IPv4 | `[::ffff:127.0.0.1]` |
| Nome DNS que resolve para loopback | hostname controlado |
| Redirect | host permitido redireciona para host interno |
| Confusão de parser de URL | `http://allowed@127.0.0.1/` |

O filtro pode rodar sobre a string bruta enquanto o cliente HTTP a interpreta de outra forma. Essa discrepância é a vulnerabilidade. O OWASP SSRF Prevention Cheat Sheet pede resolver e validar o destino, não comparar uma string. [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

## Metadata interna e serviços em loopback

Serviços de metadata de cloud e endpoints de admin costumam confiar em requests da própria máquina. Um fetcher que alcança `http://169.254.169.254/` ou `http://127.0.0.1:<port>/internal` pode expor credenciais ou funções privilegiadas.

Em um lab, o objetivo normalmente é uma rota que só é alcançável a partir de loopback. Reproduza o fetch, capture a resposta e envie a flag. Não escaneie portas não relacionadas nem hosts externos.

## DNS rebinding e TOCTOU

Até um passo de validação pode ser contornado se o hostname for resolvido duas vezes:

1. O DNS controlado pelo atacante retorna um IP público na validação.
2. O registro muda para `127.0.0.1` antes da request de verdade.
3. O cliente conecta ao endereço interno.

As defesas precisam fixar o IP resolvido, validar o endereço do peer real e rechecar depois dos redirects. Desabilitar redirects ou validar cada hop é essencial.

## SSRF cego

Quando a resposta não retorna, use evidências out-of-band:

- Um callback para um listener com token único.
- Diferenças de tempo entre portas alcançáveis e inalcançáveis.
- Mensagens de erro que revelam o resultado da conexão.
- Consultas DNS que codificam dados.

SSRF cego ainda pode ter alto impacto se alcançar um endpoint interno que muda estado (webhook, ação de admin) ou vazar dados por timing.

## Projetando um fetcher seguro

1. **Allowlist** de schemes (`https` apenas, se possível) e hosts.
2. Resolva o DNS e rejeite faixas loopback, link-local, privadas, multicast e reservadas usando uma biblioteca de IP atualizada.
3. Fixe o endereço resolvido e conecte a ele, preservando o header Host.
4. Não siga redirects automaticamente; valide cada hop.
5. Restrinja as portas a 80/443 a menos que seja explicitamente necessário.
6. Adicione autenticação e autorização aos serviços de metadata internos.
7. Rode o fetcher em uma rede segmentada sem rota para serviços sensíveis.
8. Limite tamanho de resposta, tempo e content type.
9. Registre o destino e o resultado para detecção.

Uma blocklist de strings não é um controle. Uma política de rede é.

## Checklist de teste

- [ ] Identifique todo fetch de URL feito pelo servidor
- [ ] Prove que a request parte do servidor
- [ ] Teste representações IPv4/IPv6 e redirects
- [ ] Verifique suporte a schemes e discrepâncias de parser
- [ ] Confirme se as respostas são refletidas ou cegas
- [ ] Teste metadata interna, admin em loopback e endpoints de cloud
- [ ] Revise DNS rebinding e tratamento de redirect
- [ ] Verifique segmentação de rede e política de egress

## Referências

- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [PortSwigger — Server-side request forgery](https://portswigger.net/web-security/ssrf)
- [CWE-918 — Server-Side Request Forgery](https://cwe.mitre.org/data/definitions/918.html)
- [RFC 6890 — Special-Purpose IP Address Registries](https://www.rfc-editor.org/rfc/rfc6890)
- [MITRE ATT&CK — Exploit Public-Facing Application](https://attack.mitre.org/techniques/T1190/)