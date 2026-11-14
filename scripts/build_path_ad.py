#!/usr/bin/env python3
"""Generate content/learning_paths/05-active-directory.json (Active Directory Pentesting).

Honesty note, enforced by this file: the platform has **no Windows domain
targets**. Every practical step here is therefore an exercise that declares,
in its own text, exactly what the operator needs — a self-owned lab (Windows
Server + a workstation) or software they can read and reason about without
transmitting anything. Nothing is presented as a REDVAULT lab that does not
exist.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import act, default_equipment, mod, unit  # noqa: E402

AD = "ht-windows-hardening-active-directory-methodology-"
WIN = "ht-windows-hardening-"

NO_DOMAIN_LAB = (
    "A plataforma REDVAULT não possui alvo de domínio Windows. Este exercício exige "
    "um laboratório próprio (mínimo: um controlador de domínio em VM e uma estação "
    "ingressada), ou pode ser entregue como análise sobre a documentação e sobre a "
    "saída de exemplo. Nunca execute contra domínio de terceiros."
)

m0 = mod(
    "fundamentos-ad",
    "Fundamentos de Active Directory",
    "Entender objetos, autenticação Kerberos e o modelo de permissão do AD antes de abusar dele.",
    ["domínio", "floresta", "LDAP", "Kerberos", "SID", "descritores de segurança", "GPO"],
    [
        unit(
            "estrutura",
            "Estrutura, objetos e resolução de nomes",
            "Ler um domínio como um conjunto de objetos com permissões, não como uma lista de usuários.",
            ["forest", "domain", "OU", "DN", "GPO", "DNS"],
            [
                act("ad-m0-u1-kb-methodology", "theory", "Metodologia de Active Directory (documento completo)",
                    kb=AD.rstrip("-"), minutes=150),
                act("ad-m0-u1-kb-dns", "theory", "Registros DNS do AD",
                    kb=AD + "ad-dns-records", minutes=25),
                act("ad-m0-u1-kb-sd", "theory", "Descritores de segurança",
                    kb=AD + "security-descriptors", minutes=30),
                act("ad-m0-u1-kb-ldap", "theory", "LDAP — consulta a diretório",
                    kb="ht-network-services-pentesting-pentesting-ldap", minutes=40),
                act("ad-m0-u1-ex-objetos", "exercises", "Exercício: modelar o domínio",
                    equipment="required", minutes=45,
                    body_md=(
                        NO_DOMAIN_LAB + "\n\n"
                        "No seu domínio de laboratório, produza um mapa com:\n\n"
                        "1. Nome do domínio, nome NetBIOS e floresta; domínios filhos.\n"
                        "2. As três OUs principais e quantos objetos cada uma contém.\n"
                        "3. O DN do domínio no formato `DC=...,DC=...` e uma consulta LDAP que "
                        "liste usuários com `pwdLastSet` antigo.\n"
                        "4. Os registros DNS `_ldap._tcp.dc._msdcs` e `_kerberos._tcp` e o "
                        "que cada um localiza.\n"
                        "5. As GPOs aplicadas a uma OU e como confirmar a precedência.\n\n"
                        "Entregável: mapa em texto com os comandos usados."
                    )),
            ],
        ),
        unit(
            "kerberos",
            "Kerberos e o que cada ticket permite",
            "Explicar TGT, TGS, PAC e delegação com precisão suficiente para prever o efeito de um abuso.",
            ["TGT", "TGS", "PAC", "krbtgt", "SPN", "AS-REQ", "delegação"],
            [
                act("ad-m0-u1-kb-kerb", "theory", "Autenticação Kerberos",
                    kb=AD + "kerberos-authentication", minutes=30),
                act("ad-m0-u1-kb-groups", "theory", "Grupos privilegiados e privilégios de token",
                    kb=AD + "privileged-groups-and-token-privileges", minutes=45),
                act("ad-m0-u1-kb-laps", "theory", "LAPS — senhas locais gerenciadas",
                    kb=AD + "laps", minutes=30),
                act("ad-m0-u1-kb-ldap-sign", "theory", "LDAP signing e channel binding",
                    kb=AD + "ldap-signing-and-channel-binding", minutes=25),
                act("ad-m0-u1-assess", "assessment", "Avaliação: Kerberos sem decoreba",
                    minutes=25,
                    equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Qual ticket é obtido na fase de autenticação e permite pedir outros tickets? (sigla)",
                         "accepted": ["tgt", "ticket granting ticket"]},
                        {"id": "q2", "prompt": "Qual conta protege o hash que forja Golden Tickets?",
                         "accepted": ["krbtgt"]},
                        {"id": "q3", "prompt": "Que campo do ticket indica o grupo do usuário e pode ser falsificado num Silver Ticket?",
                         "accepted": ["pac", "privilege attribute certificate"]},
                        {"id": "q4", "prompt": "Sem qual atributo a conta fica vulnerável a Kerberoasting? (sigla)",
                         "accepted": ["spn", "serviceprincipalname"]},
                    ]),
            ],
        ),
    ],
    summary="AD não é uma lista de usuários: é um grafo de objetos com ACLs e um protocolo de tickets.",
    completion="Mapa do domínio entregue e avaliação ≥ 70%.",
    minutes=420,
)

m1 = mod(
    "enumeracao-ad",
    "Enumeração do domínio",
    "Coletar caminhos de ataque com evidência, sem se afogar em ruído.",
    ["PowerView", "BloodHound", "ADWS", "kerberoast", "AS-REP", "password spraying"],
    [
        unit(
            "coleta",
            "Coleta e correlação",
            "Transformar consultas de diretório em um grafo de privilégio.",
            ["LDAP", "ADWS", "BloodHound", "SharpHound", "ACL"],
            [
                act("ad-m1-u1-kb-enum", "theory", "Enumeração via ADWS",
                    kb=AD + "adws-enumeration", minutes=30),
                act("ad-m1-u1-kb-bloodhound", "theory", "BloodHound",
                    kb=AD + "bloodhound", minutes=30),
                act("ad-m1-u1-kb-printers", "theory", "Informações do AD em impressoras",
                    kb=AD + "ad-information-in-printers", minutes=25),
                act("ad-m1-u1-kb-spray", "theory", "Password spraying",
                    kb=AD + "password-spraying", minutes=30),
                act("ad-m1-u1-kb-kerb", "theory", "Kerberoasting",
                    kb=AD + "kerberoast", minutes=35),
                act("ad-m1-u1-kb-asrep", "theory", "AS-REP Roasting",
                    kb=AD + "asreproast", minutes=25),
                act("ad-m1-u1-ex-grafo", "exercises", "Exercício: do inventário ao grafo",
                    equipment="required", minutes=75,
                    body_md=(
                        NO_DOMAIN_LAB + "\n\n"
                        "1. Colete usuários, computadores, grupos e ACLs relevantes com "
                        "PowerView (equivalente ao que está no documento de enumeração).\n"
                        "2. Importe os dados no BloodHound e liste **cinco** caminhos até "
                        "Domain Admin, ordenados por número de saltos.\n"
                        "3. Para cada caminho, cite o mecanismo exato (GenericAll, "
                        "WriteDACL, ForceChangePassword, AddMember...).\n"
                        "4. Marque quais caminhos dependem de uma ACL que um usuário comum "
                        "consiga escrever.\n\n"
                        "Entregável: lista de caminhos com evidência da ACL de origem."
                    )),
            ],
        ),
        unit(
            "credenciais-por-ticket",
            "De credencial fraca a ticket utilizável",
            "Sair de um usuário comum e chegar a material utilizável de outro.",
            ["kerberoast", "AS-REP", "hashcat", "ticket", "delegação"],
            [
                act("ad-m1-u2-kb-unconstrained", "theory", "Delegação irrestrita",
                    kb=AD + "unconstrained-delegation", minutes=30),
                act("ad-m1-u2-kb-constrained", "theory", "Delegação restrita",
                    kb=AD + "constrained-delegation", minutes=30),
                act("ad-m1-u2-kb-rbcd", "theory", "Resource-Based Constrained Delegation",
                    kb=AD + "resource-based-constrained-delegation", minutes=45),
                act("ad-m1-u2-kb-pth", "theory", "Pass the Hash e Pass the Key",
                    kb=AD + "over-pass-the-hash-pass-the-key", minutes=25),
                act("ad-m1-u2-kb-ptt", "theory", "Pass the Ticket",
                    kb=AD + "pass-the-ticket", minutes=20),
                act("ad-m1-u2-kb-saw", "theory", "Roubo de credenciais NTLM",
                    kb=WIN + "ntlm-places-to-steal-ntlm-creds", minutes=20),
                act("ad-m1-u2-kb-ntlm", "theory", "Autenticação NTLM (modelo)",
                    kb=WIN + "ntlm", minutes=30),
                act("ad-m1-u2-ex-kerberoast", "exercises", "Exercício: quebrar um TGS",
                    equipment="required", minutes=60,
                    body_md=(
                        NO_DOMAIN_LAB + "\n\n"
                        "1. Peça um TGS para uma conta com SPN e salve a saída.\n"
                        "2. Converta para o formato aceito pelo hashcat e explique o modo "
                        "escolhido (o tipo do hash depende da versão do RC4/AES do domínio).\n"
                        "3. Quebre com wordlist própria e registre tempo e taxa.\n"
                        "4. Explique por que senha de serviço longa e aleatória muda o "
                        "resultado, e o que recomendaria ao dono do domínio.\n\n"
                        "Entregável: passo a passo com os comandos e o tempo de quebra."
                    )),
            ],
        ),
    ],
    summary="Enumeração só vale quando vira caminho ordenado com evidência de ACL.",
    completion="Cinco caminhos documentados e exercício de quebra entregue.",
    requires="fundamentos-ad",
    minutes=600,
)

m2 = mod(
    "escalada-ad",
    "ACLs, AES e servidores",
    "Abusar do que o AD considera permissão: descritores, fila de certificados e serviços internos.",
    ["ACL abuse", "Shadow Credentials", "AD CS", "ESC", "MSSQL", "spooler", "Lansweeper"],
    [
        unit(
            "acl-e-certificados",
            "Descritores e AD CS",
            "Explorar permissões escritas e a PKI do domínio, que é o caminho de escalada mais comum em domínio real.",
            ["WriteDACL", "GenericAll", "Shadow Credentials", "ESC1..ESC8", "certipy"],
            [
                act("ad-m2-u1-kb-acl", "theory", "Abuso de ACL e persistência",
                    kb=AD + "acl-persistence-abuse", minutes=60),
                act("ad-m2-u1-kb-badsucc", "theory", "BadSuccessor",
                    kb=AD + "acl-persistence-abuse-badsuccessor", minutes=25),
                act("ad-m2-u1-kb-shadow", "theory", "Shadow Credentials",
                    kb=AD + "acl-persistence-abuse-shadow-credentials", minutes=20),
                act("ad-m2-u1-kb-dmsa", "theory", "Migração para dMSA e abuso",
                    kb=AD + "badsuccessor-dmsa-migration-abuse", minutes=25),
                act("ad-m2-u1-kb-gdmsa", "theory", "Golden dMSA / gMSA",
                    kb=AD + "golden-dmsa-gmsa", minutes=30),
                act("ad-m2-u1-kb-certs", "theory", "Certificados do AD — visão geral",
                    kb=AD + "ad-certificates", minutes=35),
                act("ad-m2-u1-kb-certs2", "theory", "Certificados do AD — parte 2",
                    kb=AD + "ad-certificates-2", minutes=25),
                act("ad-m2-u1-kb-esc", "theory", "Escalada de domínio via certificados",
                    kb=AD + "ad-certificates-domain-escalation", minutes=90),
                act("ad-m2-u1-kb-certtheft", "theory", "Roubo de certificado",
                    kb=AD + "ad-certificates-certificate-theft", minutes=25),
                act("ad-m2-u1-ex-esc", "exercises", "Exercício: classificar a configuração de CA",
                    equipment="required", minutes=70,
                    body_md=(
                        NO_DOMAIN_LAB + "\n\n"
                        "Sem explorar nada, faça o **inventário** da PKI do seu laboratório:\n\n"
                        "1. Liste as CAs publicadas na floresta e os templates publicados.\n"
                        "2. Para cada template, registre: direito de inscrição, "
                        "`EnrolleeSuppliesSubject`, uso de EKU de autenticação de cliente, "
                        "requer aprovação, e se permite exportação da chave.\n"
                        "3. Classifique cada template encontrado segundo as condições de "
                        "escalada descritas no documento de escalada (ESC1 a ESC8), citando "
                        "a condição exata que bate.\n"
                        "4. Escreva a correção para cada um.\n\n"
                        "Entregável: tabela de templates com classificação e correção. "
                        "O exercício é de auditoria; exploração fica fora do escopo."
                    )),
                act("ad-m2-u1-assess", "assessment", "Avaliação: ACL e certificados",
                    minutes=25,
                    equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Qual direito permite reescrever a ACL de um objeto e portanto obter qualquer permissão depois? (sigla em inglês)",
                         "accepted": ["writedacl", "write_dac", "writedac"]},
                        {"id": "q2", "prompt": "Qual técnica usa a chave `msDS-KeyCredentialLink` para autenticar como outro usuário?",
                         "accepted": ["shadow credentials", "shadow credential", "shadowcredentials"]},
                        {"id": "q3", "prompt": "Que condição de template permite pedir um certificado com o nome de outro usuário? (nome do atributo)",
                         "accepted": ["enrolleesuppliessubject", "supplies_subject", "suppliessubject"]},
                    ]),
            ],
        ),
        unit(
            "servicos",
            "Serviços internos como caminho de domínio",
            "Enxergar MSSQL, spooler e ferramentas de inventário como superfície de domínio.",
            ["MSSQL", "PrintNightmare", "spooler", "Lansweeper", "SCCM"],
            [
                act("ad-m2-u2-kb-mssql", "theory", "Abuso de MSSQL no AD",
                    kb=AD + "abusing-ad-mssql", minutes=40),
                act("ad-m2-u2-kb-print", "theory", "Abuso do spooler de impressão",
                    kb=AD + "printers-spooler-service-abuse", minutes=35),
                act("ad-m2-u2-kb-pn", "theory", "PrintNightmare",
                    kb=AD + "printnightmare", minutes=30),
                act("ad-m2-u2-kb-lansweeper", "theory", "Lansweeper — segurança",
                    kb=AD + "lansweeper-security", minutes=30),
                act("ad-m2-u2-kb-sccm", "theory", "SCCM — management point e segredos de política",
                    kb=AD + "sccm-management-point-relay-sql-policy-secrets", minutes=25),
                act("ad-m2-u2-kb-doublehop", "theory", "O problema do double hop em Kerberos",
                    kb=AD + "kerberos-double-hop-problem", minutes=25),
                act("ad-m2-u2-kb-rdp", "theory", "Abuso de sessões RDP",
                    kb=AD + "rdp-sessions-abuse", minutes=25),
            ],
        ),
    ],
    summary="Em domínio real, a escalada quase sempre passa por uma ACL mal escrita ou por um template de certificado.",
    completion="Inventário de PKI classificado e avaliação ≥ 70%.",
    requires="enumeracao-ad",
    minutes=600,
)

m3 = mod(
    "dominio-e-deteccao",
    "Domínio comprometido: persistência, florestas e detecção",
    "Chegar a Domain Admin, manter acesso, cruzar fronteira de floresta e provar que cada passo é detectável.",
    ["DCSync", "Golden Ticket", "Silver Ticket", "SID History", "Shadow Credentials", "detecção", "limpeza"],
    [
        unit(
            "persistencia-ad",
            "Persistência no domínio",
            "Manter acesso de forma que o próprio AD registre, e saber remover.",
            ["krbtgt", "Golden Ticket", "Silver Ticket", "Skeleton Key", "DCShadow", "DSRM", "SID History"],
            [
                act("ad-m3-u1-kb-dcsync", "theory", "DCSync",
                    kb=AD + "dcsync", minutes=25),
                act("ad-m3-u1-kb-golden", "theory", "Golden Ticket",
                    kb=AD + "golden-ticket", minutes=25),
                act("ad-m3-u1-kb-silver", "theory", "Silver Ticket",
                    kb=AD + "silver-ticket", minutes=30),
                act("ad-m3-u1-kb-diamond", "theory", "Diamond Ticket",
                    kb=AD + "diamond-ticket", minutes=30),
                act("ad-m3-u1-kb-skeleton", "theory", "Skeleton Key",
                    kb=AD + "skeleton-key", minutes=20),
                act("ad-m3-u1-kb-dcshadow", "theory", "DCShadow",
                    kb=AD + "dcshadow", minutes=25),
                act("ad-m3-u1-kb-dsrm", "theory", "Credenciais de DSRM",
                    kb=AD + "dsrm-credentials", minutes=20),
                act("ad-m3-u1-kb-sidhist", "theory", "Injeção de SID History",
                    kb=AD + "sid-history-injection", minutes=25),
                act("ad-m3-u1-kb-customssp", "theory", "Custom SSP",
                    kb=AD + "custom-ssp", minutes=20),
                act("ad-m3-u1-kb-dyn", "theory", "Objetos dinâmicos e anti-forense",
                    kb=AD + "ad-dynamic-objects-anti-forensics", minutes=25),
                act("ad-m3-u1-kb-timeroast", "theory", "Timeroasting",
                    kb=AD + "timeroasting", minutes=20),
                act("ad-m3-u1-kb-certpersist", "theory", "Persistência por certificado de conta",
                    kb=AD + "ad-certificates-account-persistence", minutes=30),
                act("ad-m3-u1-kb-certdompersist", "theory", "Persistência de domínio via certificados",
                    kb=AD + "ad-certificates-domain-persistence", minutes=30),
            ],
        ),
        unit(
            "florestas-e-deteccao",
            "Fronteiras de floresta e visão do defensor",
            "Cruzar domínio e floresta com confiança explícita, e fechar com detecção e limpeza.",
            ["trust", "SID filtering", "domain trust", "Event ID", "limpeza"],
            [
                act("ad-m3-u2-kb-outbound", "theory", "Domínio de floresta externa — confiança de saída",
                    kb=AD + "external-forest-domain-one-way-outbound", minutes=30),
                act("ad-m3-u2-kb-inbound", "theory", "Domínio de floresta externa — confiança de entrada",
                    kb=AD + "external-forest-domain-oneway-inbound", minutes=30),
                act("ad-m3-u2-kb-lateral", "theory", "Movimentação lateral no Windows (visão geral)",
                    kb=WIN + "lateral-movement", minutes=20),
                act("ad-m3-u2-project", "project", "Relatório de domínio comprometido (capstone)",
                    equipment="software", minutes=120,
                    body_md=(
                        "Entregue o relatório técnico do **capstone** desta trilha, a partir "
                        "do laboratório de domínio que você montou (ou, se não montou, a partir "
                        "dos caminhos enumerados no módulo 2 e das saídas de exemplo que você "
                        "produziu em cada exercício).\n\n"
                        "Estrutura obrigatória:\n\n"
                        "1. **Escopo**: domínio, floresta, domínios filhos, e o que ficou fora.\n"
                        "2. **Caminho**: da conta inicial até Domain Admin, com cada passo e o "
                        "artefato que o comprova (ACL, template, ticket, log).\n"
                        "3. **Persistência implementada** e como você a removeu, com a "
                        "verificação que falha depois da remoção.\n"
                        "4. **Detecção**: para cada achado, o Event ID ou a telemetria que o "
                        "revela, e a regra que você proporia.\n"
                        "5. **Risco residual**: o que continua possível mesmo depois das "
                        "correções propostas.\n\n"
                        "Critério de aceite: cada afirmação do relatório ou tem evidência "
                        "citada, ou está marcada explicitamente como hipótese."
                    )),
                act("ad-m3-u2-ex-deteccao", "exercises", "Exercício: mapa de detecção",
                    equipment="software", minutes=60,
                    body_md=(
                        "Sem executar nada, monte um mapa de detecção a partir da "
                        "documentação que você leu nesta trilha:\n\n"
                        "| Técnica | Artefato gerado no AD | Log/Event ID | Regra proposta |\n"
                        "|---|---|---|---|\n\n"
                        "Cubra no mínimo: DCSync, Golden Ticket, Shadow Credentials, "
                        "inscrição em template vulnerável, criação de objeto dinâmico, e "
                        "alteração de `msDS-KeyCredentialLink`.\n\n"
                        "Este exercício roda **só com software**: a entrega é a tabela e a "
                        "justificativa de cada regra, não um teste em domínio."
                    )),
                act("ad-m3-u2-assess", "assessment", "Avaliação: persistência e fronteiras",
                    minutes=25,
                    equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Qual operação do protocolo de replicação o DCSync imita? (nome)",
                         "accepted": ["dsgetncchanges", "drsgetncchanges", "replicacao", "replicação"]},
                        {"id": "q2", "prompt": "Que conta/atributo um Golden Ticket exige como segredo?",
                         "accepted": ["krbtgt"]},
                        {"id": "q3", "prompt": "O Silver Ticket é válido contra qual componente?",
                         "accepted": ["servico", "serviço", "service", "servidor", "aplicacao", "aplicação"]},
                        {"id": "q4", "prompt": "Qual mecanismo impede que um SID de outra floresta seja aceito numa confiança?",
                         "accepted": ["sid filtering", "filtragem de sid", "sid filter"]},
                    ]),
            ],
        ),
    ],
    summary="Comprometer domínio é fácil de provar e difícil de justificar; o relatório com detecção é o produto real.",
    completion="Relatório do capstone entregue e avaliação ≥ 70%.",
    requires="escalada-ad",
    minutes=600,
)

path = default_equipment({
    "slug": "active-directory-pentesting",
    "title": "Active Directory Pentesting",
    "codename": "AD",
    "domain": "windows",
    "summary": "Objetos, Kerberos, ACLs e PKI: como um domínio Windows decide confiança e como isso é abusado até Domain Admin.",
    "description": (
        "A trilha parte da estrutura do domínio e de Kerberos, passa pela enumeração que "
        "transforma consultas em grafo de privilégio, e chega aos dois caminhos que dominam "
        "domínio real: descritores de segurança mal escritos e templates de certificado. "
        "O último módulo trata persistência, fronteiras de floresta e o que cada técnica deixa "
        "de rastro. Todo trabalho prático é feito em laboratório próprio: a plataforma não tem "
        "alvos de domínio Windows, e isso está declarado em cada exercício."
    ),
    "entry_level": "confortável com Windows e PowerShell; trilha Windows Security concluída",
    "exit_level": "capaz de enumerar, escalar, persistir e documentar um domínio com visão de detecção",
    "estimated_hours": 38,
    "priority": 45,
    "phase": 2,
    "icon": "route",
    "accent": "blue",
    "prerequisites": ["windows-security"],
    "competencies": [
        "Explicar TGT, TGS, PAC e delegação",
        "Enumerar um domínio e ordenar caminhos até Domain Admin",
        "Classificar templates de certificado e ACLs por risco",
        "Executar e remover persistência de domínio",
        "Propor detecção para cada técnica usada",
    ],
    "tools": ["PowerView", "BloodHound/SharpHound", "Certipy", "Rubeus", "Impacket", "hashcat", "LDAP queries", "RSAT"],
    "equipment": (
        "Somente software na leitura e nos exercícios de análise; os exercícios de laboratório "
        "exigem VM própria de Windows Server (controlador de domínio) e uma estação ingressada. "
        "A plataforma REDVAULT não fornece alvo de domínio."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Comprometer um domínio de laboratório próprio e entregar relatório com caminho, persistência removida e detecção.",
        "scope_md": (
            "Domínio de laboratório montado pelo operador (controlador de domínio + ao menos uma "
            "estação). Escopo alternativo aceito: análise documentada sobre os caminhos enumerados "
            "e as saídas produzidas nos exercícios, sem execução contra alvo."
        ),
        "resources_md": (
            "VMs próprias com Windows Server (avaliação) e Windows 10/11, BloodHound, PowerView, "
            "Rubeus, Impacket, Certipy, hashcat. Nenhum recurso pago é necessário. A plataforma "
            "não fornece domínio."
        ),
        "steps_md": (
            "1. Mapear domínio, floresta e fronteiras de confiança.\n"
            "2. Enumerar e ordenar caminhos até Domain Admin com evidência.\n"
            "3. Executar a cadeia e registrar cada artefato.\n"
            "4. Implementar uma persistência, verificar e remover.\n"
            "5. Para cada achado, escrever a regra de detecção correspondente.\n"
            "6. Listar risco residual."
        ),
        "success_criteria": [
            "Domain Admin obtido no laboratório, ou cadeia completa justificada com evidência de ACL/template",
            "Cada passo reproduzível com comando e saída",
            "Persistência removida e remoção comprovada",
            "Regra de detecção para cada técnica usada",
            "Risco residual explícito",
        ],
        "evidence": [
            "Saída de enumeração (LDAP, PowerView, BloodHound)",
            "Tabela de ACLs e de templates com classificação",
            "Comandos e saídas do caminho até Domain Admin",
            "Antes/depois da remoção de persistência",
            "Mapa de detecção preenchido",
        ],
        "expected_result": "Domínio de laboratório comprometido com caminho, limpeza e detecção documentados.",
        "grading_md": (
            "Precisão técnica 30%, evidência 25%, detecção 25%, limpeza e risco residual 20%."
        ),
        "challenge_slug": "",
    },
})

out = ROOT / "content" / "learning_paths" / "05-active-directory.json"
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")