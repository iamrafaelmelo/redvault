---
slug: command-injection
title: "OS Command Injection: quando o dado vira shell"
category: server
difficulty: medium
summary: "Reconheça metacaracteres de shell, confirme a execução com um marcador inofensivo e migre de comandos concatenados para execução por array de argumentos."
tags: [command-injection, shell, rce, subprocess, sanitization]
updated: 2026-11-12
version: "1.0"
source_type: standard
order: 90
---

# OS Command Injection: quando o dado vira shell

Command injection ocorre quando entrada não confiável é interpretada por um shell. A operação perigosa costuma ser um `system()`, `popen()`, `subprocess` com `shell=True`, backticks ou equivalente. A vulnerabilidade não é a presença de um utilitário de rede; é a fronteira com o shell.

## Encontre os construtores de comando

Funcionalidades comuns:

- Diagnósticos de ping, consulta DNS e traceroute.
- Conversão de imagem e geração de PDF.
- Utilitários de backup, exportação e arquivamento.
- Operações Git e importadores de repositório.
- Handlers de "abrir com" e pré-visualização de arquivo.
- Definições de jobs de CI/CD.

Procure por concatenação de strings:

```python
os.system("ping -c 1 " + host)
```

ou chamadas de subprocess habilitadas para shell:

```python
subprocess.run(f"nslookup {host}", shell=True)
```

O shell interpreta `;`, `&`, `|`, quebras de linha, backticks, `$()` e redirecionamentos antes de o programa pretendido rodar.

## Confirmação sem dano

Use um comando marcador seguro e observável:

```text
127.0.0.1; id
127.0.0.1 && uname -a
127.0.0.1 | whoami
```

Se a saída não retornoar, use um callback:

```text
127.0.0.1; curl http://127.0.0.1:PORT/collect?c=marker
```

ou uma diferença de tempo:

```text
127.0.0.1; sleep 3
```

A confirmação deve distinguir "a aplicação ecoou minha entrada" de "um shell a executou". Em um lab, leia o arquivo de flag designado apenas após confirmar a execução.

## Contexto e quoting

O payload exato depende de como a entrada é citada:

| Construção | Exemplo | Escape |
| --- | --- | --- |
| Argumento sem quotes | `ping {host}` | `; id` |
| Com aspas simples | `ping '{host}'` | `'; id; '` |
| Com aspas duplas | `ping "{host}"` | `"; id; "` |
| Array passado ao shell | `["sh", "-c", cmd]` | qualquer metacaractere de shell |
| Sem shell | `["ping", host]` | metacaracteres são inertes |

Quando não há shell envolvido, `; id` vira parte do hostname e o comando falha de forma segura. Essa distinção é central para a correção.

## Injeção cega e com saída codificada

Se o stdout não é exibido, teste:

- Callback DNS/HTTP com token único.
- Atrasos de tempo contra uma baseline.
- Mensagens de erro que incluam a saída do comando.
- Escritas em um diretório acessível pela web (apenas dentro do diretório de estado do lab).
- Diferenças de exit code.

Evite escrever fora do estado atribuído do lab. Não use comandos destrutivos, reverse shells para hosts externos ou persistência.

## Command injection versus argument injection

Mesmo sem shell, a entrada do usuário pode alterar o comportamento do programa se for passada como opção:

```python
subprocess.run(["curl", user_url])
```

Uma URL começando com `-` pode ser interpretada como opção. Use `--` para encerrar as opções e valide schemes/hosts. Isso é argument injection, não shell injection, mas o impacto pode ser parecido.

Da mesma forma, ferramentas que interpretam nomes de arquivo como opções (`tar`, `ffmpeg`, `git`) precisam de separadores `--` explícitos e argumentos em allowlist.

## Correção

1. Evite execução via shell. Passe um array de argumentos com `shell=False` e um executável fixo.
2. Valide a entrada contra uma allowlist estrita (por exemplo, um endereço IP interpretado por uma biblioteca).
3. Use bibliotecas dedicadas em vez de chamar `ping`, `curl` ou `convert` pelo shell.
4. Reduza privilégios, use sandbox e restrinja acesso a filesystem/rede.
5. Defina timeouts e limites de saída.
6. Registre o comando e os argumentos exatos, sem segredos.

```python
# Mais seguro: sem shell, programa fixo, argumento validado
ip = ipaddress.ip_address(host)
subprocess.run(["ping", "-c", "1", str(ip)], shell=False, timeout=5)
```

Nenhum escaping é tão confiável quanto remover o shell. Blocklists de caracteres são rotineiramente contornadas por encoding, separadores alternativos e recursos do shell.

## Checklist de teste

- [ ] Identifique toda funcionalidade de diagnóstico/exportação/conversão
- [ ] Determine se há um shell envolvido
- [ ] Teste `;`, `&&`, `|`, quebra de linha, `$()` e backticks
- [ ] Tente contextos com e sem quotes
- [ ] Confirme execução cega com callback ou timing
- [ ] Teste argument injection com `-` no início
- [ ] Verifique privilégios, acesso a filesystem e egress de rede
- [ ] Confirme que a correção usa arrays de argumentos e allowlists

## Referências

- [OWASP Command Injection Defense Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html)
- [PortSwigger — OS command injection](https://portswigger.net/web-security/os-command-injection)
- [CWE-78 — Improper Neutralization of Special Elements used in an OS Command](https://cwe.mitre.org/data/definitions/78.html)
- [Python — subprocess security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations)
- [MITRE ATT&CK — Command and Scripting Interpreter](https://attack.mitre.org/techniques/T1059/)