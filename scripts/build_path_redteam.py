#!/usr/bin/env python3
"""Generate content/learning_paths/17-red-team.json (Red Team).

A base tem material bom sobre phishing, evasão de IDS, infraestrutura ofensiva,
persistência e Cobalt Strike. Não há C2 nem infraestrutura de operação na
plataforma, e a trilha não simula que haja: a prática é planejamento, detecção e
exercício de laboratório com ferramentas que o operador instala.

Ponto de honestidade central: todo exercício de Red Team desta trilha tem alvo
definido pelo operador ou pela própria plataforma. Nada de alvo de terceiro.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

PHISH = "ht-generic-methodologies-and-resources-phishing-methodology"
PHISH_CLONE = PHISH + "-clone-a-website"
PHISH_DETECT = PHISH + "-detecting-phising"
PHISH_CLIP = PHISH + "-clipboard-hijacking"
PHISH_HOMO = PHISH + "-homograph-attacks"
IDS = "ht-generic-methodologies-and-resources-pentesting-network-ids-evasion"
INFRA = "ht-privacy-offensive-infrastructure-and-attribution-evasion"
CB = "patt-methodology-and-resources-cobalt-strike-cheatsheet"
CB_H = "ht-windows-hardening-cobalt-strike"
C2G = "ht-generic-methodologies-and-resources-github-issues-and-repository-files-c2"
ADAPTIX = "ht-generic-methodologies-and-resources-basic-forensic-methodology-adaptixc2-config-extraction-and-ttps"
WIN_PERSIST = "patt-methodology-and-resources-windows-persistence"
LIN_PERSIST = "patt-methodology-and-resources-linux-persistence"
LIN_EVAS = "patt-methodology-and-resources-linux-evasion"
MIMI = "patt-methodology-and-resources-windows-mimikatz"
MIMI_H = "ht-windows-hardening-stealing-credentials-credentials-mimikatz"
LOLBAS = "own-lolbas-metodologia"
MAL = "own-yara-regras-deteccao"

m0 = mod(
    "escopo-e-regras",
    "Escopo, regras de engajamento e ética",
    "Estabelecer o que pode ser feito, contra quem, e o que acontece se sair do combinado.",
    ["autorização", "regras de engajamento", "escopo", "registro"],
    [
        unit(
            "autorizacao",
            "Autorização e escopo",
            "Nenhuma operação começa sem documento.",
            ["autorização escrita", "janela", "alvo declarado", "ponto de contato"],
            [
                act("rt-m0-u1-ex-ro", "exercises",
                    "Exercício: escrever regras de engajamento",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Nenhuma ação técnica.\n\n"
                        "Escreva um documento de regras para um exercício de Red Team contra "
                        "**um laboratório seu** (suas VMs):\n\n"
                        "1. Alvos dentro do escopo e explicitamente fora.\n"
                        "2. Janela de execução.\n"
                        "3. Técnicas permitidas e proibidas.\n"
                        "4. Ponto de contato e procedimento de interrupção.\n"
                        "5. Como o resultado é protegido.\n\n"
                        "Regra do exercício: se você colocar 'rede doméstica' no escopo, o "
                        "documento está errado — a LAN compartilhada fica fora."
                    )),
                act("rt-m0-u1-ex-fronteira", "exercises",
                    "Exercício: reconhecer quando a operação saiu do escopo",
                    minutes=40,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Liste cinco situações em que continuar a operação seria uma violação, "
                        "mesmo que o alvo esteja no escopo:\n\n"
                        "1. Descoberta de dado de terceiro.\n"
                        "2. Serviço de outra organização compartilhando a infraestrutura.\n"
                        "3. Credencial de usuário real fora do escopo.\n"
                        "4. Efeito colateral em serviço em produção.\n"
                        "5. Qualquer uma que **você** acrescente.\n\n"
                        "Para cada uma, escreva a ação correta: parar, notificar ou registrar."
                    )),
            ],
        ),
    ],
    summary="Autorização, janela e ponto de parada. Sem isso, a técnica é crime.",
    completion="Regras de engajamento escritas com alvos internos e externos explícitos.",
)

m1 = mod(
    "infraestrutura-e-c2",
    "Infraestrutura de operação e C2",
    "Montar ambiente que separe a operação da rede pessoal e entender o que um C2 expõe.",
    ["infraestrutura", "redirecionador", "C2", "atribuição"],
    [
        unit(
            "infra",
            "Infraestrutura",
            "Separar identidade e rede do operador.",
            ["VPS dedicado", "redirector", "domínio", "atribuição"],
            [
                act("rt-m1-u1-kb-infra", "theory", "Infraestrutura ofensiva e evasão de atribuição",
                    kb=INFRA, minutes=50),
                act("rt-m1-u1-kb-cb", "theory", "Cobalt Strike",
                    kb=CB, minutes=45),
                act("rt-m1-u1-ex-infra", "exercises",
                    "Exercício: desenhar infraestrutura em três camadas",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Documento, sem provisionar.\n\n"
                        "1. Desenhe: domínio público, ponto de entrada (redirector) e servidor "
                        "de controle, para uma operação contra laboratório.\n"
                        "2. Para cada camada, diga o que ela protege.\n"
                        "3. Explique por que o servidor de controle **não** deve ser o mesmo "
                        "endereço usado pelo cliente final.\n"
                        "4. Diga como você apaga a infraestrutura ao final.\n\n"
                        "Entregue o diagrama e as respostas. A camada que se esquece de apagar "
                        "é a que fica registrada para sempre."
                    )),
            ],
        ),
        unit(
            "c2",
            "C2",
            "Entender o que o agente expõe e como a defesa o detecta.",
            ["beacon", "perfil", "confiança de TLS", "canal alternativo"],
            [
                act("rt-m1-u2-kb-cbh", "theory", "Cobalt Strike — visão de hardening",
                    kb=CB_H, minutes=40),
                act("rt-m1-u2-kb-c2g", "theory", "GitHub Issues e arquivos de repositório como canal C2",
                    kb=C2G, minutes=40),
                act("rt-m1-u2-kb-adaptix", "theory", "Extração de configuração e TTPs do AdaptixC2",
                    kb=ADAPTIX, minutes=45),
                act("rt-m1-u2-ex-detect", "exercises",
                    "Exercício: olhar o C2 pelo lado azul",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Para um agente de C2 que você **não** vai executar, liste os "
                        "indicadores que a rede deixaria:\n\n"
                        "1. Beacons em intervalo fixo — o que muda no tráfego?\n"
                        "2. Perfil de HTTP que imita navegador — que inconsistência aparece?\n"
                        "3. Certificado autoassinado ou de domínio recém-registrado.\n"
                        "4. Qualquer um que você considere mais forte que os três.\n\n"
                        "Entregue a lista com a consulta de detecção correspondente. Red Team "
                        "sem lado azul é exercício de imaginação."
                    )),
            ],
        ),
    ],
    summary="Infraestrutura em camadas, C2 e o que ele deixa visível para a defesa.",
    prereq="escopo-e-regras",
    completion="Diagrama de infraestrutura e lista de detecção de C2.",
)

m2 = mod(
    "execucao-e-persistencia",
    "Execução e persistência",
    "Usar o sistema como ele é — binário legítimo, persistência nativa — e medir deteção.",
    ["living off the land", "persistência", "credencial", "evasão"],
    [
        unit(
            "execucao",
            "Execução no sistema",
            "Reconhecer o uso de binário assinado como primeiro estágio.",
            ["LOLBAS", "PowerShell", "WMI", "fileless"],
            [
                act("rt-m2-u1-own-lolbas", "theory", "Living off the land: metodologia",
                    kb=LOLBAS, minutes=50),
                act("rt-m2-u1-kb-lin-evasion", "theory", "Linux — Evasion",
                    kb=LIN_EVAS, minutes=40),
                act("rt-m2-u1-kb-ids", "theory", "Técnicas de evasão de IDS/IPS",
                    kb=IDS, minutes=45),
                act("rt-m2-u1-ex-lolbas", "exercises",
                    "Exercício: catalogar capacidade de binário assinado no seu host",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Inventário, sem execução maliciosa.\n\n"
                        "1. Para cinco binários do sistema, descreva uma capacidade que eles "
                        "têm além do propósito (ex.: baixar, executar, escrever arquivo).\n"
                        "2. Para cada uma, escreva a consulta que detectaria o uso anômalo.\n"
                        "3. Escolha uma que pareça indetectável e explique por que não é.\n\n"
                        "Entregue a tabela. O valor está na coluna de detecção, não na de "
                        "capacidade."
                    )),
            ],
        ),
        unit(
            "persistencia-e-cred",
            "Persistência e credencial",
            "Conhecer os mecanismos e o rastro que cada um deixa.",
            ["registro", "serviço", "cron", "LSASS", "Mimikatz"],
            [
                act("rt-m2-u2-kb-winp", "theory", "Persistência no Windows",
                    kb=WIN_PERSIST, minutes=45),
                act("rt-m2-u2-kb-linp", "theory", "Persistência no Linux",
                    kb=LIN_PERSIST, minutes=45),
                act("rt-m2-u2-kb-mimi", "theory", "Mimikatz",
                    kb=MIMI, minutes=40),
                act("rt-m2-u2-kb-mimih", "theory", "Mimikatz — visão de hardening",
                    kb=MIMI_H, minutes=40),
                act("rt-m2-u2-ex-rastro", "exercises",
                    "Exercício: para cada persistência, o evento que a denuncia",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Preencha a tabela:\n\n"
                        "| Mecanismo | O que cria | Evento que denuncia | Fonte |\n"
                        "| --- | --- | --- | --- |\n\n"
                        "Cubra: chave de registro de execução, serviço, tarefa agendada, cron "
                        "e perfil de shell.\n\n"
                        "Entregue a tabela preenchida. Persistência sem evento de detecção "
                        "correspondente é técnica incompleta para exercício."
                    )),
            ],
        ),
    ],
    summary="LOLBAS, persistência, credencial e o rastro de cada técnica.",
    prereq="infraestrutura-e-c2",
    completion="Tabela de capacidade + detecção e tabela de persistência + evento.",
)

m3 = mod(
    "phishing-e-relatorio",
    "Phishing e relatório",
    "Avaliar engenharia social como risco de processo e entregar relatório que a organização usa.",
    ["phishing", "homógrafo", "clone", "detecção", "relatório"],
    [
        unit(
            "phishing",
            "Phishing",
            "Entender o que faz um e-mail passar — e o que a defesa faz para detectar.",
            ["clone", "homógrafo", "pastejacking", "notificação"],
            [
                act("rt-m3-u1-kb-phish", "theory", "Metodologia de phishing",
                    kb=PHISH, minutes=50),
                act("rt-m3-u1-kb-clone", "theory", "Clonando um website",
                    kb=PHISH_CLONE, minutes=40),
                act("rt-m3-u1-kb-homo", "theory", "Homograph e homoglyph em phishing",
                    kb=PHISH_HOMO, minutes=40),
                act("rt-m3-u1-kb-clip", "theory", "Clipboard hijacking",
                    kb=PHISH_CLIP, minutes=35),
                act("rt-m3-u1-kb-detect", "theory", "Detectando phishing",
                    kb=PHISH_DETECT, minutes=40),
                act("rt-m3-u1-ex-phish", "exercises",
                    "Exercício: campanha simulada dentro do próprio laboratório",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Destinatário: uma conta que você mesmo criou.\n\n"
                        "1. Monte uma mensagem simulada, com URL apontando para página local.\n"
                        "2. Liste os indicadores que permitem detectá-la (domínio novo, "
                        "homógrafo, urgência, botão com URL diferente).\n"
                        "3. Escreva a regra de e-mail ou de proxy que bloquearia a campanha.\n"
                        "4. Explique como você treinaria a pessoa a reconhecê-la.\n\n"
                        "Entregue os quatro itens. Campanha sem item 3 e 4 é apenas ataque."
                    )),
            ],
        ),
        unit(
            "relatorio",
            "Relatório",
            "Descrever a operação, os achados e o que a organização deve corrigir.",
            ["narrativa", "cobertura", "detecção", "correção"],
            [
                act("rt-m3-u2-kb-yara", "theory", "Escrever regra de detecção que não gera falso positivo",
                    kb=MAL, minutes=45),
                act("rt-m3-u2-ex-ro", "exercises",
                    "Exercício: relatório com cobertura e detecção",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Produza o relatório da operação de laboratório com:\n\n"
                        "1. Regras de engajamento aplicadas.\n"
                        "2. Linha do tempo da operação.\n"
                        "3. Técnicas usadas, com identificador de ATT&CK.\n"
                        "4. **O que a organização detectou** e o que não detectou.\n"
                        "5. Correções priorizadas.\n\n"
                        "O item 4 é o que distingue Red Team de pentest: o valor é o buraco "
                        "de detecção, não a lista de falhas exploradas."
                    )),
                act("rt-m3-u2-assess", "assessment", "Avaliação: Red Team",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "O que deve existir antes de qualquer execução técnica?",
                         "accepted": ["autorização escrita", "regras de engajamento"],
                         "explanation": "Sem autorização escrita e escopo, a operação é acesso não autorizado."},
                        {"id": "q2", "prompt": "Por que o servidor de C2 não deve ser o mesmo endereço que o cliente vê?",
                         "accepted": ["protege a infraestrutura de controle", "o redirecionador absorve a detecção"],
                         "explanation": "O ponto de entrada absorve detecção e bloqueio; o controle fica protegido atrás dele."},
                        {"id": "q3", "prompt": "Qual é o produto mais valioso de um exercício de Red Team?",
                         "accepted": ["o que a organização não detectou", "a lacuna de detecção"],
                         "explanation": "O valor está na medição da capacidade de detecção e resposta, não na lista de falhas."},
                        {"id": "q4", "prompt": "O que fazer se encontrar dado de pessoa fora do escopo?",
                         "accepted": ["parar e notificar", "registrar e não usar"],
                         "explanation": "Dado fora do escopo não se coleta nem se usa; documenta-se e notifica-se."},
                    ]),
                act("rt-m3-u2-project", "project",
                    "Capstone: operação de laboratório com medição de detecção",
                    minutes=180,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "Alvo: seu laboratório (VMs ou a própria plataforma RedVault). Nenhuma "
                        "rede ou sistema de terceiro.\n\n"
                        "Entregue:\n\n"
                        "1. Regras de engajamento assinadas por você.\n"
                        "2. Diagrama de infraestrutura em camadas.\n"
                        "3. Linha do tempo da operação com técnicas e horários.\n"
                        "4. Regra de detecção escrita para pelo menos uma técnica.\n"
                        "5. Tabela de cobertura: o que foi detectado e o que não foi.\n"
                        "6. Correções priorizadas.\n"
                        "7. Limitações.\n\n"
                        "Recusa: operação sem regras, alvo fora do laboratório, ou relatório "
                        "sem a coluna de detecção."
                    )),
            ],
        ),
    ],
    summary="Phishing, relatório e a medida que importa: o que a defesa viu.",
    prereq="execucao-e-persistencia",
    completion="Campanha simulada, relatório com cobertura e avaliação aprovada.",
)

path = {
    "slug": "red-team",
    "title": "Red Team",
    "codename": "RT",
    "domain": "redteam",
    "summary": "Escopo, infraestrutura, C2, execução com binário legítimo e phishing — medindo o que a defesa conseguiu detectar.",
    "description": (
        "A trilha trata Red Team como operação com regras, não como coleção de ataques. "
        "Cobre regras de engajamento, infraestrutura em camadas, C2 e o que ele deixa "
        "visível, execução com binário legítimo, persistência e phishing — sempre com o "
        "lado de detecção correspondente. O produto final é a tabela de cobertura: o que "
        "a defesa viu e o que não viu. Toda operação acontece em laboratório do próprio "
        "operador."
    ),
    "entry_level": "Linux e Windows, rede e exploração intermediária",
    "exit_level": "capaz de conduzir uma operação de laboratório e medir a cobertura de detecção",
    "estimated_hours": 36,
    "priority": 86,
    "phase": 3,
    "icon": "flame",
    "accent": "red",
    "prerequisites": ["active-directory-pentesting", "network-pentesting"],
    "competencies": [
        "Escrever regras de engajamento com escopo interno e externo",
        "Desenhar infraestrutura de operação em camadas",
        "Explicar o que um agente de C2 deixa visível",
        "Catalogar capacidade de binário assinado e sua detecção",
        "Mapear mecanismo de persistência ao evento que o denuncia",
        "Conduzir campanha simulada com indicadores e bloqueio",
        "Emitir relatório de cobertura de detecção",
    ],
    "tools": ["Sliver/Havoc/AdaptixC2 (opcional)", "Cobalt Strike (referência)", "Empire/PowerShell", "curl", "gophish (opcional)", "Sigma", "YARA"],
    "equipment": (
        "Somente software, com ressalva: infraestrutura de C2 e campanha de phishing "
        "exigem máquina própria ou VPS do operador. Nada disso é fornecido pela plataforma "
        "e nenhum exercício requer alvo externo."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Executar uma operação de Red Team em laboratório próprio e medir a cobertura de detecção, entregando relatório com correções.",
        "scope_md": (
            "Laboratório do próprio operador: VMs, a instância local da plataforma. Nenhum "
            "sistema ou rede de terceiro."
        ),
        "resources_md": (
            "Laboratório local, ferramentas de C2 (se quiser), host com telemetria (auditd/"
            "Sysmon), regras Sigma/YARA. Infraestrutura de VPS é opcional e de custo próprio."
        ),
        "steps_md": (
            "1. Escrever e assinar regras de engajamento.\n"
            "2. Desenhar infraestrutura em camadas.\n"
            "3. Executar as técnicas planejadas, registrando horário.\n"
            "4. Escrever regra de detecção para ao menos uma técnica.\n"
            "5. Medir o que foi detectado e o que não foi.\n"
            "6. Priorizar correções."
        ),
        "success_criteria": [
            "Regras de engajamento com escopo e ponto de parada",
            "Diagrama de infraestrutura com o que cada camada protege",
            "Linha do tempo com técnica e horário",
            "Regra de detecção escrita e validada",
            "Tabela de cobertura com detectado e não detectado",
            "Correções priorizadas",
        ],
        "evidence": [
            "Regras de engajamento",
            "Diagrama de infraestrutura",
            "Linha do tempo da operação",
            "Regra de detecção",
            "Tabela de cobertura",
            "Relatório final",
        ],
        "expected_result": "Relatório de operação de laboratório com medição de detecção.",
        "grading_md": "Escopo 20%, execução e registro 30%, medição de detecção 30%, correções 20%.",
        "challenge_slug": "",
    },
}

emit("17-red-team.json", path)