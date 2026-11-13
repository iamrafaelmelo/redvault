---
slug: file-upload
title: "File Upload: do arquivo armazenado ao risco armazenado"
category: upload
difficulty: medium
summary: "Teste extensão, content-type, content sniffing, local de armazenamento e caminhos de renderização sem confundir um arquivo armazenado com execução de código."
tags: [upload, svg, content-type, webshell, magic-bytes]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 150
---

# File Upload: do arquivo armazenado ao risco armazenado

Um endpoint de upload aceita bytes de uma fonte não confiável e lhes dá um nome, um tipo e um lugar para morar. O risco depende do que acontece depois: o arquivo é servido inline, interpretado, executado, incluído, compartilhado ou considerado confiável por outro sistema?

Comece mapeando o ciclo de vida completo:

```text
upload -> validação -> armazenamento -> entrega/download -> renderização/parsing -> compartilhamento/exportação
```

Cada etapa pode falhar de forma diferente.

## Camadas de validação

Um pipeline de upload robusto checa mais que o nome do arquivo:

| Camada | O que verificar | Erro comum |
| --- | --- | --- |
| Nome do arquivo | basename, tamanho, caracteres permitidos | confiar no path do cliente |
| Extensão | allowlist, insensível a caixa | blocklist só de `.php` |
| Content-Type | allowlist, mas nunca sozinho | aceitar `image/svg+xml` às cegas |
| Magic bytes | assinatura real do arquivo | confiar no `Content-Type` |
| Conteúdo | interpretar/decodificar com segurança | passar bytes a um interpretador |
| Armazenamento | fora do web root, nome aleatório | nome original em diretório público |
| Entrega | `Content-Disposition`, `X-Content-Type-Options` | execução inline de HTML/SVG |
| Autorização | quem pode ler o arquivo | URLs previsíveis |

Nenhuma camada isolada é suficiente. Um arquivo chamado `avatar.png` pode conter HTML ou SVG; um PNG válido pode carregar um payload poliglota; um parser de imagem pode ter vulnerabilidades próprias.

## SVG é conteúdo ativo

SVG é XML e pode conter scripts e referências externas. Se um SVG enviado é servido inline a partir da origem da aplicação, ele pode executar JavaScript nessa origem.

```xml
<svg xmlns="http://www.w3.org/2000/svg">
  <script>fetch('/collect?c=' + document.cookie)</script>
</svg>
```

Mitigações:

- Sirva uploads de usuário a partir de uma origem separada, sem cookies de sessão.
- Force `Content-Disposition: attachment` e um `Content-Type` seguro.
- Sanitize SVG server-side se a renderização inline for necessária.
- Aplique CSP e `X-Content-Type-Options: nosniff`.

## Confusão de extensão e parser

Teste:

- Extensões duplas: `shell.php.jpg`, `shell.jpg.php`.
- Variantes de caixa: `.PhP`, `.pHp5`.
- Pontos/espaços à direita (Windows): `shell.php.`, `shell.php `.
- Bytes nulos em stacks legadas.
- Extensões executáveis alternativas configuradas no servidor (`.phtml`, `.jsp`, `.aspx`).
- Content-type incompatível com os magic bytes.
- Formatos compactados que extraem para paths executáveis.

A configuração do servidor decide quais extensões executam. Um arquivo inofensivo em uma stack pode ser código em outra.

## Path traversal em nomes de arquivo

Se o servidor usa o nome enviado pelo cliente diretamente:

```text
../../../../var/www/html/shell.php
..\..\..\windows\system32\file
```

Use `basename`, gere um nome aleatório server-side e armazene fora do web root. Preserve o nome original apenas como metadado, escapado na exibição.

## Entrega e content sniffing

Navegadores podem farejar o conteúdo quando o `Content-Type` está ausente ou ambíguo. Defina:

```http
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="download.bin"
X-Content-Type-Options: nosniff
```

Para imagens, sirva de uma origem estática dedicada e valide a imagem decodificada. Para PDFs, considere o parser de PDF e o suporte a JavaScript; PDFs podem conter conteúdo ativo.

## Malware e abuso

Uploads podem ser usados para hospedar malware, conteúdo de phishing, esgotar armazenamento e fazer SSRF via fetchers server-side. Adicione:

- Limites de tamanho e cotas.
- Antivírus/scan de malware quando apropriado.
- Re-encoding de imagens para remover metadados e conteúdo ativo.
- Rate limits por conta.
- Revisão de conteúdo para uploads públicos.

## Verificação

Um marcador armazenado não é execução. Para provar impacto:

- Para XSS: carregue o arquivo enviado em um navegador e observe execução de script/callback.
- Para execução de código: apenas se o lab foi feito para isso, e dentro do diretório de estado do lab.
- Para path traversal: leia um arquivo conhecido após o upload, não um arquivo arbitrário do sistema.
- Para SSRF: use um listener de callback e um alvo em loopback.

Nesta plataforma, o lab de avatar SVG coleta o cookie da vítima depois que o bot renderiza o arquivo. É prova em navegador real, não um palpite de MIME type.

## Checklist de teste

- [ ] Mapeie o pipeline de upload até a renderização
- [ ] Teste nome, extensão, content-type e magic bytes
- [ ] Tente conteúdo ativo SVG/HTML
- [ ] Verifique local de armazenamento e previsibilidade da URL pública
- [ ] Teste `Content-Disposition`, `nosniff` e origem separada
- [ ] Teste limites de tamanho, cotas e rate limits
- [ ] Revise parsers de imagem/PDF e extração de arquivos
- [ ] Prove o impacto em navegador ao alegar XSS

## Referências

- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [PortSwigger — File upload vulnerabilities](https://portswigger.net/web-security/file-upload)
- [MDN — Content-Disposition](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition)
- [MDN — X-Content-Type-Options](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Content-Type-Options)
- [CWE-434 — Unrestricted Upload of File with Dangerous Type](https://cwe.mitre.org/data/definitions/434.html)