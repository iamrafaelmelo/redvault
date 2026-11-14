#!/usr/bin/env python3
"""Generate content/learning_paths/01-web-application-pentesting.json.

Written as a script so the structure is checked as it is built (every slug is
read from the live platform) and the JSON stays pretty-printed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import act, mod, unit  # noqa: E402








# ---------------------------------------------------------------------------
# Módulo 0 — fundamentos
# ---------------------------------------------------------------------------
m0 = mod(
    "fundamentos",
    "Fundamentos de aplicações web e HTTP",
    "Ler uma aplicação web como um sistema de camadas: o que o cliente envia, o que o servidor decide e onde a confiança muda de mão.",
    ["HTTP request/response", "DNS e resolução de nomes", "cookies e sessões", "arquitetura cliente/servidor", "API vs página"],
    [
        unit(
            "http-e-sessoes",
            "HTTP, cookies e sessões",
            "Explicar o ciclo de uma request e localizar onde estado de sessão é guardado.",
            ["ler a request crua", "distinguir header/cookie/body", "identificar o transporte de sessão"],
            [
                act("m0-u1-kb-metodologia", "theory", "Método de avaliação web: o loop repetível",
                    academy="methodology", minutes=25),
                act("m0-u1-kb-recon", "theory", "Recon e mapeamento da superfície",
                    academy="recon", minutes=25),
                act("m0-u1-lab-recon-backup", "lab", "Primeiro contato: backup exposto",
                    lab="recon-backup-vault", minutes=20),
                act("m0-u1-ex-http", "exercises", "Exercício: reconstruir uma request a partir do DevTools",
                    body_md=(
                        "Abra qualquer aplicação dos labs, use o DevTools (aba Network) e escolha uma request POST.\n\n"
                        "1. Copie a request como `curl` (botão direito → Copy as cURL).\n"
                        "2. Identifique: método, caminho, headers de conteúdo (`Content-Type`, `Content-Length`), "
                        "cookie de sessão e corpo.\n"
                        "3. Reproduza a request com `curl -i` e compare o status com o do navegador.\n"
                        "4. Responda por escrito: qual header ou cookie carrega a identidade? O que acontece se você "
                        "remover só esse cookie?\n\n"
                        "Registre as observações no campo de anotações desta atividade."
                    ), minutes=30),
            ],
        ),
        unit(
            "arquitetura-web",
            "Arquitetura: cliente, servidor e API",
            "Distinguir página renderizada no servidor, SPA e API, e saber qual camada valida o quê.",
            ["SPA vs SSR", "stateless vs stateful", "onde fica a autorização"],
            [
                act("m0-u2-kb-academy-recon", "theory", "Reconhecimento antes do primeiro payload",
                    academy="recon", minutes=20),
                act("m0-u2-kb-js-bundle", "theory", "JavaScript como fonte de reconhecimento",
                    kb="ht-pentesting-web-browser-extension-pentesting-methodology-browext-clickjacking",
                    minutes=15),
                act("m0-u2-lab-js", "lab", "Ler o bundle JS para achar rotas",
                    lab="recon-js-bundle", minutes=20),
                act("m0-u2-lab-sourcemap", "lab", "Source maps expostos",
                    lab="recon-source-map", minutes=20),
                act("m0-u2-assess", "assessment", "Avaliação: o que cada camada decide",
                    minutes=15,
                    questions=[
                        {"id": "q1", "prompt": "Em uma SPA que consome uma API, onde a autorização por objeto precisa ser decidida?",
                         "accepted": ["servidor", "server", "backend", "api"]},
                        {"id": "q2", "prompt": "Qual arquivo do front pode revelar rotas internas não documentadas?",
                         "accepted": ["bundle", "js", "javascript", "source map", "sourcemap"]},
                        {"id": "q3", "prompt": "Um cookie com atributo HttpOnly pode ser lido por JavaScript na página?",
                         "accepted": ["nao", "não", "no", "false"]},
                    ]),
            ],
        ),
    ],
    summary="HTTP, sessões e arquitetura são o vocabulário do resto da trilha.",
    completion="Todas as atividades do módulo concluídas e a avaliação aprovada com 70%.",
)

# ---------------------------------------------------------------------------
# Módulo 1 — recon
# ---------------------------------------------------------------------------
m1 = mod(
    "recon",
    "Reconnaissance",
    "Mapear a superfície de ataque de uma aplicação antes de qualquer tentativa de exploração.",
    ["enumeração de diretórios", "fingerprinting", "descoberta de endpoints", "análise de JS", "mapeamento"],
    [
        unit(
            "mapeamento",
            "Mapeamento manual e automatizado",
            "Construir um inventário de rotas, parâmetros e tecnologias a partir de evidência.",
            ["ffuf/gobuster", "burp sitemap", "whatweb", "organizar inventário"],
            [
                act("m1-u1-kb-methodology", "theory", "Método: reconhecimento com propósito",
                    academy="methodology", minutes=20),
                act("m1-u1-lab-api-docs", "lab", "Documentação de API esquecida",
                    lab="recon-api-docs", minutes=20),
                act("m1-u1-lab-cloud", "lab", "Listagem de bucket exposta",
                    lab="recon-cloud-listing", minutes=20),
                act("m1-u1-ex-ffuf", "exercises", "Exercício: wordlist × alvo",
                    body_md=(
                        "Com um lab no ar, execute três passes de enumeração e registre a diferença:\n\n"
                        "1. `ffuf -w <wordlist> -u http://127.0.0.1:<porta>/FUZZ -mc 200,301,302,401,403`\n"
                        "2. Repita com `-e .js,.json`.\n"
                        "3. Repita com uma wordlist diferente (menor) e compare o que cada uma encontra.\n\n"
                        "Entregue uma tabela: rota, status, tamanho, por que ela importa. Rotas que devolvem "
                        "sempre o mesmo tamanho são provavelmente soft-404 — explique como você detectou isso."
                    ), minutes=40),
            ],
        ),
    ],
    summary="Nenhuma exploração começa sem inventário. Recon mal feito produz achado falso.",
    completion="Inventário de ao menos um alvo documentado, com os labs do módulo concluídos.",
    requires="fundamentos",
)

# ---------------------------------------------------------------------------
# Módulo 2 — authn/authz
# ---------------------------------------------------------------------------
m2 = mod(
    "autenticacao-autorizacao",
    "Autenticação e autorização",
    "Separar falhas de identidade (quem é você) de falhas de permissão (o que você pode fazer) e testar cada uma com o método correto.",
    ["enumeração de usuário", "JWT", "sessão", "IDOR/BOLA", "BFLA", "mass assignment"],
    [
        unit(
            "identidade",
            "Autenticação: sessão, reset e JWT",
            "Identificar como a identidade é provada e onde o fluxo pode ser desviado.",
            ["fluxo de login", "reset de senha", "validação de JWT"],
            [
                act("m2-u1-kb-auth", "theory", "Autenticação: identidade, sessões e recuperação",
                    academy="authentication", minutes=30),
                act("m2-u1-kb-jwt", "theory", "JWT: assinaturas, claims e gestão de chaves",
                    academy="jwt", minutes=25),
                act("m2-u1-lab-enum", "lab", "Enumeração de usuário pela resposta",
                    lab="auth-username-enum", minutes=20),
                act("m2-u1-lab-weakkey", "lab", "JWT com chave fraca",
                    lab="auth-jwt-weak-key", minutes=30),
                act("m2-u1-lab-reset", "lab", "Envenenamento de host no reset",
                    lab="auth-reset-host", minutes=30),
                act("m2-u1-lab-mfa", "lab", "Bypass de MFA por manipulação de resposta",
                    lab="auth-mfa-bypass-response", minutes=35),
            ],
        ),
        unit(
            "autorizacao",
            "Autorização: objeto, função e propriedade",
            "Provar ausência de checagem de autorização com duas identidades.",
            ["BOLA/IDOR", "BFLA", "mass assignment", "tenant"],
            [
                act("m2-u2-kb-access", "theory", "Controle de acesso: objetos, funções e tenants",
                    academy="access-control", minutes=30),
                act("m2-u2-own-bola", "theory", "BOLA: autorização em nível de objeto (documento próprio)",
                    kb="own-bola-autorizacao-objeto", minutes=25),
                act("m2-u2-lab-idor", "lab", "IDOR em faturas",
                    lab="access-idor-invoices", minutes=25),
                act("m2-u2-lab-bola", "lab", "BOLA em contas",
                    lab="access-bola-accounts", minutes=30),
                act("m2-u2-lab-bfla", "lab", "BFLA no painel admin",
                    lab="access-bfla-admin", minutes=30),
                act("m2-u2-lab-mass", "lab", "Mass assignment de papel",
                    lab="access-mass-assignment", minutes=30),
                act("m2-u2-assess", "assessment", "Avaliação: distinguir BOLA, BFLA e mass assignment",
                    minutes=20,
                    questions=[
                        {"id": "q1", "prompt": "Você usa uma rota normalmente permitida ao seu papel, mas troca o id do objeto e recebe dados de outro usuário. Qual classe é essa?",
                         "accepted": ["bola", "idor"]},
                        {"id": "q2", "prompt": "Um usuário comum chama diretamente uma rota administrativa e ela responde 200. Qual classe é essa?",
                         "accepted": ["bfla"]},
                        {"id": "q3", "prompt": "Comparar o sub do JWT com o id pedido resolve BOLA? Responda sim ou não.",
                         "accepted": ["nao", "não", "no"]},
                    ]),
            ],
        ),
    ],
    summary="A maioria dos vazamentos reais mora aqui. Teste com duas contas, sempre.",
    completion="Todos os labs do módulo concluídos e avaliação ≥ 70%.",
    requires="recon",
)

# ---------------------------------------------------------------------------
# Módulo 3 — injeções e server-side
# ---------------------------------------------------------------------------
m3 = mod(
    "vulnerabilidades-server-side",
    "Injeção e vulnerabilidades server-side",
    "Reconhecer contextos de injeção e provar execução/leitura controlada, sem depender de ferramenta.",
    ["SQLi", "SSTI", "command injection", "LFI/path traversal", "XXE", "SSRF", "NoSQL"],
    [
        unit(
            "injeção-sql",
            "Injeção de SQL",
            "Identificar o contexto da query e escolher a técnica de prova mais simples.",
            ["login bypass", "union", "blind boolean", "WAF bypass"],
            [
                act("m3-u1-kb-sqli", "theory", "SQL Injection: contexto, prova e fronteiras",
                    academy="sql-injection", minutes=35),
                act("m3-u1-lab-login", "lab", "Bypass de login por SQLi",
                    lab="sqli-login-bypass", minutes=20),
                act("m3-u1-lab-union", "lab", "Union-based em catálogo",
                    lab="sqli-union-catalog", minutes=30),
                act("m3-u1-lab-blind", "lab", "Blind boolean",
                    lab="sqli-blind-boolean", minutes=40),
                act("m3-u1-lab-waf", "lab", "SQLi com bypass de WAF",
                    lab="sqli-waf-bypass", minutes=45),
                act("m3-u1-lab-second", "lab", "SQLi de segunda ordem",
                    lab="sqli-second-order", minutes=40),
            ],
        ),
        unit(
            "arquivos-e-comandos",
            "Arquivos, comandos e templates",
            "Distinguir leitura de arquivo, execução de comando e renderização de template.",
            ["LFI", "path traversal", "command injection", "SSTI"],
            [
                act("m3-u2-kb-inclusion", "theory", "File inclusion e path traversal",
                    academy="file-inclusion", minutes=30),
                act("m3-u2-kb-cmdi", "theory", "OS Command Injection: quando o dado vira shell",
                    academy="command-injection", minutes=30),
                act("m3-u2-lab-lfi", "lab", "LFI em leitor de documentos",
                    lab="lfi-document-reader", minutes=25),
                act("m3-u2-lab-cmdi", "lab", "Injeção de comando em ping",
                    lab="command-ping", minutes=20),
                act("m3-u2-lab-blindcmdi", "lab", "Command injection cega",
                    lab="server-blind-cmdi", minutes=40),
                act("m3-u2-lab-ssti", "lab", "SSTI em cartão",
                    lab="ssti-card", minutes=35),
                act("m3-u2-lab-jinja", "lab", "SSTI com escape de sandbox Jinja",
                    lab="server-ssti-jinja-sandbox", minutes=50),
            ],
        ),
        unit(
            "requisicoes-e-dados",
            "Requestss server-side e dados estruturados",
            "Usar o servidor como proxy e explorar parsers XML/NoSQL.",
            ["SSRF", "XXE", "NoSQL"],
            [
                act("m3-u3-kb-ssrf", "theory", "Server-Side Request Forgery: posição confiável na rede",
                    academy="ssrf", minutes=30),
                act("m3-u3-lab-ssrf", "lab", "SSRF em buscador de imagem",
                    lab="ssrf-image-fetcher", minutes=30),
                act("m3-u3-lab-webhook", "lab", "SSRF via webhook",
                    lab="server-ssrf-webhook", minutes=35),
                act("m3-u3-lab-xxe", "lab", "XXE em leitor",
                    lab="server-xxe-reader", minutes=35),
                act("m3-u3-lab-nosql", "lab", "NoSQL operator auth",
                    lab="server-nosql-auth", minutes=30),
                act("m3-u3-assess", "assessment", "Avaliação: qual classe de injeção?",
                    minutes=20,
                    questions=[
                        {"id": "q1", "prompt": "O parâmetro vira `${7*7}` na resposta HTTP. Qual classe?",
                         "accepted": ["ssti", "template injection", "server-side template injection"]},
                        {"id": "q2", "prompt": "Você faz o servidor buscar http://169.254.169.254. Qual classe?",
                         "accepted": ["ssrf"]},
                        {"id": "q3", "prompt": "Qual método prova SQLi cega quando não há saída de erro nem de dados?",
                         "accepted": ["boolean", "blind", "time", "temporal", "based"]},
                    ]),
            ],
        ),
    ],
    summary="Um contexto por vez. A técnica segue o contexto, não o contrário.",
    completion="Labs do módulo concluídos (incluindo os avançados) e avaliação ≥ 70%.",
    requires="autenticacao-autorizacao",
    minutes=600,
)

# ---------------------------------------------------------------------------
# Módulo 4 — client-side
# ---------------------------------------------------------------------------
m4 = mod(
    "client-side",
    "Segurança client-side",
    "Entender o navegador como parte do sistema distribuído: o que ele confia, o que ele executa e como isso é abusado.",
    ["XSS", "CSRF", "CORS", "CSP", "clickjacking", "prototype pollution", "WebSocket"],
    [
        unit(
            "xss",
            "XSS: sources, sinks e contexto",
            "Escolher o payload pelo contexto de saída, não pela lista.",
            ["reflected", "stored", "DOM", "CSP bypass"],
            [
                act("m4-u1-kb-xss", "theory", "Cross-Site Scripting: sources, sinks e contexto",
                    academy="xss", minutes=35),
                act("m4-u1-lab-reflected", "lab", "XSS refletido em busca",
                    lab="xss-reflected-search", minutes=20),
                act("m4-u1-lab-stored", "lab", "XSS armazenado em guestbook",
                    lab="xss-stored-guestbook", minutes=25),
                act("m4-u1-lab-dom", "lab", "XSS via DOM hash",
                    lab="xss-dom-hash", minutes=25),
                act("m4-u1-lab-attr", "lab", "Injeção em atributo",
                    lab="xss-attribute-injection", minutes=25),
                act("m4-u1-lab-nonce", "lab", "Bypass de CSP nonce",
                    lab="xss-csp-nonce-bypass", minutes=45),
                act("m4-u1-lab-clobber", "lab", "DOM clobbering",
                    lab="xss-dom-clobber", minutes=40),
            ],
        ),
        unit(
            "navegador-e-sessao",
            "Navegador, CSRF e CORS",
            "Testar decisões do navegador que o servidor assume como verdadeiras.",
            ["CSRF", "CORS", "postMessage", "clickjacking", "WebSocket"],
            [
                act("m4-u2-kb-client", "theory", "Segurança Client-Side: o navegador como trust boundary",
                    academy="client-side", minutes=30),
                act("m4-u2-lab-cors", "lab", "CORS refletindo origem",
                    lab="client-cors-reflect", minutes=30),
                act("m4-u2-lab-clickjack", "lab", "Clickjacking em frame",
                    lab="client-clickjacking-frame", minutes=20),
                act("m4-u2-lab-postmsg", "lab", "postMessage sem verificação",
                    lab="client-postmessage", minutes=35),
                act("m4-u2-lab-ws-csrf", "lab", "CSRF em WebSocket",
                    lab="client-websocket-csrf", minutes=35),
                act("m4-u2-lab-proto", "lab", "Prototype pollution",
                    lab="client-prototype-pollution", minutes=35),
            ],
        ),
    ],
    summary="O navegador é atacante e vítima ao mesmo tempo. As decisões dele são testáveis.",
    completion="Labs concluídos e pelo menos um relato de impacto escrito para um XSS.",
    requires="autenticacao-autorizacao",
)

# ---------------------------------------------------------------------------
# Módulo 5 — lógica e upload
# ---------------------------------------------------------------------------
m5 = mod(
    "logica-e-upload",
    "Lógica de negócio e upload",
    "Explorar regras de negócio e o caminho de um arquivo do upload até a execução.",
    ["abuso de regra", "race condition", "upload bypass", "polyglot", "zip slip"],
    [
        unit(
            "logica",
            "Regras de negócio",
            "Traduzir a regra esperada em um teste que a viola.",
            ["cupom", "reembolso", "workflow", "race"],
            [
                act("m5-u1-kb-logic", "theory", "Lógica de negócio: abuse das regras, não do parser",
                    academy="business-logic", minutes=30),
                act("m5-u1-lab-coupon", "lab", "Empilhamento de cupom",
                    lab="logic-coupon-stack", minutes=25),
                act("m5-u1-lab-negative", "lab", "Carrinho com quantidade negativa",
                    lab="logic-negative-cart", minutes=25),
                act("m5-u1-lab-race", "lab", "Corrida de cupom",
                    lab="logic-coupon-race", minutes=40),
                act("m5-u1-lab-approval", "lab", "Autoaprovação",
                    lab="logic-approval-self", minutes=30),
                act("m5-u1-lab-workflow", "lab", "Pular etapa do fluxo",
                    lab="logic-workflow-skip", minutes=30),
            ],
        ),
        unit(
            "upload",
            "Upload de arquivos",
            "Seguir o arquivo: validação de tipo, extensão, armazenamento e execução.",
            ["content-type", "polyglot", "zip slip", "path traversal no nome"],
            [
                act("m5-u2-kb-upload", "theory", "File Upload: do arquivo armazenado ao risco armazenado",
                    academy="file-upload", minutes=30),
                act("m5-u2-lab-svg", "lab", "SVG como avatar",
                    lab="upload-svg-avatar", minutes=25),
                act("m5-u2-lab-ctype", "lab", "Confusão de Content-Type",
                    lab="upload-content-type-confusion", minutes=30),
                act("m5-u2-lab-polyglot", "lab", "Polyglot GIF/HTML",
                    lab="upload-polyglot-image", minutes=35),
                act("m5-u2-lab-zipslip", "lab", "Zip slip",
                    lab="upload-zip-slip", minutes=35),
                act("m5-u2-lab-archive", "lab", "Traversal em arquivo tar",
                    lab="upload-archive-traversal", minutes=40),
            ],
        ),
    ],
    summary="A regra de negócio é a superfície; o upload é o caminho até o disco.",
    completion="Todos os labs do módulo concluídos.",
    requires="client-side",
)

# ---------------------------------------------------------------------------
# Módulo 6 — avançado
# ---------------------------------------------------------------------------
m6 = mod(
    "exploracao-avancada",
    "Exploração avançada",
    "Ataques que exigem entender infraestrutura e estado: cache, desserialização, host header, encadeamento.",
    ["cache poisoning/deception", "deserialização", "host header", "chaining"],
    [
        unit(
            "infra-e-estado",
            "Cache, host header e desserialização",
            "Explorar decisões de infraestrutura que o aplicativo não controla.",
            ["cache key", "poisoning", "host header", "pickle"],
            [
                act("m6-u1-kb-cache", "theory", "Cache Deception e Poisoning",
                    academy="cache-deception", minutes=30),
                act("m6-u1-lab-cached", "lab", "Cache deception",
                    lab="adv-cache-deception", minutes=35),
                act("m6-u1-lab-poison", "lab", "Cache poisoning por header",
                    lab="adv-cache-poison-header", minutes=40),
                act("m6-u1-lab-keynorm", "lab", "Normalização de chave de cache",
                    lab="adv-cache-key-normalization", minutes=35),
                act("m6-u1-lab-host", "lab", "Host header no fluxo de reset",
                    lab="adv-http-host-header-reset", minutes=35),
                act("m6-u1-lab-pickle", "lab", "Desserialização de pickle em cookie",
                    lab="server-deserialization-pickle", minutes=45),
            ],
        ),
        unit(
            "encadeamento",
            "Encadeamento de vulnerabilidades",
            "Combinar dois achados médios em um impacto alto e documentar cada elo.",
            ["cadeia", "impacto", "evidência por elo"],
            [
                act("m6-u2-kb-chain", "theory", "Encadeamento: do achado ao objetivo",
                    academy="chaining", minutes=30),
                act("m6-u2-lab-idor-admin", "lab", "IDOR até admin",
                    lab="chain-idor-to-admin", minutes=45),
                act("m6-u2-lab-jwt-sqli", "lab", "JWT até SQLi",
                    lab="chain-jwt-to-sqli", minutes=45),
                act("m6-u2-lab-xss-csrf", "lab", "XSS até CSRF admin",
                    lab="chain-xss-to-csrf-admin", minutes=50),
                act("m6-u2-lab-lfi-rce", "lab", "LFI até RCE",
                    lab="chain-lfi-to-rce", minutes=60),
            ],
        ),
    ],
    summary="Impacto raramente vem de um único bug. Vem da composição.",
    completion="Pelo menos duas cadeias concluídas com relato de elo por elo.",
    requires="logica-e-upload",
    minutes=480,
)

# ---------------------------------------------------------------------------
# Módulo 7 — pentest realista
# ---------------------------------------------------------------------------
m7 = mod(
    "pentest-realista",
    "Pentest web realista",
    "Executar um engajamento completo contra alvo multi-estágio e produzir relatório técnico.",
    ["metodologia completa", "máquina", "evidências", "relatório"],
    [
        unit(
            "engajamento",
            "Da recon ao relatório",
            "Aplicar a metodologia em uma máquina completa sem indicação de vulnerabilidades.",
            ["recon", "exploração", "pós-exploração", "relatório"],
            [
                act("m7-u1-kb-quickref", "theory", "Referência rápida do operador",
                    academy="quick-reference", minutes=15),
                act("m7-u1-lab-meridian", "lab", "Máquina: Meridian Bank",
                    lab="machine-meridian-bank", minutes=60),
                act("m7-u1-lab-nexus", "lab", "Máquina: Nexus Commerce",
                    lab="machine-nexus-commerce", minutes=70),
                act("m7-u1-lab-horizon", "lab", "Máquina: Horizon Health",
                    lab="realistic-horizon-health", minutes=80),
                act("m7-u1-lab-atlas", "lab", "Máquina: Atlas HR",
                    lab="machine-hr-onboarding", minutes=60),
                act("m7-u1-report", "project", "Relatório técnico de uma máquina",
                    minutes=90,
                    body_md=(
                        "Escolha **uma** das máquinas concluídas neste módulo e produza um relatório "
                        "técnico completo.\n\n"
                        "Estrutura obrigatória:\n\n"
                        "1. Escopo e regras de engajamento (o que estava dentro).\n"
                        "2. Superfície: rotas, parâmetros e tecnologias, com como você descobriu.\n"
                        "3. Achados: para cada um, request reprodutível, resposta, impacto, severidade "
                        "e referência (CWE/OWASP).\n"
                        "4. Cadeia: como os achados se encadearam até cada flag.\n"
                        "5. Correção: por achado, a mudança mínima que fecha a falha.\n"
                        "6. Evidências: trechos de request/response, sem expor valores de flag.\n\n"
                        "Critério de aceite: um leitor que não participou do teste consegue reproduzir "
                        "cada achado a partir do relatório."
                    )),
            ],
        ),
    ],
    summary="Sem lista de vulnerabilidades. Sem mão na mão. Reconhecimento decide.",
    completion="Máquina concluída e relatório entregue com todos os itens da estrutura.",
    requires="exploracao-avancada",
    minutes=420,
)

path = {
    "slug": "web-application-pentesting",
    "title": "Web Application Pentesting",
    "codename": "WEB",
    "domain": "web",
    "summary": "Formação completa em testes de segurança de aplicações web: do HTTP ao encadeamento de vulnerabilidades em alvo realista.",
    "description": (
        "A trilha começa no vocabulário mínimo (HTTP, sessão, arquitetura) e termina em um "
        "engajamento completo contra uma máquina multi-estágio. Cada módulo tem teoria ancorada "
        "na Knowledge Base, exercícios guiados, laboratórios reais da plataforma e uma avaliação. "
        "As ferramentas (Burp, ZAP, curl, ffuf, nmap, katana) aparecem onde são necessárias, não "
        "como uma lista separada."
    ),
    "entry_level": "iniciante com Linux e linha de comando",
    "exit_level": "operador capaz de conduzir um pentest web completo e documentá-lo",
    "estimated_hours": 70,
    "priority": 10,
    "phase": 1,
    "icon": "radar",
    "accent": "red",
    "prerequisites": [],
    "competencies": [
        "Ler e reproduzir requests HTTP",
        "Mapear superfície de ataque",
        "Provar falhas de autenticação e autorização",
        "Explorar injeções e falhas server-side",
        "Testar decisões do navegador",
        "Abusar de regras de negócio e upload",
        "Encadear vulnerabilidades",
        "Produzir relatório técnico",
    ],
    "tools": ["Burp Suite", "OWASP ZAP", "curl", "ffuf", "gobuster", "katana", "nmap", "sqlmap", "whatweb"],
    "equipment": "Somente software. Todos os laboratórios rodam em loopback na própria plataforma.",
    "modules": [m0, m1, m2, m3, m4, m5, m6, m7],
    "capstone": {
        "objective": "Conduzir uma avaliação web completa contra um alvo desconhecido e entregar o relatório.",
        "scope_md": (
            "Escolha **uma** máquina ainda não resolvida entre `realistic-horizon-health`, "
            "`machine-logistics-api`, `machine-insurance-claims`, `machine-saas-admin-console`. "
            "O escopo é a origem loopback atribuída pelo gerenciador de labs; nada fora dela."
        ),
        "resources_md": (
            "Plataforma REDVAULT (catch, reset, flags), Burp Suite ou OWASP ZAP, curl, ffuf, nmap. "
            "Nenhum recurso pago."
        ),
        "steps_md": (
            "1. Reconhecimento sem exploração: rotas, tecnologias, autenticação observada.\n"
            "2. Mapeamento de trust boundaries por funcionalidade.\n"
            "3. Teste de autenticação e autorização com duas identidades.\n"
            "4. Teste de entrada: injeção, upload, SSRF onde o fluxo permitir.\n"
            "5. Exploração encadeada até cada flag, registrando request/resposta.\n"
            "6. Relatório final com achados, impacto e correção."
        ),
        "success_criteria": [
            "Todas as flags obrigatórias da máquina obtidas",
            "Cada achado com request e resposta reproduzíveis",
            "Achados classificados por severidade com referência CWE ou OWASP",
            "Correção proposta para cada achado",
            "Relatório sem valores de flag",
        ],
        "evidence": [
            "Log de requests por ferramenta (Burp/ZAP export)",
            "Capturas de resposta que provam o acesso indevido",
            "Notas de recon com a origem de cada rota descoberta",
            "Relatório final em Markdown",
        ],
        "expected_result": "Relatório de pentest web completo e máquina resolvida.",
        "grading_md": (
            "Distingue-se a nota por: cobertura de superfície (25%), profundidade de cada achado (25%), "
            "qualidade da evidência (20%), correção adequada (20%) e clareza do relatório (10%). "
            "Flag obtida sem evidência documentada não pontua."
        ),
        "challenge_slug": "machine-saas-admin-console",
    },
}

out = ROOT / "content" / "learning_paths" / "01-web-application-pentesting.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")