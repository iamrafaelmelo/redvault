#!/usr/bin/env python3
"""Generate content/learning_paths/16-osint.json (OSINT).

Esta é a área com menor base importada: três documentos cobrem metodologia
externa, GitHub dorks e WHOIS. Por isso a trilha se apoia especialmente nos três
documentos próprios (metodologia, superfície externa, pessoas e organizações).

A prática usa plataformas públicas dentro do escopo declarado e os labs de recon
da plataforma. Nenhum exercício autoriza tocar em alvo de terceiro.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

METH = "own-osint-metodologia"
SURF = "own-osint-superficie-externa"
PEOPLE = "own-osint-pessoas-organizacoes"
EXT = "ht-generic-methodologies-and-resources-external-recon-methodology"
GH = EXT + "-github-leaked-secrets"
TI = EXT + "-reconnaissance-and-threat-intelligenc"
WIDE = EXT + "-wide-source-code-search"
LEAKS = EXT + "-database-leaks"
WHOIS = "ht-network-services-pentesting-43-pentesting-whois"
DNS = "ht-network-services-pentesting-pentesting-dns"
SUB = "ht-network-services-pentesting-pentesting-web-uncovering-cloudflare"
BUCKET = "ht-network-services-pentesting-pentesting-web-buckets"
WEB = "ht-network-services-pentesting-pentesting-web"
ACAD_RECON = "recon"

m0 = mod(
    "metodo-e-limites",
    "Método e limites",
    "Definir pergunta, escopo e registro antes de coletar qualquer coisa.",
    ["pergunta", "escopo", "fonte", "verificação", "registro"],
    [
        unit(
            "pergunta-e-escopo",
            "Pergunta e escopo",
            "Saber o que se pretende responder e o que está fora do exercício.",
            ["pergunta formulável", "escopo autorizado", "dado sensível"],
            [
                act("osi-m0-u1-own-meth", "theory", "OSINT: da pergunta ao registro",
                    kb=METH, minutes=60),
                act("osi-m0-u1-academy", "theory", "Reconhecimento: método",
                    academy=ACAD_RECON, minutes=40),
                act("osi-m0-u1-kb-ext", "theory", "Metodologia de reconhecimento externo",
                    kb=EXT, minutes=45),
                act("osi-m0-u1-ex-escopo", "exercises",
                    "Exercício: transformar um pedido vago em pergunta e escopo",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Nenhuma coleta nesta etapa.\n\n"
                        "Receba o pedido: *'preciso saber tudo sobre a empresa X'*.\n\n"
                        "1. Reescreva em **três** perguntas que possam ser respondidas com "
                        "dado público.\n"
                        "2. Para cada uma, defina o escopo (domínio, organização, janela de "
                        "tempo).\n"
                        "3. Liste o que fica **fora** de escopo e por quê.\n\n"
                        "Entregue as perguntas, o escopo e a lista de exclusão. A lista de "
                        "exclusão é a parte que protege a coleta de virar assédio."
                    )),
            ],
        ),
        unit(
            "registro-e-verificacao",
            "Registro e verificação",
            "Produzir tabela citável com confiança por linha.",
            ["tabela de registro", "fonte primária", "independência", "confiança"],
            [
                act("osi-m0-u2-ex-tabela", "exercises",
                    "Exercício: montar a tabela de registro com confiança",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Escolha uma organização pública (não pessoa) e uma pergunta do "
                        "exercício anterior.\n\n"
                        "1. Colete **cinco** afirmações com fonte.\n"
                        "2. Preencha: pergunta, afirmação, fonte, data de consulta, trecho, "
                        "confiança.\n"
                        "3. Marque quais afirmações têm **segunda fonte independente**.\n\n"
                        "Entregue a tabela. Afirmação com fonte republicada não conta como "
                        "segunda fonte — é a mesma fonte duas vezes."
                    )),
                act("osi-m0-u2-ex-limites", "exercises",
                    "Exercício: decidir quando parar",
                    minutes=40,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Leia os quatro sinais de que a coleta cruzou o limite (no artigo de "
                        "metodologia) e responda, para um cenário que você invente:\n\n"
                        "1. Em que ponto a coleta deveria ter parado?\n"
                        "2. Que dado coletado **não serve** para a conclusão?\n"
                        "3. O que você faria se encontrasse credencial real?\n\n"
                        "Entregue as três respostas. A terceira é a mais importante: usar "
                        "credencial encontrada transforma exercício em crime."
                    )),
            ],
        ),
    ],
    summary="Pergunta, escopo, fonte, verificação e o limite que não se negocia.",
    completion="Perguntas formuladas, tabela de registro preenchida e decisão de parada registrada.",
)

m1 = mod(
    "superficie-tecnica",
    "Superfície técnica",
    "Mapear domínio, DNS, certificado e serviço exposto com fonte por afirmação.",
    ["certificate transparency", "DNS", "WHOIS", "buscador de serviços", "bucket"],
    [
        unit(
            "dominio-e-dns",
            "Domínio e DNS",
            "Descobrir nomes e endereços sem tocar no alvo.",
            ["registro de domínio", "registros DNS", "subdomínio", "provedor"],
            [
                act("osi-m1-u1-own-surf", "theory", "Superfície externa: certificate transparency, Shodan e limites",
                    kb=SURF, minutes=60),
                act("osi-m1-u1-kb-whois", "theory", "43 — Pentesting WHOIS",
                    kb=WHOIS, minutes=35),
                act("osi-m1-u1-kb-dns", "theory", "53 — Pentesting DNS",
                    kb=DNS, minutes=45),
                act("osi-m1-u1-ex-ct", "exercises",
                    "Exercício: inventariar nomes por transparência de certificação",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Escolha um domínio que você administra ou um "
                        "domínio público de organização com site institucional — coleta passiva.\n\n"
                        "1. Consulte o log de transparência de certificação para o domínio.\n"
                        "2. Deduplicate os nomes de host obtidos.\n"
                        "3. Classifique: institucional, API, ambiente de teste, "
                        "provedor de terceiro, ruído (wildcard).\n"
                        "4. Para três nomes, registre o que mais você precisaria para afirmar "
                        "que há serviço ativo.\n\n"
                        "Entregue a tabela. Nome no log é nome pedido, não serviço funcionando."
                    )),
            ],
        ),
        unit(
            "servico-e-recurso",
            "Serviço e recurso exposto",
            "Ler buscador de serviços e recurso de armazenamento com a limitação correta.",
            ["Shodan", "banner", "data de observação", "bucket", "CDN"],
            [
                act("osi-m1-u2-ex-buscador", "exercises",
                    "Exercício: interpretar resultado de buscador de serviços",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Não escaneie nada.\n\n"
                        "1. Escolha um endereço que você controla (ou um provedor público "
                        "documentado).\n"
                        "2. Consulte o buscador de serviços e registre: porta, banner, "
                        "data da última observação.\n"
                        "3. Compare com o que você **sabe** do seu host.\n\n"
                        "Responda: quantas diferenças há entre o índice e a realidade? O "
                        "que isso diz sobre usar esse índice como prova?"
                    )),
                act("osi-m1-u2-kb-bucket", "theory", "Buckets",
                    kb=BUCKET, minutes=40),
                act("osi-m1-u2-kb-web", "theory", "80, 443 — Metodologia de pentesting web",
                    kb=WEB, minutes=45),
                act("osi-m1-u2-kb-cloudflare", "theory", "Uncovering CloudFlare",
                    kb=SUB, minutes=40),
                act("osi-m1-u2-ex-origem", "exercises",
                    "Exercício: descrever como identificar origem atrás de CDN",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Análise documental.\n\n"
                        "1. Descreva três sinais que sugerem que um domínio está atrás de "
                        "provedor de borda (CDN).\n"
                        "2. Descreva duas evidências que **confirmariam** um endereço de origem.\n"
                        "3. Explique por que 'o IP do registro DNS' não é necessariamente a "
                        "origem.\n\n"
                        "Entregue as listas. Achar origem exige evidência independente; "
                        "inferir pelo registro DNS é o erro mais comum."
                    )),
            ],
        ),
    ],
    summary="Nomes por certificado, DNS, registro e serviço exposto — com data e limite por afirmação.",
    prereq="metodo-e-limites",
    completion="Inventário de nomes por certificado e leitura crítica de buscador de serviços.",
)

m2 = mod(
    "vazamento-e-codigo",
    "Vazamento e código público",
    "Encontrar exposição acidental em repositório e base pública — e não usar o que encontra.",
    ["GitHub dork", "busca ampla", "vazamento de banco", "credencial", "notificação"],
    [
        unit(
            "repositorio",
            "Repositório",
            "Localizar segredo publicado e agir corretamente.",
            ["dork", "busca em histórico", "arquivo de configuração", "notificação"],
            [
                act("osi-m2-u1-kb-gh", "theory", "GitHub Dorks & Leaks",
                    kb=GH, minutes=50),
                act("osi-m2-u1-kb-wide", "theory", "Busca ampla em código-fonte público",
                    kb=WIDE, minutes=45),
                act("osi-m2-u1-ex-dork", "exercises",
                    "Exercício: procurar exposição acidental em repositório conhecido",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Restrinja-se a repositório de organização "
                        "pública e a busca **passiva**.\n\n"
                        "1. Monte três consultas que encontrariam arquivo de configuração "
                        "com credencial em repositório público.\n"
                        "2. Execute e registre cada resultado: repositório, arquivo, data.\n"
                        "3. Para cada resultado, classifique: **credencial ativa suspeita**, "
                        "**placeholder**, **exemplo/documentação**.\n\n"
                        "Se encontrar credencial que pareça ativa: **não use**. Documente e "
                        "notifique. Usar é acesso não autorizado."
                    )),
            ],
        ),
        unit(
            "vazamento-publico",
            "Vazamento público",
            "Avaliar vazamento publicado sem ampliar o dano.",
            ["base vazada", "verificação", "dado pessoal", "relatório"],
            [
                act("osi-m2-u1b-kb-leaks", "theory", "Leaks de bancos de dados",
                    kb=LEAKS, minutes=45),
                act("osi-m2-u1b-kb-ti", "theory", "Reconhecimento e APIs de inteligência de ameaças",
                    kb=TI, minutes=45),
                act("osi-m2-u2-ex-vazamento", "exercises",
                    "Exercício: descrever o procedimento para confirmar vazamento sem usá-lo",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Análise documental — nenhum dado real de pessoa.\n\n"
                        "1. Escreva o procedimento para confirmar que um conjunto de dados "
                        "publicado contém dado da organização alvo.\n"
                        "2. Defina o mínimo de dado que precisa ser lido.\n"
                        "3. Defina o que **não** se copia para o relatório.\n\n"
                        "Responda: por que a confirmação de vazamento é um exercício de "
                        "minimização, e não de coleta?"
                    )),
            ],
        ),
    ],
    summary="GitHub dork, busca ampla e vazamento: encontrar exposição sem usar credencial.",
    prereq="superficie-tecnica",
    completion="Consultas de dork classificadas e procedimento de vazamento escrito.",
)

m3 = mod(
    "pessoas-e-relatorio",
    "Pessoas e relatório",
    "Correlacionar identidade com evidência e publicar sem atribuir além da prova.",
    ["correlação", "homonímia", "metadata", "relatório", "atribuição"],
    [
        unit(
            "correlacao",
            "Correlação de identidade",
            "Sustentar vínculo com dois elementos independentes.",
            ["homonímia", "nome de usuário", "metadado", "documento"],
            [
                act("osi-m3-u1-own-people", "theory", "Pessoas e organizações: correlação e limite ético",
                    kb=PEOPLE, minutes=60),
                act("osi-m3-u1-ex-homonimo", "exercises",
                    "Exercício: descartar vínculo por homonímia",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Cenário fictício.\n\n"
                        "Você encontrou duas contas com o mesmo nome de usuário e uma com o "
                        "mesmo nome completo de um funcionário da organização alvo.\n\n"
                        "1. Liste o que cada coincidência **sustenta**.\n"
                        "2. Liste o que faltaria para afirmar vínculo.\n"
                        "3. Escreva a frase de relatório com confiança declarada.\n\n"
                        "Entregue as três listas. 'Mesmo nome de usuário' propõe hipótese; não "
                        "conclui."
                    )),
            ],
        ),
        unit(
            "relatorio",
            "Relatório",
            "Entregar tabela com fonte, data e confiança, e dizer o que não foi confirmado.",
            ["estrutura", "data de corte", "limitação", "confiança"],
            [
                act("osi-m3-u2-ex-relatorio", "exercises",
                    "Exercício: relatório de OSINT com data de corte",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Produza o relatório de uma investigação pequena:\n\n"
                        "1. Pergunta e escopo.\n"
                        "2. Tabela de afirmações com fonte, data e confiança.\n"
                        "3. Separação explícita: fato / inferência.\n"
                        "4. O que **não** foi possível confirmar.\n"
                        "5. Data de corte.\n\n"
                        "Se você escrever conclusão sem data de corte, o laudo não é "
                        "reproduzível — as fontes mudam."
                    )),
                act("osi-m3-u2-assess", "assessment", "Avaliação: OSINT",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "O que torna duas fontes independentes?",
                         "accepted": ["não é a mesma republicação", "origens diferentes"],
                         "explanation": "Duas páginas que copiam a mesma nota são uma fonte só."},
                        {"id": "q2", "prompt": "Um nome de host no log de certificado prova que há serviço ativo?",
                         "accepted": ["não", "nao", "não prova"],
                         "explanation": "O log registra pedido de certificado, não serviço em execução."},
                        {"id": "q3", "prompt": "Qual é o procedimento ao encontrar credencial real?",
                         "accepted": ["notificar e documentar, sem usar"],
                         "explanation": "Usar credencial encontrada é acesso não autorizado; o procedimento é documentar e notificar."},
                        {"id": "q4", "prompt": "Por que um laudo de OSINT precisa de data de corte?",
                         "accepted": ["as fontes mudam", "a internet é dinâmica"],
                         "explanation": "Sites mudam e conteúdo é excluído; a data de corte define quando a conclusão valia."},
                    ]),
                act("osi-m3-u2-project", "project",
                    "Capstone: investigação OSINT de superfície com limites declarados",
                    minutes=160,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "Escolha **uma** superfície pública que você pode analisar "
                        "(idealmente a do seu próprio domínio ou de organização com "
                        "política pública de análise).\n\n"
                        "Entregue:\n\n"
                        "1. Perguntas e escopo, com lista de exclusão.\n"
                        "2. Inventário por transparência de certificação, DNS e registro.\n"
                        "3. Leitura de buscador de serviços com data de observação.\n"
                        "4. Consultas de repositório público e classificação de resultado.\n"
                        "5. Tabela de afirmações com fonte, data e confiança.\n"
                        "6. O que não foi confirmado.\n"
                        "7. Prova de que nenhuma credencial encontrada foi usada.\n\n"
                        "Recusa: afirmação sem fonte, fonte republicada contada como "
                        "independente, ou uso de credencial encontrada."
                    )),
            ],
        ),
    ],
    summary="Homonímia, metadado e o relatório com data de corte e confiança declarada.",
    prereq="vazamento-e-codigo",
    completion="Análise de homonímia, relatório com data de corte e avaliação aprovada.",
)

path = {
    "slug": "osint",
    "title": "OSINT",
    "codename": "OSI",
    "domain": "osint",
    "summary": "Da pergunta ao laudo: certificado, DNS, serviço exposto, código público e correlação de identidade — sempre com fonte, data e limite.",
    "description": (
        "OSINT é a área com menor material importado nesta base, e a trilha se apoia "
        "nos três documentos próprios de metodologia, superfície e pessoas. O eixo não "
        "é ferramenta: é o registro com fonte, data e confiança, a distinção entre fato "
        "e inferência, e o limite de escopo que separa investigação de assédio. Nenhum "
        "exercício autoriza tocar em alvo de terceiro, e credencial encontrada nunca é "
        "usada."
    ),
    "entry_level": "Internet, linha de comando e leitura de registro público",
    "exit_level": "capaz de investigar superfície pública e emitir relatório com fonte e confiança",
    "estimated_hours": 26,
    "priority": 84,
    "phase": 3,
    "icon": "radar",
    "accent": "blue",
    "prerequisites": [],
    "competencies": [
        "Formular pergunta e escopo antes de coletar",
        "Montar tabela de registro com fonte, data e confiança",
        "Inventariar nomes por transparência de certificação",
        "Ler resultado de buscador de serviços pelo limite de cobertura",
        "Classificar exposição em repositório público e agir sem usar credencial",
        "Avaliar vínculo de identidade com dois elementos independentes",
        "Emitir relatório com data de corte e o que não foi confirmado",
    ],
    "tools": ["bbot", "theHarvester", "recon-ng", "Sherlock", "crt.sh", "Shodan", "dig", "whois"],
    "equipment": "Somente software: coleta passiva em fonte pública, na máquina do operador. Não é necessária conta paga.",
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Conduzir uma investigação de superfície pública com fonte por afirmação, confiança declarada e limites éticos explícitos.",
        "scope_md": (
            "Domínio ou organização com política pública de análise; preferencialmente a "
            "superfície do próprio operador. Coleta passiva apenas."
        ),
        "resources_md": (
            "Navegador, terminal, crt.sh, consultas DNS, buscador de serviços gratuito, "
            "consultas de repositório público. Nenhuma ferramenta paga."
        ),
        "steps_md": (
            "1. Definir pergunta, escopo e lista de exclusão.\n"
            "2. Inventariar nomes por transparência de certificação e DNS.\n"
            "3. Ler resultado de buscador de serviços com data.\n"
            "4. Consultar repositório público e classificar resultados.\n"
            "5. Preencher tabela de afirmações.\n"
            "6. Declarar o que não foi confirmado e a data de corte."
        ),
        "success_criteria": [
            "Perguntas formuláveis e lista de exclusão",
            "Cada afirmação com fonte, data e trecho",
            "Confiança declarada por linha",
            "Resultado de buscador com data de observação",
            "Nenhuma credencial usada; procedimento documentado",
            "Seção do que não foi confirmado e data de corte",
        ],
        "evidence": [
            "Documento de escopo",
            "Inventário de nomes",
            "Consultas e resultados classificados",
            "Tabela de afirmações",
            "Relatório final",
        ],
        "expected_result": "Relatório de OSINT com fonte citável e limites declarados.",
        "grading_md": "Método e escopo 25%, qualidade das fontes 30%, distinção fato/inferência 25%, limites 20%.",
        "challenge_slug": "",
    },
}

emit("16-osint.json", path)