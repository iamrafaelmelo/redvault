#!/usr/bin/env python3
"""Generate content/learning_paths/*.json for the Phase-1 API path."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_path_web import act, mod, unit  # noqa: E402

m0 = mod(
    "contratos-e-http",
    "Contratos de API e HTTP",
    "Ler o contrato de uma API e saber onde cada decisão de segurança deveria estar.",
    ["REST", "verbos", "status codes", "JSON", "versionamento", "documentação"],
    [
        unit(
            "rest",
            "REST, verbos e status",
            "Distinguir uma API resource-oriented de RPC disfarçado e o que isso muda no teste.",
            ["métodos", "idempotência", "status semântico"],
            [
                act("api-m0-u1-kb-academy", "theory", "Segurança de API: contratos, objetos e versões",
                    academy="api-security", minutes=30),
                act("api-m0-u1-lab-docs", "lab", "Descobrir documentação exposta",
                    lab="recon-api-docs", minutes=20),
                act("api-m0-u1-lab-learning", "lab", "Listagem de dados de aprendizado",
                    lab="recon-cloud-listing", minutes=20),
                act("api-m0-u1-ex-contract", "exercises", "Exercício: escrever o contrato observado",
                    body_md=(
                        "Escolha um lab de API no ar e, **sem ler o código do lab**, escreva o contrato "
                        "observado:\n\n"
                        "1. Liste cada rota com método, parâmetros (path, query, body) e status de sucesso.\n"
                        "2. Marque quais rotas são idempotentes na prática (repita a request 3× e compare).\n"
                        "3. Marque o que a documentação pública diz e onde a implementação diverge.\n\n"
                        "A divergência entre documentação e implementação é o achado: registre as duas versões."
                    ), minutes=45),
            ],
        ),
    ],
    summary="Antes de testar autorização, é preciso saber o que a API promete.",
    completion="Contrato escrito de um alvo com divergências anotadas.",
)

m1 = mod(
    "objetos-e-funcoes",
    "Autorização de objetos, funções e propriedades",
    "Provar BOLA, BFLA e exposição excessiva com duas identidades.",
    ["BOLA", "BFLA", "mass assignment", "excessive data exposure", "tenant"],
    [
        unit(
            "bola-bfla",
            "Objeto e função",
            "Diferenciar e testar cada nível de autorização.",
            ["duas contas", "troca de id", "rota admin"],
            [
                act("api-m1-u1-own-bola", "theory", "BOLA: autorização em nível de objeto",
                    kb="own-bola-autorizacao-objeto", minutes=25),
                act("api-m1-u1-kb-access", "theory", "Controle de acesso em revisão",
                    academy="access-control", minutes=25),
                act("api-m1-u1-lab-bola", "lab", "BOLA em contas",
                    lab="access-bola-accounts", minutes=30),
                act("api-m1-u1-lab-bfla", "lab", "BFLA em admin",
                    lab="access-bfla-admin", minutes=30),
                act("api-m1-u1-lab-tenant", "lab", "Tenant header",
                    lab="access-tenant-header", minutes=30),
                act("api-m1-u1-lab-method", "lab", "Method override",
                    lab="access-method-override", minutes=25),
                act("api-m1-u1-lab-hpp", "lab", "HTTP parameter pollution",
                    lab="access-http-parameter-pollution", minutes=30),
            ],
        ),
        unit(
            "propriedades",
            "Propriedades e dados excessivos",
            "Testar o que o servidor aceita gravar e o que ele devolve a mais.",
            ["mass assignment", "excessive data", "paginação"],
            [
                act("api-m1-u2-lab-mass", "lab", "Mass assignment",
                    lab="access-mass-assignment", minutes=30),
                act("api-m1-u2-lab-excessive", "lab", "Excessive data exposure",
                    lab="api-excessive-data", minutes=30),
                act("api-m1-u2-lab-pagination", "lab", "Vazamento por paginação",
                    lab="api-pagination-leak", minutes=35),
                act("api-m1-u2-lab-version", "lab", "Downgrade de versão",
                    lab="api-version-downgrade", minutes=35),
                act("api-m1-u2-assess", "assessment", "Avaliação: nomear a categoria",
                    minutes=20,
                    questions=[
                        {"id": "q1", "prompt": "A resposta de /users/me traz o hash de senha e o salário. Qual categoria OWASP API?",
                         "accepted": ["api3", "excessive data", "excessive data exposure", "exposição excessiva"]},
                        {"id": "q2", "prompt": "Você envia `\"role\":\"admin\"` num PUT /profile e vira admin. Qual classe?",
                         "accepted": ["mass assignment", "mass-assignment"]},
                        {"id": "q3", "prompt": "Qual teste distingue BOLA de BFLA?",
                         "accepted": ["papel", "role", "duas contas", "different role"]},
                    ]),
            ],
        ),
    ],
    summary="Cada nível de autorização tem um teste próprio.",
    completion="Todos os labs e avaliação ≥ 70%.",
    requires="contratos-e-http",
)

m2 = mod(
    "identidade-e-tokens",
    "Identidade, tokens e federação",
    "Analisar JWT, OAuth 2.0 e OIDC como sistemas de confiança e atacar cada ponto de validação.",
    ["JWT", "OAuth 2.0", "OIDC", "sessão", "refresh"],
    [
        unit(
            "jwt",
            "JWT",
            "Ataque assinatura, header e claims.",
            ["alg confusion", "kid traversal", "jku injection"],
            [
                act("api-m2-u1-kb-jwt", "theory", "JWT: assinaturas, claims e chaves",
                    academy="jwt", minutes=30),
                act("api-m2-u1-lab-weak", "lab", "Chave fraca",
                    lab="auth-jwt-weak-key", minutes=30),
                act("api-m2-u1-lab-alg", "lab", "Algorithm confusion",
                    lab="auth-jwt-alg-confusion", minutes=40),
                act("api-m2-u1-lab-kid", "lab", "kid traversal",
                    lab="auth-jwt-kid-traversal", minutes=40),
                act("api-m2-u1-lab-jku", "lab", "jku injection",
                    lab="auth-jwt-jku-injection", minutes=40),
            ],
        ),
        unit(
            "oauth-oidc",
            "OAuth 2.0 e OpenID Connect",
            "Entender fluxo, redirect_uri, state e validação de ID Token.",
            ["fluxos", "redirect_uri", "ID Token", "nonce"],
            [
                act("api-m2-u2-own-oidc", "theory", "OpenID Connect: ID Token e validação",
                    kb="own-oidc-openid-connect", minutes=30),
                act("api-m2-u2-kb-oauth", "theory", "OAuth Misconfiguration",
                    kb="patt-oauth-misconfiguration-readme", minutes=20),
                act("api-m2-u2-lab-sso", "lab", "Replay de assertion SSO",
                    lab="auth-sso-assertion-replay", minutes=45),
                act("api-m2-u2-lab-reset", "lab", "Reset host poisoning",
                    lab="auth-reset-host", minutes=30),
                act("api-m2-u2-lab-fixation", "lab", "Session fixation",
                    lab="auth-session-fixation", minutes=30),
                act("api-m2-u2-lab-otp", "lab", "Bruteforce de OTP",
                    lab="auth-otp-bruteforce", minutes=30),
            ],
        ),
    ],
    summary="Token é assinatura + claims + validação. Falha em qualquer um dos três.",
    completion="Labs de JWT e SSO concluídos.",
    requires="objetos-e-funcoes",
)

m3 = mod(
    "graphql-e-protocolos",
    "GraphQL, SOAP e webhooks",
    "Testar APIs que não são REST: autenticação por campo, batch, schema e webhook.",
    ["GraphQL", "batch", "SOAP", "webhook", "rate limit"],
    [
        unit(
            "graphql",
            "GraphQL",
            "Testar autorização por campo e por operação.",
            ["introspection", "field auth", "alias", "batch"],
            [
                act("api-m3-u1-kb-graphql", "theory", "GraphQL Injection e enumeração de schema",
                    kb="patt-graphql-injection-readme", minutes=25),
                act("api-m3-u1-lab-field", "lab", "Autorização por campo",
                    lab="api-graphql-field-auth", minutes=40),
                act("api-m3-u1-lab-batch", "lab", "Batch endpoint auth",
                    lab="api-batch-endpoint-auth", minutes=40),
            ],
        ),
        unit(
            "outros-protocolos",
            "Webhooks, SOAP e limites",
            "Explorar confiança em callbacks e ausência de limite.",
            ["webhook forging", "SSRF em webhook", "rate limit"],
            [
                act("api-m3-u2-lab-webhook", "lab", "Webhook SSRF",
                    lab="server-ssrf-webhook", minutes=35),
                act("api-m3-u2-lab-race", "lab", "Corrida em operação de API",
                    lab="logic-race-withdraw", minutes=40),
                act("api-m3-u2-lab-otp", "lab", "Ausência de rate limit em OTP",
                    lab="auth-otp-bruteforce", minutes=30),
            ],
        ),
    ],
    summary="API não é só REST. Cada protocolo tem seu modelo de confiança.",
    completion="Labs de GraphQL e webhook concluídos.",
    requires="identidade-e-tokens",
)

m4 = mod(
    "pentest-api-realista",
    "Pentest de API realista",
    "Executar avaliação completa de API multi-serviço e entregar relatório.",
    ["inventário", "autorização", "encadeamento", "relatório"],
    [
        unit(
            "engajamento",
            "Engajamento",
            "Aplicar o método em máquina orientada a API.",
            ["recon", "exploração", "relatório"],
            [
                act("api-m4-u1-lab-logistics", "lab", "Máquina: Wayline Logistics",
                    lab="machine-logistics-api", minutes=70),
                act("api-m4-u1-lab-fintech", "lab", "Máquina: Finch Support",
                    lab="machine-fintech-support", minutes=70),
                act("api-m4-u1-report", "project", "Relatório de avaliação de API",
                    minutes=90,
                    body_md=(
                        "Produza o relatório de **uma** das máquinas deste módulo.\n\n"
                        "Obrigatório: inventário de endpoints com o método de descoberta; matriz de "
                        "autorização (ator × objeto × função); cada achado com request/response; "
                        "classificação OWASP API Top 10; correção por achado.\n\n"
                        "O relatório deve permitir que outro operador reproduza cada achado."
                    )),
            ],
        ),
    ],
    summary="Duas máquinas com superfície de API real.",
    completion="Máquina concluída e relatório entregue.",
    requires="graphql-e-protocolos",
    minutes=240,
)

path = {
    "slug": "api-security",
    "title": "API Security & API Pentesting",
    "codename": "API",
    "domain": "api",
    "summary": "Segurança de APIs REST, GraphQL e federação de identidade, com laboratórios reais da plataforma.",
    "description": (
        "A trilha trata a API como sistema distribuído: contrato, autorização em três níveis "
        "(objeto, função, propriedade), identidade via JWT/OAuth/OIDC, e protocolos que não são "
        "REST. Os laboratórios são aplicações reais que expõem API, e o capstone exige o "
        "relatório com matriz de autorização."
    ),
    "entry_level": "confortável com HTTP e ferramentas de linha de comando",
    "exit_level": "capaz de auditar APIs e documentar falhas de autorização encadeadas",
    "estimated_hours": 45,
    "priority": 20,
    "phase": 1,
    "icon": "plug",
    "accent": "amber",
    "prerequisites": ["web-application-pentesting"],
    "competencies": [
        "Escrever contrato observado de API",
        "Provar BOLA/BFLA com duas identidades",
        "Identificar exposição excessiva e mass assignment",
        "Atacar JWT e falhas de federação OIDC",
        "Testar GraphQL e webhooks",
        "Encadear falhas de API até acesso administrativo",
    ],
    "tools": ["Burp Suite", "OWASP ZAP", "curl", "jq", "httpx", "ffuf", "Postman/Insomnia"],
    "equipment": "Somente software.",
    "modules": [m0, m1, m2, m3, m4],
    "capstone": {
        "objective": "Avaliar duas aplicações com API e entregar relatório com matriz de autorização.",
        "scope_md": "As máquinas `machine-logistics-api` e `machine-fintech-support`, em loopback.",
        "resources_md": "REDVAULT, Burp/ZAP, curl, jq.",
        "steps_md": (
            "1. Descobrir documentação e inventariar endpoints.\n"
            "2. Criar duas identidades e montar a matriz ator × objeto × função.\n"
            "3. Testar cada célula da matriz.\n"
            "4. Explorar os achados até as flags.\n"
            "5. Escrever o relatório."
        ),
        "success_criteria": [
            "Matriz de autorização completa para ao menos uma máquina",
            "Achados com request/response reproduzíveis",
            "Classificação OWASP API Top 10 por achado",
            "Correção proposta por achado",
        ],
        "evidence": [
            "Export do Burp/ZAP",
            "Matriz de autorização em tabela",
            "Relatório em Markdown",
        ],
        "expected_result": "Relatório de segurança de API com matriz de autorização validada.",
        "grading_md": "Cobertura da matriz 30%, evidência 30%, correção 20%, encadeamento 20%.",
        "challenge_slug": "machine-logistics-api",
    },
}

out = ROOT / "content" / "learning_paths" / "02-api-security.json"
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")