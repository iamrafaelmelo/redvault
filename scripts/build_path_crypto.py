#!/usr/bin/env python3
"""Generate content/learning_paths/15-applied-crypto.json (Criptografia Aplicada).

A base importada cobre primitivas, RSA, primitivas simétricas, TLS e certificados,
além de JWT/OAuth/SAML do lado web. Dois documentos próprios preenchem as lacunas
apontadas no audit: HMAC/integridade e PKI.

A trilha é de avaliação e implementação correta, não de criptoanálise matemática.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

C = "ht-crypto"
HASH = C + "-hashes"
SYM = C + "-symmetric"
PUB = C + "-public-key"
RSA = C + "-public-key-rsa"
TLS = C + "-tls-and-certificates"
CTF = C + "-ctf-workflow"
CTF_MISC = C + "-ctf-misc"
MAL = C + "-crypto-in-malware"
HMAC = "own-hmac-e-integridade"
PKI = "own-pki-cadeia-confianca"
JWT = "ht-pentesting-web-hacking-jwt-json-web-tokens"
JWT_P = "patt-json-web-token-readme"
OAUTH = "ht-pentesting-web-oauth-to-account-takeover"
SAML = "ht-pentesting-web-saml-attacks"
LDAP = "ht-windows-hardening-active-directory-methodology-ldap-signing-and-channel-binding"
STEGO = "ht-stego"

m0 = mod(
    "primitivas",
    "Primitivas e o que cada uma garante",
    "Distinguir hash, MAC, cifra e KDF pelo problema que resolvem.",
    ["hash", "MAC", "cifra simétrica", "modo de operação", "KDF"],
    [
        unit(
            "hash-e-mac",
            "Hash e MAC",
            "Saber quando hash basta e quando é preciso chave.",
            ["digest", "integridade", "autenticação", "tempo constante"],
            [
                act("cry-m0-u1-own-hmac", "theory", "HMAC, hash e MAC",
                    kb=HMAC, minutes=60),
                act("cry-m0-u1-kb-hashes", "theory", "Hashes, MACs e KDFs",
                    kb=HASH, minutes=50),
                act("cry-m0-u1-kb-ctf", "theory", "Fluxo de trabalho de Crypto CTF",
                    kb=CTF, minutes=40),
                act("cry-m0-u1-kb-ctf-misc", "theory", "Crypto CTF Misc",
                    kb=CTF_MISC, minutes=35),
                act("cry-m0-u1-ex-extensao", "exercises",
                    "Exercício: reproduzir ataque de extensão de comprimento",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Implemente `hash(chave || mensagem)` e `HMAC(chave, mensagem)` "
                        "com SHA-256.\n"
                        "2. Para o primeiro, mostre que é possível calcular o hash de "
                        "`mensagem || extensão` sem conhecer a chave (use a técnica de "
                        "estado interno do SHA-256; uma biblioteca de referência ou "
                        "implementação didática serve).\n"
                        "3. Repita a tentativa com HMAC e mostre por que falha.\n\n"
                        "Entregue a demonstração e duas frases explicando por que a chave "
                        "aparece em **dois** pontos no HMAC."
                    )),
            ],
        ),
        unit(
            "cifra-e-kdf",
            "Cifra e KDF",
            "Escolher modo e custo corretos, e saber o que cada erro revela.",
            ["modo de operação", "IV", "salt", "PBKDF2", "argon2"],
            [
                act("cry-m0-u2-kb-sym", "theory", "Criptografia simétrica",
                    kb=SYM, minutes=50),
                act("cry-m0-u2-ex-modo", "exercises",
                    "Exercício: demonstrar por que ECB não pode ser usado em dado estruturado",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Cifre uma imagem pequena em ECB e em CBC.\n"
                        "2. Compare as duas saídas visualmente.\n"
                        "3. Responda: o que a estrutura visível na saída de ECB revela sobre "
                        "o texto claro?\n"
                        "4. Explique por que IV fixo em CBC tem problema equivalente.\n\n"
                        "Entregue as duas imagens e as respostas. A lição é que modo não é "
                        "detalhe de implementação: é parte da segurança."
                    )),
                act("cry-m0-u2-ex-kdf", "exercises",
                    "Exercício: medir o custo de um KDF de senha",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Faça um hash de senha com SHA-256 puro e outro com PBKDF2 de "
                        "100 000 iterações.\n"
                        "2. Meça o tempo de cada um.\n"
                        "3. Estime quantas tentativas por segundo um atacante faria em cada "
                        "caso.\n\n"
                        "Responda: por que 'hash de senha' com função rápida é mais perigoso "
                        "que um vazamento comum? E por que o salt **não** impede ataque de "
                        "dicionário, apenas o de tabela pré-computada?"
                    )),
            ],
        ),
    ],
    summary="Hash, MAC, cifra e KDF: qual problema cada um resolve e qual erro cada um permite.",
    completion="Ataque de extensão reproduzido, ECB demonstrado e custo de KDF medido.",
)

m1 = mod(
    "chave-publica-e-pki",
    "Chave pública e PKI",
    "Entender assinatura, certificado e cadeia de confiança.",
    ["RSA", "assinatura", "X.509", "cadeia", "revogação"],
    [
        unit(
            "chave-publica",
            "Chave pública",
            "Separar o que a chave pública garante do que a assinatura garante.",
            ["RSA", "assinatura", "verificação", "padding"],
            [
                act("cry-m1-u1-kb-pub", "theory", "Criptografia de chave pública",
                    kb=PUB, minutes=50),
                act("cry-m1-u1-kb-rsa", "theory", "Ataques RSA",
                    kb=RSA, minutes=45),
                act("cry-m1-u1-ex-assinatura", "exercises",
                    "Exercício: assinar e verificar com e sem padding",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Gere um par de chaves.\n"
                        "2. Assine uma mensagem com esquema com padding definido.\n"
                        "3. Verifique a assinatura; depois altere um byte e verifique de novo.\n"
                        "4. Descreva o que muda se o esquema não usar padding estruturado.\n\n"
                        "Entregue o resultado e a explicação. A assinatura é sobre o **hash**, "
                        "com padding — sem isso a construção perde as propriedades que "
                        "promete."
                    )),
            ],
        ),
        unit(
            "pki",
            "PKI",
            "Avaliar certificado, cadeia, nome e revogação.",
            ["X.509", "SAN", "validade", "cadeia", "revogação"],
            [
                act("cry-m1-u2-own-pki", "theory", "PKI na prática: cadeia, validação e erros",
                    kb=PKI, minutes=60),
                act("cry-m1-u2-kb-tls", "theory", "TLS e certificados",
                    kb=TLS, minutes=50),
                act("cry-m1-u2-ex-cadeia", "exercises",
                    "Exercício: inspecionar a cadeia de um certificado real",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Abra uma conexão TLS com um site e extraia a cadeia "
                        "(`openssl s_client -showcerts`).\n"
                        "2. Para cada certificado, registre: titular, nomes alternativos, "
                        "validade, uso e emissor.\n"
                        "3. Verifique se a cadeia termina numa raiz confiável.\n"
                        "4. Teste o que acontece se o nome esperado não casar com os SANs.\n\n"
                        "Entregue a cadeia e as respostas. 'Usa HTTPS' não é evidência "
                        "de nada; a cadeia é."
                    )),
            ],
        ),
    ],
    summary="Assinatura, certificado e cadeia. O que cada um prova e o que nenhum prova.",
    prereq="primitivas",
    completion="Assinatura verificada, cadeia inspecionada e teste de nome realizado.",
)

m2 = mod(
    "aplicada-a-protocolos",
    "Criptografia aplicada a protocolos",
    "Auditar onde a primitiva correta é usada errado.",
    ["JWT", "OAuth", "SAML", "LDAP", "canal"],
    [
        unit(
            "tokens",
            "Tokens",
            "Avaliar JWT, OAuth e SAML pelo que a assinatura e o canal garantem.",
            ["JWT", "alg confusion", "OAuth", "SAML assertion"],
            [
                act("cry-m2-u1-kb-jwt", "theory", "Vulnerabilidades JWT",
                    kb=JWT, minutes=50),
                act("cry-m2-u1-kb-jwt-p", "theory", "JWT — JSON Web Token",
                    kb=JWT_P, minutes=40),
                act("cry-m2-u1-kb-oauth", "theory", "OAuth para tomada de conta",
                    kb=OAUTH, minutes=45),
                act("cry-m2-u1-kb-saml", "theory", "Ataques SAML",
                    kb=SAML, minutes=45),
                act("cry-m2-u1-lab-jwt", "lab", "Tomada de conta por JWT",
                    lab="chain-jwt-to-sqli", minutes=50),
            ],
        ),
        unit(
            "canais",
            "Canais e diretórios",
            "Avaliar canal, assinatura de tráfego e metadado.",
            ["LDAP signing", "TLS", "canal binding", "esteganografia"],
            [
                act("cry-m2-u2-kb-ldap", "theory", "Fortalecimento de LDAP Signing e Channel Binding",
                    kb=LDAP, minutes=40),
                act("cry-m2-u2-kb-mal", "theory", "Criptografia em malware",
                    kb=MAL, minutes=40),
                act("cry-m2-u2-kb-stego", "theory", "Stego",
                    kb=STEGO, minutes=35),
                act("cry-m2-u2-ex-token", "exercises",
                    "Exercício: revisar um JWT e dizer o que ele garante",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Use um JWT seu, gerado localmente.\n\n"
                        "1. Decodifique cabeçalho e corpo (sem validar assinatura).\n"
                        "2. Identifique algoritmo e campos de expiração.\n"
                        "3. Liste o que o token **garante** e o que é apenas declaração.\n"
                        "4. Descreva o que acontece se `alg` for aceito do cliente sem "
                        "verificação de qual algoritmo o servidor espera.\n\n"
                        "Entregue as duas listas. A primeira é curta — e é o motivo de tanta "
                        "falha em JWT."
                    )),
            ],
        ),
    ],
    summary="JWT, OAuth, SAML, LDAP e o que a assinatura garante em cada protocolo.",
    prereq="chave-publica-e-pki",
    completion="Token revisado e garantias separadas de declaração.",
)

m3 = mod(
    "avaliacao-e-relatorio",
    "Avaliação e relatório",
    "Aplicar checklist de avaliação criptográfica e descrever achado com mecanismo.",
    ["inventário", "configuração", "achado", "correção"],
    [
        unit(
            "inventario",
            "Inventário de uso",
            "Localizar onde criptografia é usada e com qual configuração.",
            ["inventário", "modo", "chave", "rotação"],
            [
                act("cry-m3-u1-ex-inventario", "exercises",
                    "Exercício: inventariar uso criptográfico de uma aplicação sua",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Escolha uma aplicação que você tem (servidor local, app próprio).\n\n"
                        "1. Onde há criptografia? (transporte, armazenamento, token)\n"
                        "2. Para cada ponto: primitiva, modo, tamanho de chave, gestão de chave.\n"
                        "3. Onde há hash usado onde deveria haver MAC? Ou hash rápido onde "
                        "deveria haver KDF?\n\n"
                        "Entregue a tabela. O achado criptográfico mais comum não é algoritmo "
                        "quebrado: é primitiva certa no lugar errado."
                    )),
                act("cry-m3-u1-ex-achado", "exercises",
                    "Exercício: escrever o achado com mecanismo e correção",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Pegue um item do inventário e escreva o achado no formato:\n\n"
                        "1. **Configuração observada** (com evidência).\n"
                        "2. **Mecanismo** — por que aquilo permite o que permite.\n"
                        "3. **Impacto realista**.\n"
                        "4. **Correção mínima** e o que ela fecha.\n\n"
                        "Se você escrever 'criptografia fraca' sem o item 2, o achado é "
                        "recusado: quem lê precisa poder verificar o mecanismo sem confiar na "
                        "sua word escolhida."
                    )),
                act("cry-m3-u1-assess", "assessment", "Avaliação: criptografia aplicada",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "O que HMAC impede que hash(chave || mensagem) não impede?",
                         "accepted": ["ataque de extensão de comprimento", "extensao de comprimento"],
                         "explanation": "A chave em dois pontos interrompe a capacidade de estender a mensagem a partir do estado interno conhecido."},
                        {"id": "q2", "prompt": "Por que um hash rápido é ruim para senha?",
                         "accepted": ["permite muitas tentativas por segundo", "não tem custo por tentativa"],
                         "explanation": "Sem custo, o atacante testa bilhões de tentativas; KDF adiciona trabalho por tentativa."},
                        {"id": "q3", "prompt": "O que o salt impede?",
                         "accepted": ["tabela pré-computada", "rainbow table"],
                         "explanation": "Salt por usuário invalida tabelas prontas; não impede dicionário, que precisa de custo por tentativa."},
                        {"id": "q4", "prompt": "Por que desabilitar a verificação de hostname em TLS é grave?",
                         "accepted": ["qualquer certificado válido passa a ser aceito", "permite interceptação"],
                         "explanation": "Sem checar o nome, um certificado legítimo de outro domínio serve para interceptar."},
                    ]),
                act("cry-m3-u1-project", "project",
                    "Capstone: avaliação criptográfica de uma aplicação própria",
                    minutes=150,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "Escolha uma aplicação sua (serviço local, API própria) e avalie o uso "
                        "criptográfico.\n\n"
                        "Entregue:\n\n"
                        "1. Inventário completo com primitiva, modo, tamanho e gestão de chave.\n"
                        "2. Demonstração de pelo menos um erro de uso (ECB, hash rápido para "
                        "senha, assinatura sem padding, token sem verificação de algoritmo) "
                        "com o comportamento observado.\n"
                        "3. Achados com mecanismo, impacto e correção.\n"
                        "4. Avaliação de transporte: cadeia e verificação de nome.\n"
                        "5. Limitações.\n\n"
                        "Recusa: achado sem mecanismo, ou 'está seguro' sem inventário."
                    )),
            ],
        ),
    ],
    summary="Inventário, mecanismo, correção e a demonstração de um erro real.",
    prereq="aplicada-a-protocolos",
    completion="Inventário criptográfico, achado com mecanismo e avaliação aprovada.",
)

path = {
    "slug": "applied-crypto",
    "title": "Criptografia Aplicada",
    "codename": "CRY",
    "domain": "crypto",
    "summary": "Hash, MAC, KDF, RSA, PKI e tokens: avaliar onde a primitiva correta é usada errado e descrever o mecanismo do erro.",
    "description": (
        "Trilha de avaliação e implementação, não de criptoanálise matemática. Cruza o "
        "material importado de primitivas, RSA, TLS e tokens (JWT, OAuth, SAML) com dois "
        "documentos próprios sobre HMAC/integridade e PKI. O foco é o erro de uso: "
        "primitiva certa no lugar errado, que é a causa da maior parte dos problemas "
        "criptográficos reais."
    ),
    "entry_level": "Programação e noções de redes",
    "exit_level": "capaz de avaliar uso criptográfico de uma aplicação e escrever achado com mecanismo",
    "estimated_hours": 28,
    "priority": 82,
    "phase": 3,
    "icon": "key",
    "accent": "amber",
    "prerequisites": ["web-application-pentesting", "api-security"],
    "competencies": [
        "Distinguir hash, MAC e KDF pelo problema que resolvem",
        "Explicar o ataque de extensão de comprimento e o porquê do HMAC",
        "Demonstrar por que modo ECB e IV fixo são inseguros",
        "Verificar assinatura e cadeia de certificado corretamente",
        "Avaliar token e separar garantia de declaração",
        "Escrever achado criptográfico com mecanismo verificável",
    ],
    "tools": ["openssl", "hashcat", "python3 (cryptography/hmac)", "jwt_tool", "Wireshark", "exiftool"],
    "equipment": "Somente software, livre, na máquina do operador.",
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Avaliar o uso criptográfico de uma aplicação própria, demonstrar ao menos um erro de uso e propor correção com mecanismo.",
        "scope_md": "Aplicação que o operador controla. Nenhum serviço de terceiro.",
        "resources_md": (
            "openssl, python3, jwt_tool, navegador para inspecionar cadeia. Liberado como "
            "software na trilha."
        ),
        "steps_md": (
            "1. Inventariar todo uso criptográfico.\n"
            "2. Escolher um erro de uso e reproduzi-lo.\n"
            "3. Registrar comportamento observado.\n"
            "4. Escrever achado com mecanismo, impacto e correção.\n"
            "5. Avaliar transporte (cadeia e nome).\n"
            "6. Declarar limitações."
        ),
        "success_criteria": [
            "Inventário com primitiva, modo, tamanho e gestão",
            "Erro de uso demonstrado com comportamento observado",
            "Achado com mecanismo verificável",
            "Cadeia TLS inspecionada e nome verificado",
            "Correção mínima justificada",
            "Limitações explícitas",
        ],
        "evidence": [
            "Tabela de inventário",
            "Registro da demonstração",
            "Achados",
            "Saída de inspeção de certificado",
            "Relatório final",
        ],
        "expected_result": "Avaliação criptográfica com demonstração de erro e correção fundamentada.",
        "grading_md": "Inventário 25%, demonstração 30%, escrita do achado 30%, limitações 15%.",
        "challenge_slug": "",
    },
}

emit("15-applied-crypto.json", path)