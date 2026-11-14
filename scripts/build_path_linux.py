#!/usr/bin/env python3
"""Generate content/learning_paths/03-linux-security.json (Linux Security & PrivEsc)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import act, mod, unit  # noqa: E402

KB = "ht-linux-hardening-"

m0 = mod(
    "fundamentos-linux",
    "Fundamentos de Linux para segurança",
    "Ler o modelo de processo, arquivo e permissão do Linux com precisão suficiente para prever o efeito de uma configuração errada.",
    ["filesystem", "permissões", "usuários e grupos", "processos", "descritores", "variáveis de ambiente"],
    [
        unit(
            "modelo",
            "Arquivos, permissões e identidade",
            "Explicar como o kernel decide se um processo pode ler, escrever ou executar um arquivo.",
            ["rwx e bits especiais", "uid/gid/euid", "ACL", "hard link e symlink"],
            [
                act("lx-m0-u1-kb-basics", "theory", "Fundamentos de Linux",
                    kb=KB + "linux-basics", minutes=20),
                act("lx-m0-u1-kb-files", "theory", "Arquivos interessantes e permissões",
                    kb=KB + "interesting-files-permissions", minutes=20),
                act("lx-m0-u1-kb-links", "theory", "Symlinks, hardlinks e descritores de arquivo",
                    kb=KB + "main-system-information-filesystem-links-and-file-descriptors", minutes=25),
                act("lx-m0-u1-kb-euid", "theory", "euid, ruid e o bit SUID",
                    kb=KB + "user-information-euid-ruid-suid", minutes=20),
                act("lx-m0-u1-ex-model", "exercises", "Exercício: provar o modelo de permissão",
                    body_md=(
                        "Num container ou VM que você controla, execute e registre a saída:\n\n"
                        "1. Crie dois usuários. Como o usuário A, crie `a.txt` modo `600`.\n"
                        "2. Tente ler como B. Registre o erro exato do kernel.\n"
                        "3. Adicione A ao grupo de B e repita com modo `640`.\n"
                        "4. Crie um binário mínimo, aplique `chmod 4755` e imprima `id` — explique por que\n"
                        "   o euid é `0` e o ruid não é.\n"
                        "5. Crie um hard link e um symlink para o mesmo arquivo, apague o original e\n"
                        "   explique por que um continua acessível e o outro não.\n\n"
                        "Escreva a explicação em 1 parágrafo por item, citando uid/euid e o bit testado."
                    ), minutes=45),
            ],
        ),
        unit(
            "processos",
            "Processos, serviços e ambiente",
            "Identificar quem executa o quê, com qual identidade e com qual ambiente.",
            ["ps e /proc", "systemd", "cron", "/etc/passwd e shadow", "env e PATH"],
            [
                act("lx-m0-u2-kb-env", "theory", "Variáveis de ambiente do Linux",
                    kb=KB + "linux-basics-linux-environment-variables", minutes=30),
                act("lx-m0-u2-kb-proc", "theory", "Enumeração de processos e caminhos de serviços",
                    kb=KB + "processes-crontab-systemd-dbus-process-enumeration-and-service-paths", minutes=35),
                act("lx-m0-u2-kb-cron", "theory", "Cron e timers do systemd",
                    kb=KB + "processes-crontab-systemd-dbus-cron-and-systemd-timers", minutes=35),
                act("lx-m0-u2-kb-users", "theory", "Usuários, sessões e artefatos de credenciais",
                    kb=KB + "user-information-user-and-session-triage", minutes=20),
                act("lx-m0-u2-assess", "assessment", "Avaliação: identidade efetiva",
                    minutes=20,
                    questions=[
                        {"id": "q1", "prompt": "Um arquivo `root:root` modo 4755 é executado por `alice`. Qual é o euid do processo?",
                         "accepted": ["0", "root", "zero"]},
                        {"id": "q2", "prompt": "Qual arquivo guarda os hashes de senha em sistemas Linux modernos?",
                         "accepted": ["/etc/shadow", "etc/shadow", "shadow"]},
                        {"id": "q3", "prompt": "Que seção da configuração de um timer systemd define o comando executado?",
                         "accepted": ["execstart", "exec start", "unit"]},
                    ]),
            ],
        ),
    ],
    summary="Sem dominar uid/euid, bits e PATH, todo achado de privesc vira chute.",
    completion="Exercício entregue e avaliação ≥ 70%.",
)

m1 = mod(
    "enumeracao",
    "Enumeração de Linux",
    "Produzir um inventário que responda 'onde há privilégio fora do meu usuário?'.",
    ["SUID/SGID", "capabilities", "sudoers", "cron gravável", "NFS", "grupos"],
    [
        unit(
            "manual",
            "Enumeração manual",
            "Executar a checklist na ordem que rende resultado, entendendo cada comando.",
            ["find", "getcap", "sudo -l", "id", "mount"],
            [
                act("lx-m1-u1-kb-checklist", "theory", "Checklist de escalada de privilégios no Linux",
                    kb=KB + "main-system-information-linux-privilege-escalation-checklist", minutes=20),
                act("lx-m1-u1-kb-suid", "theory", "SUID, SGID, ACLs e arquivos sensíveis",
                    kb=KB + "interesting-files-permissions-suid-sgid-and-acl-triage", minutes=35),
                act("lx-m1-u1-kb-caps", "theory", "Linux Capabilities (detalhado)",
                    kb=KB + "interesting-files-permissions-linux-capabilities", minutes=45),
                act("lx-m1-u1-kb-sudo", "theory", "Abuso de comandos do sudo",
                    kb=KB + "main-system-information-sudo-command-abuse", minutes=45),
                act("lx-m1-u1-kb-groups", "theory", "Grupos interessantes para privesc",
                    kb=KB + "user-information-interesting-groups-linux-pe", minutes=30),
                act("lx-m1-u1-kb-nfs", "theory", "NFS com no_root_squash",
                    kb=KB + "interesting-files-permissions-nfs-no-root-squash-misconfiguration-pe", minutes=20),
                act("lx-m1-u1-ex-enum", "exercises", "Exercício: inventário de privilégio",
                    body_md=(
                        "Rode a checklist num sistema de laboratório e produza uma tabela com:\n\n"
                        "- binário/arquivo/permissão encontrado;\n"
                        "- por que existe (qual pacote, `dpkg -S`, ou configuração);\n"
                        "- se gera privilégio e por qual mecanismo (SUID, capability, sudo, grupo);\n"
                        "- esforço estimado de exploração.\n\n"
                        "O objetivo não é explorar. É **priorizar** com evidência. Um `find` com SUID\n"
                        "não tem o mesmo valor de um `vim` com SUID: mostre que você sabe a diferença."
                    ), minutes=60),
            ],
        ),
        unit(
            "ferramentas",
            "Ferramentas de enumeração",
            "Usar LinPEAS, LinEnum e pspy sem virar dependente delas.",
            ["linpeas", "linenum", "pspy", "linux-exploit-suggester"],
            [
                act("lx-m1-u2-kb-privesc", "theory", "Escalada de privilégios no Linux (documento completo)",
                    kb=KB + "linux-basics-linux-privilege-escalation", minutes=90),
                act("lx-m1-u2-ex-linpeas", "exercises", "Exercício: ler a saída do LinPEAS como investigador",
                    body_md=(
                        "Execute `linpeas.sh` num alvo de laboratório e responda:\n\n"
                        "1. Liste os 5 achados que o LinPEAS marcou em vermelho. Para cada um, explique\n"
                        "   com suas palavras **por que** ele é um caminho de escalada.\n"
                        "2. Aponte dois falsos positivos que o LinPEAS destacou mas que não dão privilégio.\n"
                        "3. Rode `pspy64` por 5 minutos e registre qualquer processo que execute como\n"
                        "   root a partir de um caminho gravável por usuário comum.\n\n"
                        "Ferramentas de enumeração listam; o operador decide. Registre a decisão."
                    ), minutes=45),
            ],
        ),
    ],
    summary="Enumeração é a etapa que separa privesc real de tentativa aleatória de exploit de kernel.",
    completion="Inventário priorizado entregue e exercício de LinPEAS concluído.",
    requires="fundamentos-linux",
)

m2 = mod(
    "escalada-local",
    "Escalada de privilégios local",
    "Escalar para root em sistemas reais usando configuração errada, sem depender de CVE.",
    ["SUID abuse", "capabilities", "sudo", "cron", "PATH hijacking", "ld.so", "kernel"],
    [
        unit(
            "misconfiguracao",
            "Má configuração: o caminho mais comum",
            "Explorar cada classe de configuração errada e escrever a evidência.",
            ["gtfobins", "cap_setuid", "LD_PRELOAD", "PATH", "cron gravável"],
            [
                act("lx-m2-u1-kb-gtfobins", "theory", "GTFOBins: viver do sistema com binários legítimos",
                    kb="own-gtfobins-metodologia", minutes=25),
                act("lx-m2-u1-kb-ldso", "theory", "Exemplo de exploit de privesc via ld.so",
                    kb=KB + "interesting-files-permissions-ld-so-conf-example", minutes=25),
                act("lx-m2-u1-kb-suidsolib", "theory", "Bibliotecas compartilhadas e linker em SUID",
                    kb=KB + "interesting-files-permissions-suid-shared-library-and-linker-abuse", minutes=25),
                act("lx-m2-u1-kb-wildcards", "theory", "Truques com wildcards",
                    kb=KB + "interesting-files-permissions-wildcards-spare-tricks", minutes=30),
                act("lx-m2-u1-kb-lxd", "theory", "Grupo lxd/lxc e escalada de privilégios",
                    kb=KB + "user-information-interesting-groups-linux-pe-lxd-privilege-escalation", minutes=20),
                act("lx-m2-u1-ex-suid", "exercises", "Exercício: explorar um SUID e documentar",
                    body_md=(
                        "Escolha um binário encontrado no inventário do módulo anterior e:\n\n"
                        "1. Prove a versão e a origem do pacote (`dpkg -S`, `--version`).\n"
                        "2. Execute o primitivo do GTFOBins aplicável ao contexto (SUID, sudo ou capability).\n"
                        "3. Capture a saída de `id` antes e depois.\n"
                        "4. Proponha a correção: remover bit, remover capability, restringir sudoers.\n\n"
                        "Se o primitivo não funcionar, registre o motivo — versão, sem TTY, `secure_path`.\n"
                        "Falha documentada também é resultado válido."
                    ), minutes=60),
            ],
        ),
        unit(
            "kernel-e-servicos",
            "Kernel e serviços mal configurados",
            "Avaliar quando usar exploit de kernel e quando atacar configuração de serviço.",
            ["linux-exploit-suggester", "service races", "cron", "D-Bus", "PAM"],
            [
                act("lx-m2-u2-kb-kernel", "theory", "Avaliação de vulnerabilidades do kernel",
                    kb=KB + "main-system-information-kernel-vulnerability-assessment", minutes=25),
                act("lx-m2-u2-kb-kernelcve", "theory", "Material sobre kernel, LPE e CVEs",
                    kb=KB + "main-system-information-kernel-lpe-cves", minutes=20),
                act("lx-m2-u2-kb-modprobe", "theory", "Módulos do kernel e abuso do modprobe",
                    kb=KB + "main-system-information-kernel-modules-and-modprobe", minutes=25),
                act("lx-m2-u2-kb-dbus", "theory", "D-Bus: enumeração e privesc por injeção",
                    kb=KB + "processes-crontab-systemd-dbus-d-bus-enumeration-and-command-injection-privilege-esc", minutes=30),
                act("lx-m2-u2-kb-pam", "theory", "PAM — Pluggable Authentication Modules",
                    kb=KB + "software-information-pam-pluggable-authentication-modules", minutes=25),
                act("lx-m2-u2-kb-write", "theory", "Escrita arbitrária de arquivos como root",
                    kb=KB + "interesting-files-permissions-write-to-root", minutes=50),
                act("lx-m2-u2-ex-kernel", "exercises", "Exercício: decidir sobre exploit de kernel",
                    body_md=(
                        "Com `linux-exploit-suggester.sh` num alvo de laboratório:\n\n"
                        "1. Registre a versão do kernel (`uname -r`) e a distro.\n"
                        "2. Liste os candidatos sugeridos e, para cada um, o critério de aplicabilidade.\n"
                        "3. Descarte os que exigem pré-requisito ausente (config de compilação, módulo,\n"
                        "   namespace não permitido).\n"
                        "4. Justifique por escrito por que exploit de kernel é **última** opção:\n"
                        "   instabilidade, perda de evidência, detectabilidade.\n\n"
                        "A resposta correta costuma ser: nenhum. O exercício vale pela justificativa."
                    ), minutes=60),
                act("lx-m2-u2-assess", "assessment", "Avaliação: escolher a via de escalada",
                    minutes=25,
                    questions=[
                        {"id": "q1", "prompt": "Um binário tem `cap_setuid+ep`. Qual efeito direto isso permite?",
                         "accepted": ["setuid", "mudar uid", "trocar uid", "chamar setuid"]},
                        {"id": "q2", "prompt": "`sudo -l` mostra `(root) NOPASSWD: /usr/bin/tar`. Qual classe de falha é essa?",
                         "accepted": ["sudoers", "misconfiguracao", "má configuração", "gtfobins"]},
                        {"id": "q3", "prompt": "Por que um exploit de kernel é considerado última opção num pentest?",
                         "accepted": ["instabilidade", "crash", "risco", "reboot", "perda"]},
                    ]),
            ],
        ),
    ],
    summary="Má configuração primeiro. Kernel só quando não existe outra via — e com justificativa.",
    completion="Pelo menos dois caminhos de escalada explorados com evidência e avaliação ≥ 70%.",
    requires="enumeracao",
    minutes=420,
)

m3 = mod(
    "containers-e-docker",
    "Containers e Docker",
    "Entender isolamento de container como fronteira de segurança, não como garantia.",
    ["namespaces", "capabilities em container", "docker socket", "privileged", "runc", "seccomp", "AppArmor"],
    [
        unit(
            "isolamento",
            "O que um container isola",
            "Explicar o que um namespace, cgroup, seccomp e AppArmor impedem e o que não impedem.",
            ["namespaces", "cgroups", "seccomp", "AppArmor", "SELinux"],
            [
                act("lx-m3-u1-kb-containers", "theory", "Containers e Namespaces",
                    kb=KB + "containers-namespaces", minutes=20),
                act("lx-m3-u1-kb-sec", "theory", "Segurança de Containers",
                    kb=KB + "containers-namespaces-container-security", minutes=40),
                act("lx-m3-u1-kb-ns", "theory", "Namespaces: PID, rede, montagem e usuário",
                    kb=KB + "containers-namespaces-container-security-protections-namespaces", minutes=30),
                act("lx-m3-u1-kb-caps", "theory", "Capabilities em containers",
                    kb=KB + "containers-namespaces-container-security-protections-capabilities", minutes=40),
                act("lx-m3-u1-kb-seccomp", "theory", "seccomp",
                    kb=KB + "containers-namespaces-container-security-protections-seccomp", minutes=25),
                act("lx-m3-u1-kb-apparmor", "theory", "AppArmor",
                    kb=KB + "containers-namespaces-container-security-protections-apparmor", minutes=30),
                act("lx-m3-u1-kb-masked", "theory", "Caminhos mascarados e somente leitura",
                    kb=KB + "containers-namespaces-container-security-protections-masked-paths", minutes=20),
                act("lx-m3-u1-kb-nnp", "theory", "`no_new_privs`",
                    kb=KB + "containers-namespaces-container-security-protections-no-new-privileges", minutes=20),
            ],
        ),
        unit(
            "escape",
            "Escape de container",
            "Testar as condições concretas que quebram o isolamento.",
            ["docker socket", "privileged", "host mounts", "runc", "containerd"],
            [
                act("lx-m3-u2-kb-priv", "theory", "Escape de containers `--privileged`",
                    kb=KB + "containers-namespaces-container-security-privileged-containers", minutes=25),
                act("lx-m3-u2-kb-mounts", "theory", "Montagens sensíveis do host",
                    kb=KB + "containers-namespaces-container-security-sensitive-host-mounts", minutes=40),
                act("lx-m3-u2-kb-api", "theory", "Exposição da API do runtime e do daemon",
                    kb=KB + "containers-namespaces-container-security-runtime-api-and-daemon-exposure", minutes=30),
                act("lx-m3-u2-kb-runc", "theory", "Escalação de privilégios do runC",
                    kb=KB + "containers-namespaces-runc-privilege-escalation", minutes=15),
                act("lx-m3-u2-kb-ctr", "theory", "Escalação de privilégios do containerd (ctr)",
                    kb=KB + "containers-namespaces-containerd-ctr-privilege-escalation", minutes=15),
                act("lx-m3-u2-ex-escape", "exercises", "Exercício: mapa de isolamento",
                    body_md=(
                        "Suba um container deliberadamente mal configurado que **você mesmo** criou\n"
                        "(nunca um terceiro). Monte uma matriz:\n\n"
                        "| Configuração | Que escape é possível | Por quê |\n\n"
                        "Casos mínimos: `--privileged`, `-v /:/host`, socket docker montado, `--pid=host`,\n"
                        "`--cap-add SYS_ADMIN`.\n\n"
                        "Comprove cada linha com um comando e a saída que demonstra acesso ao host.\n"
                        "Se a tentativa falhou, registre qual controle bloqueou (seccomp, AppArmor, userns)."
                    ), minutes=75),
            ],
        ),
        unit(
            "hardening",
            "Avaliação e hardening",
            "Produzir recomendação de endurecimento com referência à configuração testada.",
            ["distroless", "assinatura de imagem", "authorization plugins", "read-only"],
            [
                act("lx-m3-u3-kb-assess", "theory", "Avaliação e hardening de containers",
                    kb=KB + "containers-namespaces-container-security-assessment-and-hardening", minutes=35),
                act("lx-m3-u3-kb-img", "theory", "Segurança, assinatura e secrets de imagens",
                    kb=KB + "containers-namespaces-container-security-image-security-and-secrets", minutes=30),
                act("lx-m3-u3-kb-distroless", "theory", "Containers distroless",
                    kb=KB + "containers-namespaces-container-security-distroless", minutes=30),
                act("lx-m3-u3-kb-authz", "theory", "Plugins de autorização em runtime",
                    kb=KB + "containers-namespaces-container-security-authorization-plugins", minutes=30),
            ],
        ),
    ],
    summary="Container não é sandbox. É processo com nome diferente — e as fronteiras são testáveis.",
    completion="Matriz de isolamento comprovada e recomendação de hardening escrita.",
    requires="escalada-local",
)

m4 = mod(
    "pos-exploracao",
    "Pós-exploração e persistência em Linux",
    "Manter acesso de forma que sobreviva a reboot e documentar cada mecanismo para remoção.",
    ["persistência", "exfiltração", "pivoting básico", "fileless", "limpeza"],
    [
        unit(
            "persistencia",
            "Persistência",
            "Enumerar e construir mecanismos de persistência com evidência e caminho de remoção.",
            ["cron", "systemd", "ld.so", "SSH", "shell startup"],
            [
                act("lx-m4-u1-kb-post", "theory", "Linux pós-exploração",
                    kb=KB + "post-exploitation", minutes=45),
                act("lx-m4-u1-kb-fileless", "theory", "Execução fileless no Linux",
                    kb=KB + "post-exploitation-linux-fileless-execution", minutes=25),
                act("lx-m4-u1-kb-daemons", "theory", "Daemons trojanizados e reverse proxies",
                    kb=KB + "post-exploitation-trojanized-system-daemons-and-reverse-proxies", minutes=20),
                act("lx-m4-u1-kb-shellstart", "theory", "Inicialização do shell, aliases e histórico",
                    kb=KB + "linux-basics-shell-startup-aliases-and-history", minutes=20),
                act("lx-m4-u1-kb-ssh", "theory", "SSH agent forwarding",
                    kb=KB + "user-information-ssh-forward-agent-exploitation", minutes=15),
                act("lx-m4-u1-kb-payloads", "theory", "Payloads de execução (cron/systemd/D-Bus)",
                    kb=KB + "processes-crontab-systemd-dbus-payloads-to-execute", minutes=20),
                act("lx-m4-u1-ex-persist", "exercises", "Exercício: persistência auditável",
                    body_md=(
                        "Num container descartável, implemente **dois** mecanismos de persistência\n"
                        "(por exemplo, timer systemd de usuário e entrada em `~/.bashrc`).\n\n"
                        "Para cada um entregue: artefato criado, caminho, comando de verificação,\n"
                        "comando de remoção, e como um analista o encontraria (arquivo, mtime, log).\n\n"
                        "Destrua o container ao final. Este exercício ensina detecção tanto quanto persistência."
                    ), minutes=45),
            ],
        ),
        unit(
            "rede-e-movimento",
            "Rede e movimento",
            "Mapear a rede a partir do host comprometido sem quebrar escopo.",
            ["sockets", "egress", "pivot", "tunelamento", "metadados"],
            [
                act("lx-m4-u2-kb-net", "theory", "Triagem de rede local e sockets",
                    kb=KB + "network-information-local-network-and-socket-triage", minutes=30),
                act("lx-m4-u2-kb-egress", "theory", "Captura de tráfego, firewall e egress",
                    kb=KB + "network-information-traffic-capture-and-firewall-egress", minutes=20),
                act("lx-m4-u2-kb-md", "theory", "Metadados de instância na nuvem a partir de Linux",
                    kb=KB + "post-exploitation-cloud-instance-metadata", minutes=15),
                act("lx-m4-u2-lab-meridian", "lab", "Máquina: Meridian Bank (cadeia web → host)",
                    lab="machine-meridian-bank", minutes=60),
                act("lx-m4-u2-project", "project", "Relatório de privesc do capstone",
                    minutes=90,
                    body_md=(
                        "Produza o relatório técnico do **capstone** desta trilha a partir do host\n"
                        "comprometido.\n\n"
                        "Estrutura obrigatória:\n\n"
                        "1. Escopo e origem loopback usada.\n"
                        "2. Inventário priorizado: arquivo/binário, contexto (SUID, capability, sudo,\n"
                        "   cron, grupo), por que gera privilégio.\n"
                        "3. Cadeia: cada elo com comando executado e saída que prova o passo.\n"
                        "4. Persistência encontrada e persistência criada, com remoção comprovada.\n"
                        "5. Hardening: por achado, o arquivo/configuração e a linha exata a corrigir.\n\n"
                        "Critério de aceite: outro operador reproduz cada passo a partir do relatório."
                    )),
                act("lx-m4-u2-assess", "assessment", "Avaliação: persistência e escopo",
                    minutes=20,
                    questions=[
                        {"id": "q1", "prompt": "Qual unidade systemd define um timer? Responda com o sufixo.",
                         "accepted": [".timer", "timer", ".timer unit"]},
                        {"id": "q2", "prompt": "Qual arquivo de configuração do ld.so pode carregar biblioteca em binário SUID?",
                         "accepted": ["/etc/ld.so.preload", "ld.so.preload"]},
                        {"id": "q3", "prompt": "Persistência fora do escopo autorizado é aceitável? Responda sim ou não.",
                         "accepted": ["nao", "não", "no"]},
                    ]),
            ],
        ),
    ],
    summary="Persistência é prova de impacto — e obrigação de remoção documentada.",
    completion="Dois mecanismos implementados, removidos e documentados; avaliação ≥ 70%.",
    requires="containers-e-docker",
)

path = {
    "slug": "linux-security",
    "title": "Linux Security & Privilege Escalation",
    "codename": "LNX",
    "domain": "linux",
    "summary": "Modelo de permissão, enumeração metódica, escalada local, containers e pós-exploração em sistemas Linux.",
    "description": (
        "A trilha constrói o entendimento do modelo de privilégio do Linux (uid/euid, bits, "
        "capabilities, PATH) e usa esse entendimento para enumerar, priorizar e explorar escalada "
        "de privilégios em laboratório. A segunda metade trata containers como fronteira testável "
        "e pós-exploração com persistência e remoção documentadas. Ferramentas (LinPEAS, pspy, "
        "linux-exploit-suggester, GTFOBins) aparecem como apoio, nunca como substituto do raciocínio."
    ),
    "entry_level": "usuário de Linux confortável com shell e permissões",
    "exit_level": "capaz de enumerar, escalar e documentar privesc Linux, incluindo containers",
    "estimated_hours": 50,
    "priority": 30,
    "phase": 1,
    "icon": "terminal",
    "accent": "green",
    "prerequisites": [],
    "competencies": [
        "Prever o efeito de permissão, bit e capability",
        "Enumerar privilégio fora do usuário e priorizar achados",
        "Explorar SUID, capabilities, sudo e cron com evidência",
        "Avaliar e testar isolamento de container",
        "Implementar e remover persistência documentada",
    ],
    "tools": ["LinPEAS", "LinEnum", "pspy", "linux-exploit-suggester", "GTFOBins", "find", "getcap", "sudo"],
    "equipment": "Somente software: containers locais e as máquinas da plataforma.",
    "modules": [m0, m1, m2, m3, m4],
    "capstone": {
        "objective": "Comprometer um host Linux multi-estágio por via de privesc e documentar o caminho completo.",
        "scope_md": (
            "A máquina `machine-meridian-bank` na origem loopback atribuída pelo gerenciador. "
            "Escopo é o container do lab; não testar o host da plataforma."
        ),
        "resources_md": "REDVAULT, shell, LinPEAS, pspy, GTFOBins, linux-exploit-suggester. Sem recursos pagos.",
        "steps_md": (
            "1. Reconhecimento do host: identidade, kernel, serviços expostos.\n"
            "2. Enumeração completa (SUID, capabilities, sudo, cron, grupos, montagens).\n"
            "3. Priorização em tabela, com mecanismo por achado.\n"
            "4. Exploração até root com evidência de cada passo.\n"
            "5. Mapa de persistência encontrada/criada e remoção.\n"
            "6. Recomendações de hardening com arquivo e linha."
        ),
        "success_criteria": [
            "Root obtido na máquina",
            "Cada passo de escalada com comando e saída reproduzíveis",
            "Inventário de enumeração priorizado e entregue",
            "Recomendação de hardening correspondente a cada achado",
        ],
        "evidence": [
            "Saída de enumeração (find, getcap, sudo -l, id)",
            "Comando e saída de cada passo de escalada",
            "Tabela de achados com mecanismo e correção",
        ],
        "expected_result": "Host comprometido com cadeia de privesc documentada e remediações propostas.",
        "grading_md": (
            "Clareza do inventário (25%), correção técnica de cada exploração (35%), evidência (20%), "
            "hardening proposto (20%). Escalada por força bruta sem explicação não pontua."
        ),
        "challenge_slug": "machine-meridian-bank",
    },
}

out = ROOT / "content" / "learning_paths" / "03-linux-security.json"
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")