---
slug: file-inclusion
title: "File inclusion e path traversal"
category: server
difficulty: medium
summary: "Escape de um diretório base, entenda a diferença entre ler e incluir um arquivo, e reconheça quando um endpoint de download vira execução de código."
tags: [lfi, rfi, path-traversal, wrappers, templates]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 80
---

# File inclusion e path traversal

Path traversal e file inclusion são relacionados mas distintos:

- **Path traversal** escapa de um diretório para ler, escrever ou apagar um arquivo.
- **Local File Inclusion (LFI)** faz a aplicação incluir/executar um arquivo local como código ou template.
- **Remote File Inclusion (RFI)** inclui um arquivo remoto, geralmente levando a execução de código.

O mesmo parâmetro pode ser traversal em um caminho de código e include em outro. Identifique o sink antes de escolher um payload.

## Lendo arquivos

Um endpoint de download tipicamente vulnerável:

```python
path = os.path.join("documents", request.args["file"])
return open(path).read()
```

`../` escapa de `documents/`. Teste:

```text
?file=../etc/passwd
?file=..%2f..%2fetc%2fpasswd
?file=....//....//etc/passwd
?file=/etc/passwd
```

Codificações podem ser decodificadas uma vez, duas vezes ou nenhuma. No Windows, teste barras invertidas, letras de drive e alternate data streams. No Unix, bytes nulos geralmente são rejeitados por runtimes modernos, mas stacks legadas podem diferir.

O objetivo normalmente é um arquivo de configuração, chave SSH, segredo da aplicação, banco ou flag. Leia apenas o necessário para a prova.

## Inclusão versus leitura

LFI vira execução de código quando o arquivo incluído é interpretado:

```php
include($_GET["page"] . ".php");
```

Se você consegue escrever um arquivo em algum lugar que o servidor inclui, ou incluir um arquivo de log/upload/sessão contendo PHP, você executa. Log poisoning funciona quando a aplicação grava dados de request controlados pelo atacante em um arquivo que depois é incluído.

Stacks modernas de Python/Node/Ruby podem usar engines de template com semântica de include própria. Rastreie o dado até o renderer real; uma leitura de arquivo pode não executar, e um include de template pode não ser um path de filesystem.

## Wrappers e filtros

Stream wrappers do PHP são um amplificador clássico de LFI:

- `php://filter/convert.base64-encode/resource=index.php` — lê o código-fonte.
- `data://text/plain;base64,...` — injeta conteúdo (exige `allow_url_include`).
- `zip://`, `phar://` — inclusão baseada em arquivo compactado.

Isso é específico de PHP. Não cole wrappers em um alvo que não é PHP e chame de achado. O manual do PHP documenta os wrappers e seus requisitos de configuração. [PHP — Supported Protocols and Wrappers](https://www.php.net/manual/en/wrappers.php)

## Traversal em uploads e arquivos compactados

Traversal também aparece ao extrair arquivos:

- Nomes de entrada de ZIP como `../../etc/cron.d/job`.
- Symlinks dentro de um tar apontando para fora da raiz de extração.
- Nomes de arquivo com separadores codificados.
- Chaves de object storage que normalizam de forma diferente do filesystem local.

A classe "Zip Slip" está documentada pela Snyk. [Snyk — Zip Slip](https://security.snyk.io/research/zip-slip-vulnerability)

## Defesas

1. **Não construa paths de filesystem a partir de entrada de usuário.** Use IDs opacos mapeados server-side para paths fixos.
2. Se um nome de arquivo for inevitável, normalize com `realpath`, resolva symlinks e verifique se o resultado está dentro da raiz permitida com uma checagem ciente de separador de path.
3. Use allowlist de extensões e content types para uploads e downloads.
4. Sirva arquivos de usuário a partir de object storage ou de uma origem separada, não do include path da aplicação.
5. Desabilite wrappers perigosos e `allow_url_include` quando aplicável.
6. Rode com menor privilégio; um usuário web não deveria ler `/etc/shadow` nem segredos da aplicação.
7. Registre e alerte sobre padrões de traversal, mas não dependa de assinaturas de WAF.

Uma checagem falha comum:

```python
if ".." in filename: reject()
```

Ela perde URL encoding, paths absolutos, symlinks e separadores específicos de plataforma. Canonicalize primeiro e depois compare com a raiz resolvida.

## Checklist de teste

- [ ] Identifique sinks de leitura, inclusão, download e extração
- [ ] Teste paths absolutos, traversal relativo e variantes de encoding
- [ ] Determine se os arquivos incluídos são executados
- [ ] Revise paths de upload, log e sessão em busca de conteúdo gravável
- [ ] Teste nomes de entrada de arquivos e symlinks
- [ ] Verifique wrappers apenas no runtime relevante
- [ ] Confirme menor privilégio e permissões de arquivo
- [ ] Confirme a correção com casos de normalização e symlink

## Referências

- [OWASP WSTG — Testing Directory Traversal and File Include](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/01-Testing_Directory_Traversal_File_Include)
- [PortSwigger — File path traversal](https://portswigger.net/web-security/file-path-traversal)
- [CWE-22 — Improper Limitation of a Pathname to a Restricted Directory](https://cwe.mitre.org/data/definitions/22.html)
- [CWE-98 — Improper Control of Filename for Include/Require Statement](https://cwe.mitre.org/data/definitions/98.html)
- [PHP — Supported Protocols and Wrappers](https://www.php.net/manual/en/wrappers.php)