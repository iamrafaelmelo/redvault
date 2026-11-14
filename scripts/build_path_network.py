#!/usr/bin/env python3
"""Generate content/learning_paths/06-network-pentesting.json (Network Pentesting).

Honesty note: the platform's labs are web applications reachable over the
loopback origin. They are real network targets (TCP, HTTP, SSRF to internal
services), but they are **not** a routed enterprise network with VLANs,
switches or routing protocols. Exercises that need that are declared as
requiring the operator's own isolated network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import act, default_equipment, mod, unit  # noqa: E402

NET = "ht-generic-methodologies-and-resources-pentesting-network"
SVC = "ht-network-services-pentesting-"
TUN = "ht-generic-hacking-tunneling-and-port-forwarding"

m0 = mod(
    "fundamentos-rede",
    "Fundamentos de rede para pentest",
    "Ler um pacote e um roteamento sem depender de ferramenta: ARP, IP, TCP/UDP e o que cada camada permite.",
    ["ARP", "IP", "TCP", "UDP", "ICMP", "NAT", "roteamento", "captura de pacotes"],
    [
        unit(
            "camadas-e-captura",
            "Camadas, encapsulamento e captura",
            "Explicar o caminho de um pacote e provar cada hipótese na captura.",
            ["Ethernet", "ARP", "IP", "TCP handshake", "tcpdump", "Wireshark"],
            [
                act("net-m0-u1-kb-net", "theory", "Pentest de rede — metodologia (documento completo)",
                    kb=NET, minutes=120),
                act("net-m0-u1-kb-proto", "theory", "Protocolos de rede explicados",
                    kb=NET + "-network-protocols-explained-esp", minutes=30),
                act("net-m0-u1-kb-nmap", "theory", "Resumo de Nmap",
                    kb=NET + "-nmap-summary-esp", minutes=45),
                act("net-m0-u1-ex-captura", "exercises", "Exercício: provar o handshake na captura",
                    equipment="software", minutes=60,
                    body_md=(
                        "Numa rede que é sua (máquina local basta), faça:\n\n"
                        "1. Capture o tráfego de uma conexão TCP com `tcpdump -i any -w cap.pcap`.\n"
                        "2. No Wireshark, identifique SYN, SYN-ACK, ACK e o encerramento.\n"
                        "3. Mapeie uma conexão até um destino na internet e liste cada NAT "
                        "que você consegue observar.\n"
                        "4. Gere um ARP request e explique por que a resposta é unicast.\n"
                        "5. Escreva uma regra de filtro BPF que mostre só o handshake.\n\n"
                        "Entregável: pcap + tabela ligando cada campo do cabeçalho ao que "
                        "o documento de protocolos descreve."
                    )),
            ],
        ),
        unit(
            "descoberta-e-scan",
            "Descoberta de hosts e de serviços",
            "Distinguir descoberta de varredura e escolher o tipo que não é bloqueado pela rede alvo.",
            ["ARP scan", "ICMP", "TCP SYN", "UDP scan", "service detection", "NSE"],
            [
                act("net-m0-u2-kb-academy-recon", "theory", "Reconhecimento (Academy)",
                    academy="recon", minutes=40),
                act("net-m0-u2-kb-ipv6", "theory", "Pentest em IPv6",
                    kb=NET + "-pentesting-ipv6", minutes=40),
                act("net-m0-u2-kb-ids", "theory", "Evasão de IDS",
                    kb=NET + "-ids-evasion", minutes=25),
                act("net-m0-u2-ex-scan", "exercises", "Exercício: três caminhos para a mesma descoberta",
                    equipment="software", minutes=60,
                    body_md=(
                        "Contra **um alvo da própria plataforma** (a origem loopback atribuída "
                        "pelo gerenciador de labs), compare:\n\n"
                        "1. `nmap -sn` versus `nmap -Pn -p-` — o que cada um revela e o que "
                        "cada um assume errado.\n"
                        "2. Um scan TCP connect e um scan SYN; registre o que aparece no log "
                        "do servidor em cada caso.\n"
                        "3. Um scan UDP de porta alta com `--top-ports`, e explique por que "
                        "UDP é lento.\n"
                        "4. `-sV` com `--version-intensity 0` e com `9` na mesma porta; "
                        "diga o que mudou.\n\n"
                        "Entregável: tabela comparando tempo, ruído e veracidade."
                    )),
                act("net-m0-u2-assess", "assessment", "Avaliação: leitura de tráfego",
                    minutes=20, equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Que flag TCP indica início de conexão? (sigla)",
                         "accepted": ["syn"]},
                        {"id": "q2", "prompt": "Por que o scan TCP connect é mais visível que o SYN?",
                         "accepted": ["completa o handshake", "handshake completo", "estabelece a conexao",
                                      "estabelece conexão", "tres vias", "three-way", "3-way"]},
                        {"id": "q3", "prompt": "Qual protocolo de descoberta só funciona no mesmo segmento L2?",
                         "accepted": ["arp"]},
                    ]),
            ],
        ),
    ],
    summary="Quem não sabe ler o pacote confunde ferramenta com entendimento.",
    completion="Captura analisada, comparação de scans entregue e avaliação ≥ 70%.",
    minutes=480,
)

m1 = mod(
    "servicos-rede",
    "Serviços de rede e protocolos",
    "Atacar o serviço pelo protocolo, não pela porta: SMB, DNS, LDAP, Kerberos, MSSQL, SNMP, e os serviços esquecidos.",
    ["SMB", "DNS", "LDAP", "Kerberos", "MSSQL", "SNMP", "NFS", "Redis", "MongoDB", "Docker API"],
    [
        unit(
            "identidade-corporativa",
            "SMB, DNS, LDAP e Kerberos",
            "Usar os protocolos de identidade do Windows como superfície de rede.",
            ["SMB signing", "null session", "zone transfer", "LDAP anonymous bind", "AS-REP"],
            [
                act("net-m1-u1-kb-smb", "theory", "SMB — enumeração e ataque",
                    kb=SVC + "pentesting-smb", minutes=60),
                act("net-m1-u1-kb-rpc", "theory", "rpcclient — enumeração via MSRPC",
                    kb=SVC + "pentesting-smb-rpcclient-enumeration", minutes=30),
                act("net-m1-u1-kb-msrpc", "theory", "Pentest de MSRPC (porta 135)",
                    kb=SVC + "135-pentesting-msrpc", minutes=25),
                act("net-m1-u1-kb-dns", "theory", "DNS — enumeração e abuso",
                    kb=SVC + "pentesting-dns", minutes=45),
                act("net-m1-u1-kb-ldap", "theory", "LDAP",
                    kb=SVC + "pentesting-ldap", minutes=40),
                act("net-m1-u1-kb-kerb", "theory", "Kerberos (porta 88)",
                    kb=SVC + "pentesting-kerberos-88", minutes=40),
                act("net-m1-u1-kb-kerblin", "theory", "Coleta de tickets a partir do Linux",
                    kb=SVC + "pentesting-kerberos-88-harvesting-tickets-from-linux", minutes=25),
                act("net-m1-u1-kb-spoof", "theory", "Spoofing de LLMNR/NBT-NS/mDNS/WPAD",
                    kb=NET + "-spoofing-llmnr-nbt-ns-mdns-dns-and-wpad-and-r", minutes=45),
                act("net-m1-u1-ex-smb", "exercises", "Exercício: decidir o ataque pelo cabeçalho SMB",
                    equipment="required", minutes=70,
                    body_md=(
                        "Este exercício exige um **servidor SMB seu** (Samba em container ou VM "
                        "local). A plataforma não expõe SMB.\n\n"
                        "1. Enumere com `nmap --script smb2-security-mode,smb2-capabilities` e "
                        "registre a versão mínima e se o signing é obrigatório.\n"
                        "2. Faça `smbclient -L` anônimo e, se permitido, `rpcclient -U ''`; "
                        "liste o que sai sem credencial.\n"
                        "3. Configure um share e prove acesso e negação com duas contas "
                        "diferentes.\n"
                        "4. Explique, para cada achado, qual ataque ele habilita (relay, "
                        "spray, enumeração de usuários) e a correção.\n\n"
                        "Entregável: tabela achado → ataque habilitado → correção."
                    )),
            ],
        ),
        unit(
            "bancos-e-servicos-esquecidos",
            "Bancos de dados e serviços esquecidos",
            "Reconhecer o serviço pelo que ele devolve, e não só pelo banner.",
            ["MSSQL", "MySQL", "PostgreSQL", "Oracle", "Redis", "MongoDB", "SNMP", "NFS", "IPMI"],
            [
                act("net-m1-u2-kb-mssql", "theory", "MSSQL",
                    kb=SVC + "pentesting-mssql-microsoft-sql-server", minutes=45),
                act("net-m1-u2-kb-mssqlusers", "theory", "Tipos de usuário do MSSQL",
                    kb=SVC + "pentesting-mssql-microsoft-sql-server-types-of-mssql-users", minutes=20),
                act("net-m1-u2-kb-mysql", "theory", "MySQL",
                    kb=SVC + "pentesting-mysql", minutes=30),
                act("net-m1-u2-kb-pg", "theory", "PostgreSQL",
                    kb=SVC + "pentesting-postgresql", minutes=30),
                act("net-m1-u2-kb-oracle", "theory", "Oracle Listener",
                    kb=SVC + "1521-1522-1529-pentesting-oracle-listener", minutes=30),
                act("net-m1-u2-kb-redis", "theory", "Redis",
                    kb=SVC + "6379-pentesting-redis", minutes=30),
                act("net-m1-u2-kb-mongo", "theory", "MongoDB",
                    kb=SVC + "27017-27018-mongodb", minutes=25),
                act("net-m1-u2-kb-snmp", "theory", "SNMP",
                    kb=SVC + "pentesting-snmp", minutes=40),
                act("net-m1-u2-kb-snmprce", "theory", "SNMP — caminho para RCE",
                    kb=SVC + "pentesting-snmp-snmp-rce", minutes=25),
                act("net-m1-u2-kb-nfs", "theory", "NFS",
                    kb=SVC + "nfs-service-pentesting", minutes=30),
                act("net-m1-u2-kb-ipmi", "theory", "IPMI",
                    kb=SVC + "623-udp-ipmi", minutes=25),
                act("net-m1-u2-kb-docker", "theory", "Docker API sem TLS",
                    kb=SVC + "2375-pentesting-docker", minutes=30),
            ],
        ),
        unit(
            "acesso-remoto-e-transferencia",
            "Acesso remoto e transferência",
            "Cobrir os protocolos de administração que aparecem em todo inventário.",
            ["RDP", "WinRM", "VNC", "SSH", "FTP", "TFTP", "SMTP", "NTP", "Telnet", "rsync"],
            [
                act("net-m1-u3-kb-rdp", "theory", "RDP",
                    kb=SVC + "pentesting-rdp", minutes=30),
                act("net-m1-u3-kb-winrm", "theory", "WinRM (5985/5986)",
                    kb=SVC + "5985-5986-pentesting-winrm", minutes=25),
                act("net-m1-u3-kb-vnc", "theory", "VNC",
                    kb=SVC + "pentesting-vnc", minutes=25),
                act("net-m1-u3-kb-ssh", "theory", "SSH",
                    kb=SVC + "pentesting-ssh", minutes=40),
                act("net-m1-u3-kb-ftp", "theory", "FTP e FTP bounce",
                    kb=SVC + "pentesting-ftp", minutes=35),
                act("net-m1-u3-kb-tftp", "theory", "TFTP",
                    kb=SVC + "69-udp-tftp", minutes=20),
                act("net-m1-u3-kb-smtp", "theory", "SMTP",
                    kb=SVC + "pentesting-smtp", minutes=35),
                act("net-m1-u3-kb-ntp", "theory", "NTP",
                    kb=SVC + "pentesting-ntp", minutes=25),
                act("net-m1-u3-kb-telnet", "theory", "Telnet",
                    kb=SVC + "pentesting-telnet", minutes=20),
                act("net-m1-u3-kb-rsync", "theory", "rsync",
                    kb=SVC + "873-pentesting-rsync", minutes=20),
                act("net-m1-u3-assess", "assessment", "Avaliação: escolher o caminho pelo serviço",
                    minutes=25, equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Que atributo de conta torna o AS-REP Roasting possível quando ausente? (nome do atributo)",
                         "accepted": ["dontreqpreauth", "useraccountcontrol", "preauth", "preauthentication"]},
                        {"id": "q2", "prompt": "Qual condição do SMB habilita relay de NTLM? (dois conceitos)",
                         "accepted": ["signing desabilitado", "sem signing", "signing nao obrigatorio",
                                      "signing opcional", "smb signing disabled", "signing disabled"]},
                        {"id": "q3", "prompt": "Que comando SNMP tradicional expõe a árvore inteira com community conhecida?",
                         "accepted": ["snmpwalk"]},
                        {"id": "q4", "prompt": "Qual serviço na porta 2375 normalmente não exige autenticação quando mal configurado?",
                         "accepted": ["docker", "docker api"]},
                    ]),
            ],
        ),
    ],
    summary="A porta diz onde bater; o protocolo diz o que é possível.",
    completion="Exercício SMB entregue e avaliação ≥ 70%.",
    requires="fundamentos-rede",
    minutes=720,
)

m2 = mod(
    "pos-exploracao-rede",
    "Pivoting, movimento e evasão",
    "Atravessar segmentos a partir de um host comprometido, com rastro controlado.",
    ["port forwarding", "SOCKS", "tunnel", "proxychains", "ligolo", "chisel", "VLAN bypass", "ARP spoofing"],
    [
        unit(
            "pivoting",
            "Túneis e pivoting",
            "Escolher o túnel pelo protocolo permitido, não pela ferramenta preferida.",
            ["SSH -L/-R/-D", "socat", "chisel", "proxychains", "DNS tunnel", "ICMP tunnel"],
            [
                act("net-m2-u1-kb-tun", "theory", "Tunelamento e port forwarding (documento completo)",
                    kb=TUN, minutes=120),
                act("net-m2-u1-kb-squid", "theory", "Squid como pivô",
                    kb=SVC + "3128-pentesting-squid", minutes=25),
                act("net-m2-u1-kb-socks", "theory", "SOCKS proxy",
                    kb=SVC + "1080-pentesting-socks", minutes=20),
                act("net-m2-u1-kb-rpcbind", "theory", "rpcbind",
                    kb=SVC + "pentesting-rpcbind", minutes=20),
                act("net-m2-u1-kb-es", "theory", "Elasticsearch exposto",
                    kb=SVC + "9200-pentesting-elasticsearch", minutes=20),
                act("net-m2-u1-ex-pivo", "exercises", "Exercício: três túneis, mesmas regras",
                    equipment="required", minutes=75,
                    body_md=(
                        "Este exercício exige **duas máquinas suas** (uma delas alcançável só "
                        "por meio da outra).\n\n"
                        "1. Encaminhe uma porta local para um serviço que só existe na segunda "
                        "máquina, com `ssh -L`.\n"
                        "2. Repita com `ssh -R` (a conexão sai do host remoto).\n"
                        "3. Crie um SOCKS dinâmico e use `proxychains` para alcançar o serviço.\n"
                        "4. Repita com um túnel que passe por DNS ou ICMP, e explique por que "
                        "ele é mais lento e mais ruidoso.\n\n"
                        "Para cada caso, registre: quem inicia a conexão, qual protocolo "
                        "atravessa o firewall, e como um defensor veria isso.\n\n"
                        "Entregável: tabela comparativa."
                    )),
            ],
        ),
        unit(
            "segmentacao-e-man-in-the-middle",
            "Segmentação, spoofing e camada 2",
            "Entender por que a segmentação de rede falha e como a camada 2 é abusada.",
            ["VLAN", "ARP spoofing", "HSRP/GLBP", "STP", "LLMNR", "802.1X"],
            [
                act("net-m2-u2-kb-vlan", "theory", "Bypass de segmentação entre VLANs",
                    kb=NET + "-lateral-vlan-segmentation-bypass", minutes=30),
                act("net-m2-u2-kb-hsrp", "theory", "Ataques a GLBP e HSRP",
                    kb=NET + "-glbp-and-hsrp-attacks", minutes=30),
                act("net-m2-u2-kb-eigrp", "theory", "Ataques a EIGRP",
                    kb=NET + "-eigrp-attacks", minutes=40),
                act("net-m2-u2-kb-dhcpv6", "theory", "DHCPv6",
                    kb=NET + "-dhcpv6", minutes=20),
                act("net-m2-u2-kb-vpn", "theory", "IPsec / IKE VPN",
                    kb=SVC + "ipsec-ike-vpn-pentesting", minutes=40),
                act("net-m2-u2-kb-ot", "theory", "Redes de telecomunicação",
                    kb=NET + "-telecom-network-exploitation", minutes=60),
                act("net-m2-u2-kb-dds", "theory", "DDS-RTPS e segurança",
                    kb=NET + "-dds-rtps-security", minutes=30),
                act("net-m2-u2-kb-smuggling", "theory", "SMTP smuggling",
                    kb=SVC + "pentesting-smtp-smtp-smuggling", minutes=20),
                act("net-m2-u2-kb-etherip", "theory", "Ethernet/IP (industrial)",
                    kb=SVC + "44818-ethernetip", minutes=25),
                act("net-m2-u2-kb-ftp-bounce", "theory", "FTP bounce",
                    kb=SVC + "pentesting-ftp-ftp-bounce-attack", minutes=20),
            ],
        ),
        unit(
            "entregavel-rede",
            "Relatório de rede e capstone",
            "Produzir o artefato final: um mapa de rede com achados classificados.",
            ["relatório", "mapa de rede", "priorização", "risco"],
            [
                act("net-m0-u1-kb-academy-methodology", "theory", "Metodologia (Academy)",
                    academy="methodology", minutes=45),
                act("net-m2-u3-project", "project", "Relatório de pentest de rede (capstone)",
                    equipment="software", minutes=120,
                    body_md=(
                        "Entregue o relatório do **capstone** desta trilha usando a origem "
                        "loopback atribuída pelo gerenciador de labs como alvo.\n\n"
                        "Estrutura obrigatória:\n\n"
                        "1. **Escopo**: faixa de endereços, serviços em escopo, janela de teste.\n"
                        "2. **Metodologia**: descoberta, enumeração, exploração, pós-exploração.\n"
                        "3. **Inventário**: tabela de host → porta → serviço → versão → evidência.\n"
                        "4. **Achados**: cada um com impacto, reprodutibilidade e recomendação "
                        "específica do serviço (não 'atualize o software').\n"
                        "5. **Cadeia de ataque**, quando existir, com o pivô usado.\n"
                        "6. **Mapa de rede** com segmentos e o que é alcançável de cada um.\n\n"
                        "Critério de aceite: um administrador consegue agir em cada linha do item 4."
                    )),
                act("net-m2-u3-ex-relatorio", "exercises", "Exercício: revisar um relatório ruim",
                    equipment="software", minutes=45,
                    body_md=(
                        "Pegue um achado que você mesmo escreveu num exercício anterior e "
                        "reescreva-o três vezes:\n\n"
                        "1. **Como scanner**: 'porta 3306 aberta, MySQL desatualizado'.\n"
                        "2. **Como teste**: 'MySQL 5.7 aceita conexão sem TLS de qualquer origem'.\n"
                        "3. **Como risco**: o que um atacante consegue fazer, em quanto tempo, "
                        "com o que já descobriu.\n\n"
                        "Depois escreva a recomendação em uma frase que o dono do sistema "
                        "possa executar sem perguntar nada.\n\n"
                        "Entregável: as três versões e a recomendação."
                    )),
            ],
        ),
    ],
    summary="Pivoting é decidir qual protocolo vai atravessar; o relatório é decidir o que o cliente consegue consertar.",
    completion="Relatório do capstone entregue e revisão de achado entregue.",
    requires="servicos-rede",
    minutes=660,
)

path = default_equipment({
    "slug": "network-pentesting",
    "title": "Network Pentesting",
    "codename": "NET",
    "domain": "infra",
    "summary": "Do pacote ao serviço: descoberta, enumeração de protocolos corporativos, pivoting entre segmentos e relatório de rede.",
    "description": (
        "A trilha começa na captura e na leitura do pacote, passa pela descoberta de hosts e "
        "pela enumeração dos serviços que aparecem em rede corporativa (SMB, DNS, LDAP, "
        "Kerberos, MSSQL, SNMP, NFS, Redis, Docker), e termina em pivoting, segmentação e "
        "relatório. Os labs da plataforma são aplicações reais acessíveis por TCP na origem "
        "loopback; exercícios que exigem rede roteada, switch ou SMB próprio estão marcados "
        "como tal e não são fingidos como labs da plataforma."
    ),
    "entry_level": "sabe usar terminal Linux e entende IP/TCP em nível básico",
    "exit_level": "capaz de enumerar e atacar serviços de rede, pivotar entre segmentos e entregar relatório de rede",
    "estimated_hours": 38,
    "priority": 35,
    "phase": 2,
    "icon": "route",
    "accent": "violet",
    "prerequisites": ["linux-security"],
    "competencies": [
        "Ler uma captura e explicar cada campo relevante",
        "Escolher o tipo de scan para o ambiente alvo",
        "Enumerar SMB, DNS, LDAP, Kerberos e bancos de dados",
        "Atravessar segmentos com túnel adequado ao filtro",
        "Escrever achado de rede acionável",
    ],
    "tools": ["nmap", "tcpdump", "Wireshark", "smbclient/rpcclient", "ldapsearch", "impacket", "SNMP tools", "chisel/ligolo", "proxychains", "enum4linux-ng"],
    "equipment": (
        "Somente software para captura local, scans contra a origem loopback e relatório. "
        "Os exercícios de SMB, pivoting e camada 2 exigem máquinas/redes próprias e estão "
        "marcados individualmente."
    ),
    "modules": [m0, m1, m2],
    "capstone": {
        "objective": "Executar um pentest de rede completo contra a origem loopback atribuída e entregar relatório com inventário e mapa.",
        "scope_md": (
            "A faixa loopback atribuída pelo gerenciador de labs da plataforma. Exercícios que "
            "exigem rede roteada usam laboratório próprio e não fazem parte da nota do capstone."
        ),
        "resources_md": (
            "REDVAULT, nmap, tcpdump/Wireshark, impacket, ldapsearch. Nenhum recurso pago. "
            "Não é necessário equipamento de rede próprio para o capstone."
        ),
        "steps_md": (
            "1. Definir escopo e janela.\n"
            "2. Descoberta de hosts e portas, com justificativa do tipo de scan.\n"
            "3. Enumeração de cada serviço encontrado.\n"
            "4. Exploração do que for comprovadamente vulnerável.\n"
            "5. Inventário e mapa de rede.\n"
            "6. Achados com impacto, evidência e recomendação executável."
        ),
        "success_criteria": [
            "Inventário completo de host/porta/serviço com evidência",
            "Cada achado reproduzível a partir do relatório",
            "Recomendação específica por achado",
            "Mapa de rede com o que é alcançável de cada segmento",
            "Escopo e limitações declarados",
        ],
        "evidence": [
            "Saída de nmap e capturas",
            "Saída de enumeração por serviço",
            "Tabela host → porta → serviço → versão",
            "Mapa de rede",
            "Achados com correção",
        ],
        "expected_result": "Relatório de pentest de rede completo e acionável.",
        "grading_md": (
            "Cobertura do inventário 25%, precisão dos achados 30%, evidência 25%, "
            "recomendações 20%."
        ),
        "challenge_slug": "",
    },
})

out = ROOT / "content" / "learning_paths" / "06-network-pentesting.json"
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")