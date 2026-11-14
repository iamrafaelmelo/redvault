#!/usr/bin/env python3
"""Generate content/learning_paths/04-windows-security.json (Windows Security & PrivEsc)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import act, mod, unit  # noqa: E402

KB = "ht-windows-hardening-"

m0 = mod(
    "fundamentos-windows",
    "Fundamentos de Windows para segurança",
    "Entender identidade, token, ACL e registro como o Windows realmente decide permissão.",
    ["arquitetura", "tokens", "integridade", "NTFS", "registro", "PowerShell", "CMD"],
    [
        unit(
            "identidade-e-acesso",
            "Identidade, token e integridade",
            "Explicar por que o token do processo, não o nome do usuário, define o que é possível.",
            ["SID", "token", "integridade", "UAC"],
            [
                act("win-m0-u1-own-ntfs", "theory", "NTFS na prática de pentest",
                    kb="own-ntfs-para-pentest", minutes=30),
                act("win-m0-u1-kb-tokens", "theory", "Tokens de acesso",
                    kb=KB + "windows-local-privilege-escalation-access-tokens", minutes=25),
                act("win-m0-u1-kb-integrity", "theory", "Níveis de integridade",
                    kb=KB + "windows-local-privilege-escalation-integrity-levels", minutes=20),
                act("win-m0-u1-kb-uac", "theory", "UAC — Controle de Conta de Usuário",
                    kb=KB + "authentication-credentials-uac-and-efs-uac-user-account-control", minutes=35),
                act("win-m0-u1-kb-ctrl", "theory", "Controles de segurança do Windows",
                    kb=KB + "authentication-credentials-uac-and-efs", minutes=25),
                act("win-m0-u1-ex-token", "exercises", "Exercício: ler um token",
                    body_md=(
                        "Num Windows que você controla, execute e registre:\n\n"
                        "1. `whoami /all` — liste SIDs, grupos, privilégios e nível de integridade.\n"
                        "2. `whoami /priv` antes e depois de abrir um prompt elevado. Explique cada privilégio.\n"
                        "3. Crie um arquivo e dê `icacls arquivo /grant Usuario:(WDAC)`; explique por que\n"
                        "   isso é equivalente a Full Control na prática.\n"
                        "4. Crie um arquivo com fluxo alternativo e mostre que o Explorer não o exibe.\n"
                        "   (`dir /r` mostra.)\n\n"
                        "Escreva em cada item qual estrutura do Windows está sendo manipulada."
                    ), minutes=45),
            ],
        ),
        unit(
            "shell-e-enumeracao",
            "CMD e PowerShell para operação",
            "Enumeração legível e reprodutível em shell nativa.",
            ["cmd", "powershell", ".NET", "PowerView"],
            [
                act("win-m0-u2-kb-cmd", "theory", "CMD básico para pentesters",
                    kb=KB + "basic-cmd-for-pentesters", minutes=25),
                act("win-m0-u2-kb-ps", "theory", "PowerShell básico para pentesters",
                    kb=KB + "basic-powershell-for-pentesters", minutes=25),
                act("win-m0-u2-kb-dotnet", "theory", "Enumeração do Windows com .NET",
                    kb=KB + "basic-powershell-for-pentesters-dotnet-enumeration", minutes=15),
                act("win-m0-u2-kb-powerview", "theory", "PowerView/SharpView",
                    kb=KB + "basic-powershell-for-pentesters-powerview", minutes=25),
                act("win-m0-u2-assess", "assessment", "Avaliação: token e integridade",
                    minutes=20,
                    questions=[
                        {"id": "q1", "prompt": "Qual privilégio permite a um processo ler a memória de outro?",
                         "accepted": ["sedebugprivilege", "sedebug"]},
                        {"id": "q2", "prompt": "Um processo de média integridade pode escrever em `C:\\Windows\\System32`? Sim ou não.",
                         "accepted": ["nao", "não", "no"]},
                        {"id": "q3", "prompt": "Qual verbo do PowerShell lista privilégios do usuário atual? (whoami /priv em PS)",
                         "accepted": ["whoami /all", "whoami", "get-acl", "gettoken"]},
                    ]),
            ],
        ),
    ],
    summary="Token, integridade e ACL são o alicerce; sem eles o restante é memorização.",
    completion="Exercício entregue e avaliação ≥ 70%.",
)

m1 = mod(
    "enumeracao-windows",
    "Enumeração de Windows",
    "Procurar privilégio fora do usuário em serviços, tarefas, ACLs e credenciais.",
    ["serviços", "tarefas agendadas", "ACLs", "autoruns", "credenciais", "WinPEAS/Seatbelt"],
    [
        unit(
            "superficie",
            "Serviços, tarefas e caminhos",
            "Enumerar quem executa o quê, de onde e com qual permissão de escrita.",
            ["sc qc", "schtasks", "icacls", "autoruns", "unquoted service path"],
            [
                act("win-m1-u1-kb-checklist", "theory", "Checklist de escalada local no Windows",
                    kb=KB + "checklist-windows-privilege-escalation", minutes=20),
                act("win-m1-u1-kb-privesc", "theory", "Escalonamento de privilégios local no Windows (documento completo)",
                    kb=KB + "windows-local-privilege-escalation", minutes=120),
                act("win-m1-u1-kb-acl", "theory", "ACLs — DACLs/SACLs/ACEs",
                    kb=KB + "windows-local-privilege-escalation-acls-dacls-sacls-aces", minutes=25),
                act("win-m1-u1-kb-patt", "theory", "Windows — Privilege Escalation (PayloadsAllTheThings)",
                    kb="patt-methodology-and-resources-windows-privilege-escalation", minutes=40),
                act("win-m1-u1-kb-autoruns", "theory", "Escalação com Autoruns",
                    kb=KB + "windows-local-privilege-escalation-privilege-escalation-with-autorun-binaries", minutes=25),
                act("win-m1-u1-kb-updaters", "theory", "Atualizadores corporativos e IPC privilegiado",
                    kb=KB + "windows-local-privilege-escalation-abusing-auto-updaters-and-ipc", minutes=40),
                act("win-m1-u1-ex-svc", "exercises", "Exercício: inventário de serviços",
                    body_md=(
                        "Num Windows de laboratório, produza uma tabela com:\n\n"
                        "- todo serviço cujo binário está em diretório gravável por `Users` ou `Everyone`;\n"
                        "- todo serviço com caminho não entre aspas contendo espaço;\n"
                        "- toda tarefa agendada que executa script em caminho gravável;\n"
                        "- toda ACL com `(M)`, `(F)`, `(WDAC)` ou `(WO)` para grupos amplos.\n\n"
                        "Comandos base: `sc qc`, `Get-CimInstance Win32_Service`, `schtasks /query /fo LIST /v`,\n"
                        "`icacls` recursivo, Autoruns. Justifique a priorização de cada linha."
                    ), minutes=60),
            ],
        ),
        unit(
            "credenciais",
            "Credenciais e memória",
            "Saber onde o Windows guarda segredo e o que protege cada local.",
            ["LSASS", "DPAPI", "SAM", "credenciais salvas", "proteções"],
            [
                act("win-m1-u2-kb-steal", "theory", "Roubo de credenciais do Windows",
                    kb=KB + "stealing-credentials", minutes=40),
                act("win-m1-u2-kb-mimikatz", "theory", "Mimikatz",
                    kb=KB + "stealing-credentials-credentials-mimikatz", minutes=20),
                act("win-m1-u2-kb-prot", "theory", "Proteções de credenciais",
                    kb=KB + "stealing-credentials-credentials-protections", minutes=25),
                act("win-m1-u2-kb-dpapi", "theory", "DPAPI — extraindo senhas",
                    kb=KB + "windows-local-privilege-escalation-dpapi-extracting-passwords", minutes=30),
                act("win-m1-u2-kb-ntlm", "theory", "Onde roubar credenciais NTLM",
                    kb=KB + "ntlm-places-to-steal-ntlm-creds", minutes=20),
            ],
        ),
    ],
    summary="Enumeração de Windows é leitura de configuração: caminho, ACL e identidade de execução.",
    completion="Inventário priorizado entregue.",
    requires="fundamentos-windows",
    minutes=420,
)

m2 = mod(
    "escalada-windows",
    "Escalada de privilégios no Windows",
    "Escalar de usuário comum a SYSTEM/Administrator por configuração errada.",
    ["DLL hijacking", "unquoted service path", "SeImpersonate", "AlwaysInstallElevated", "COM hijacking", "registro"],
    [
        unit(
            "caminhos",
            "Caminhos e carregamento",
            "Explorar o que o sistema carrega de diretórios graváveis.",
            ["DLL hijacking", "unquoted service path", "writable PATH", "COM hijacking", "hives"],
            [
                act("win-m2-u1-kb-dll", "theory", "DLL Hijacking",
                    kb=KB + "windows-local-privilege-escalation-dll-hijacking", minutes=60),
                act("win-m2-u1-kb-sideload", "theory", "Side-loading avançado de DLL",
                    kb=KB + "windows-local-privilege-escalation-dll-hijacking-advanced-html-staged-dll-sideload", minutes=20),
                act("win-m2-u1-kb-syspath", "theory", "Writable System PATH + DLL Hijacking",
                    kb=KB + "windows-local-privilege-escalation-dll-hijacking-writable-sys-path-dll-hijacking-p", minutes=20),
                act("win-m2-u1-kb-com", "theory", "COM Hijacking",
                    kb=KB + "windows-local-privilege-escalation-com-hijacking", minutes=25),
                act("win-m2-u1-kb-hives", "theory", "Primitivas de exploração de hives do registro",
                    kb=KB + "windows-local-privilege-escalation-windows-registry-hive-exploitation", minutes=20),
                act("win-m2-u1-kb-append", "theory", "AppendData/AddSubdirectory sobre o registro de serviço",
                    kb=KB + "windows-local-privilege-escalation-appenddata-addsubdirectory-permission-over-serv", minutes=20),
            ],
        ),
        unit(
            "tokens-e-impersonacao",
            "Tokens, impersonação e integridade",
            "Usar privilégios concedidos e mecanismos de impersonação.",
            ["SeImpersonate", "SeDebug", "named pipes", "batch logon", "leaked handles"],
            [
                act("win-m2-u2-kb-abuse", "theory", "Abusando de tokens",
                    kb=KB + "windows-local-privilege-escalation-privilege-escalation-abusing-tokens", minutes=30),
                act("win-m2-u2-kb-seimp", "theory", "SeImpersonate de High para System",
                    kb=KB + "windows-local-privilege-escalation-seimpersonate-from-high-to-system", minutes=20),
                act("win-m2-u2-kb-sedebug", "theory", "SeDebug + SeImpersonate — copy token",
                    kb=KB + "windows-local-privilege-escalation-sedebug-seimpersonate-copy-token", minutes=20),
                act("win-m2-u2-kb-pipes", "theory", "De High Integrity para SYSTEM com name pipes",
                    kb=KB + "windows-local-privilege-escalation-from-high-integrity-to-system-with-name-pipes", minutes=20),
                act("win-m2-u2-kb-pipeimp", "theory", "Impersonação de cliente em named pipe",
                    kb=KB + "windows-local-privilege-escalation-named-pipe-client-impersonation", minutes=25),
                act("win-m2-u2-kb-handle", "theory", "Exploração de handles vazados",
                    kb=KB + "windows-local-privilege-escalation-leaked-handle-exploitation", minutes=30),
                act("win-m2-u2-kb-triggers", "theory", "Service triggers",
                    kb=KB + "windows-local-privilege-escalation-service-triggers", minutes=20),
                act("win-m2-u2-kb-potato", "theory", "RoguePotato, PrintSpoofer, GodPotato",
                    kb=KB + "windows-local-privilege-escalation-roguepotato-and-printspoofer", minutes=20),
                act("win-m2-u2-kb-juicy", "theory", "JuicyPotato",
                    kb=KB + "windows-local-privilege-escalation-juicypotato", minutes=15),
                act("win-m2-u2-kb-semvol", "theory", "SeManageVolumePrivilege",
                    kb=KB + "windows-local-privilege-escalation-semanagevolume-perform-volume-maintenance-tasks", minutes=15),
                act("win-m2-u2-ex-impersonate", "exercises", "Exercício: cadeia de impersonação",
                    body_md=(
                        "Num Windows de laboratório com `SeImpersonatePrivilege` disponível para um serviço,\n"
                        "escreva a cadeia completa **antes** de executar:\n\n"
                        "1. Qual primitivo de impersonação o privilégio concede?\n"
                        "2. Quem precisa conectar, e por qual interface?\n"
                        "3. Qual condição de corrida ou nome de pipe é explorada?\n"
                        "4. O que muda se o serviço também tiver `SeDebugPrivilege`?\n\n"
                        "Só depois execute a prova de conceito em ambiente próprio. Evidência obrigatória:\n"
                        "privilégios antes, saída de `whoami /priv` após, e explicação de cada elo."
                    ), minutes=75),
            ],
        ),
        unit(
            "misconfig",
            "Instaladores, tarefas e políticas",
            "Cobrir as configurações clássicas que aparecem em auditoria.",
            ["AlwaysInstallElevated", "unattended", "scheduled task ACL", "UIAccess", "RegPwn"],
            [
                act("win-m2-u3-kb-msi", "theory", "Criando um MSI com custom action",
                    kb=KB + "windows-local-privilege-escalation-create-msi-with-wix", minutes=20),
                act("win-m2-u3-kb-msiwrap", "theory", "MSI Wrapper",
                    kb=KB + "windows-local-privilege-escalation-msi-wrapper", minutes=15),
                act("win-m2-u3-kb-uiaccess", "theory", "Bypasses via UIAccess",
                    kb=KB + "windows-local-privilege-escalation-uiaccess-admin-protection-bypass", minutes=20),
                act("win-m2-u3-kb-secdesk", "theory", "Secure Desktop Accessibility registry propagation",
                    kb=KB + "windows-local-privilege-escalation-secure-desktop-accessibility-registry-propagati", minutes=15),
                act("win-m2-u3-kb-proto", "theory", "Abuso de Windows Protocol Handler / ShellExecute",
                    kb=KB + "protocol-handler-shell-execute-abuse", minutes=15),
                act("win-m2-u3-assess", "assessment", "Avaliação: qual configuração explora o quê",
                    minutes=25,
                    questions=[
                        {"id": "q1", "prompt": "Qual chave de registro habilita AlwaysInstallElevated? (nome da política)",
                         "accepted": ["alwaysinstallelevated"]},
                        {"id": "q2", "prompt": "Um serviço roda `C:\\Program Files\\Meu App\\svc.exe` sem aspas e `C:\\Program.exe` é gravável. Qual classe de falha?",
                         "accepted": ["unquoted service path", "unquoted", "caminho sem aspas", "sem aspas"]},
                        {"id": "q3", "prompt": "Qual privilégio é o pré-requisito clássico da família Potato?",
                         "accepted": ["seimpersonateprivilege", "seimpersonate"]},
                    ]),
            ],
        ),
    ],
    summary="Cada caminho de escalada é uma pergunta específica sobre quem carrega o quê de onde.",
    completion="Duas cadeias de escalada comprovadas e avaliação ≥ 70%.",
    requires="enumeracao-windows",
    minutes=540,
)

m3 = mod(
    "defesa-e-pos-exploracao",
    "PowerShell, defesa e pós-exploração",
    "Operar com LOLBAS, entender detecção e conduzir pós-exploração com limpeza documentada.",
    ["LOLBAS", "AMSI", "logging", "AppLocker", "persistência", "limpeza"],
    [
        unit(
            "lolbas-e-powershell",
            "Living off the land",
            "Usar binários assinados e entender o que a detecção enxerga.",
            ["certutil", "rundll32", "mshta", "AMSI", "script block logging"],
            [
                act("win-m3-u1-own-lolbas", "theory", "LOLBAS: binários nativos do Windows",
                    kb="own-lolbas-metodologia", minutes=25),
                act("win-m3-u1-kb-harden", "theory", "Controles de segurança do Windows (parte 2)",
                    kb=KB + "authentication-credentials-uac-and-efs-2", minutes=25),
                act("win-m3-u1-kb-av", "theory", "Contorno de AV",
                    kb=KB + "av-bypass", minutes=90),
                act("win-m3-u1-kb-c2", "theory", "Cobalt Strike (visão geral)",
                    kb=KB + "cobalt-strike", minutes=30),
                act("win-m3-u1-ex-lolbas", "exercises", "Exercício: função, detecção e política",
                    body_md=(
                        "Escolha **três** binários do LOLBAS com funções diferentes (Executar, Baixar,\n"
                        "UAC Bypass). Para cada um entregue:\n\n"
                        "1. A linha de comando exata e o efeito.\n"
                        "2. O Event ID ou telemetria que registra o comportamento.\n"
                        "3. Uma regra de detecção (nome + argumento anômalo).\n"
                        "4. Se a política AppLocker/WDAC padrão de `C:\\Windows` bloqueia ou não — e por quê.\n\n"
                        "O exercício é de defesa: a entrega principal é a regra de detecção."
                    ), minutes=60),
            ],
        ),
        unit(
            "pos-exploracao",
            "Pós-exploração e movimento",
            "Manter acesso e mover lateralmente com rastro controlado.",
            ["persistência", "PsExec", "WinRM", "WMI", "DCOM", "limpeza"],
            [
                act("win-m3-u2-kb-lateral", "theory", "Movimentação lateral (visão geral)",
                    kb=KB + "lateral-movement", minutes=15),
                act("win-m3-u2-kb-psexec", "theory", "Execução remota (PsExec, WinExec, SMBExec)",
                    kb=KB + "lateral-movement-psexec-and-winexec", minutes=20),
                act("win-m3-u2-kb-winrm", "theory", "WinRM",
                    kb=KB + "lateral-movement-winrm", minutes=20),
                act("win-m3-u2-kb-wmi", "theory", "WmiExec",
                    kb=KB + "lateral-movement-wmiexec", minutes=15),
                act("win-m3-u2-kb-dcom", "theory", "DCOM Exec",
                    kb=KB + "lateral-movement-dcomexec", minutes=20),
                act("win-m3-u2-kb-atexec", "theory", "AtExec / SchtasksExec",
                    kb=KB + "lateral-movement-atexec", minutes=15),
                act("win-m3-u2-kb-rdp", "theory", "Abuso de sessões RDP",
                    kb=KB + "active-directory-methodology-rdp-sessions-abuse", minutes=20),
                act("win-m3-u2-kb-vsix", "theory", "Abuso de extensões VSIX e VSCode",
                    kb=KB + "visual-studio-vsix-extension-abuse", minutes=15),
                act("win-m3-u2-project", "project", "Relatório de privesc e detecção do capstone",
                    minutes=90,
                    body_md=(
                        "Produza o relatório técnico do **capstone** desta trilha.\n\n"
                        "Estrutura obrigatória:\n\n"
                        "1. Identidade inicial: `whoami /all`, integridade e privilégios.\n"
                        "2. Superfície: serviços, tarefas, caminhos graváveis, ACLs relevantes.\n"
                        "3. Cadeia de escalada: cada elo com comando e saída.\n"
                        "4. Persistência criada/removida e como a verificação comprova a remoção.\n"
                        "5. Detecção: por achado, Event ID ou telemetria e a regra proposta.\n\n"
                        "Critério de aceite: cada achado reproduzível e detectável a partir do relatório."
                    )),
                act("win-m3-u2-ex-persist", "exercises", "Exercício: persistência e remoção",
                    body_md=(
                        "Num Windows descartável, implemente **duas** persistências de usuário\n"
                        "(por exemplo, chave `Run` em HKCU e tarefa agendada de usuário).\n\n"
                        "Para cada uma: artefato, caminho/chave, verificação, remoção, e o evento\n"
                        "que um analista usaria para encontrá-la (`Microsoft-Windows-Security-Auditing`,\n"
                        "TaskScheduler/Operational, Sysmon).\n\n"
                        "Reverta tudo e comprove que a verificação falha depois da remoção."
                    ), minutes=60),
            ],
        ),
    ],
    summary="Ofensiva sem entendimento de detecção vira ruído; defesa sem teste vira software.",
    completion="Exercícios de detecção e persistência entregues.",
    requires="escalada-windows",
)

path = {
    "slug": "windows-security",
    "title": "Windows Security & Privilege Escalation",
    "codename": "WIN",
    "domain": "windows",
    "summary": "Tokens, ACLs, serviços e carregamento de DLL: como o Windows decide permissão e como isso é abusado.",
    "description": (
        "A trilha começa no modelo de identidade do Windows (token, integridade, NTFS, UAC), "
        "passa pela enumeração de serviços, tarefas, ACLs e credenciais, e chega às cadeias de "
        "escalada mais presentes em auditoria (DLL hijacking, unqualified service path, "
        "SeImpersonate, instaladores). A última parte conecta LOLBAS, PowerShell, logging e "
        "pós-exploração, incluindo remoção documentada de persistência."
    ),
    "entry_level": "usuário de Windows confortável com CMD e PowerShell",
    "exit_level": "capaz de enumerar, escalar e documentar privesc Windows com visão de detecção",
    "estimated_hours": 55,
    "priority": 40,
    "phase": 1,
    "icon": "window",
    "accent": "blue",
    "prerequisites": ["linux-security"],
    "competencies": [
        "Interpretar token, integridade e ACL",
        "Enumerar serviços, tarefas e caminhos graváveis",
        "Executar cadeias clássicas de escalada com evidência",
        "Usar LOLBAS e explicar a detecção correspondente",
        "Implementar e remover persistência de forma auditável",
    ],
    "tools": ["WinPEAS", "Seatbelt", "Sysinternals (Autoruns, Procmon, PsExec)", "LOLBAS", "PowerView", "icacls", "sc", "schtasks"],
    "equipment": "Somente software: VM Windows própria ou o host da plataforma, conforme os labs permitirem.",
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Comprometer uma máquina Windows multi-estágio e entregar relatório com detecção.",
        "scope_md": "A máquina `machine-saas-admin-console` na origem loopback atribuída pelo gerenciador de labs.",
        "resources_md": "REDVAULT, Windows/VM local para exercícios, WinPEAS, Sysinternals, LOLBAS. Sem recursos pagos.",
        "steps_md": (
            "1. Enumeração de identidade, serviços, tarefas e ACLs.\n"
            "2. Priorização em tabela com mecanismo e esforço.\n"
            "3. Escalada com evidência de cada passo.\n"
            "4. Pós-exploração: acesso mantido, rastro documentado e removido.\n"
            "5. Relatório com regra de detecção por achado."
        ),
        "success_criteria": [
            "Privilégio elevado obtido na máquina",
            "Cada elo da cadeia reproduzível com comando e saída",
            "Regra de detecção proposta para cada achado",
            "Artefatos de pós-exploração removidos e comprovados",
        ],
        "evidence": [
            "Saída de `whoami /all`, `sc qc`, `schtasks`, `icacls`",
            "Comando e saída de cada passo de escalada",
            "Tabela de achados com detecção e correção",
        ],
        "expected_result": "Host Windows comprometido com cadeia documentada e plano de detecção.",
        "grading_md": (
            "Precisão técnica 35%, evidência 25%, detecção proposta 25%, remoção comprovada 15%."
        ),
        "challenge_slug": "machine-saas-admin-console",
    },
}

out = ROOT / "content" / "learning_paths" / "04-windows-security.json"
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")