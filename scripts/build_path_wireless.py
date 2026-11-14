#!/usr/bin/env python3
"""Generate content/learning_paths/07-wireless-security.json (Wireless Security).

Honesty note: the platform has **no wireless lab**. Every hands-on item here
declares what it needs, and every exercise is scoped to a network the operator
owns. Nothing in this track requires transmitting against a network that is not
yours.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import act, default_equipment, mod, unit  # noqa: E402

W = "ht-generic-methodologies-and-resources-pentesting-wifi"
H = "ht-hardware-physical-access-radio-hacking"

OWN_NETWORK = (
    "Escopo obrigatório: apenas rede e equipamentos **seus**. Monte um AP próprio "
    "(roteador reserva, AP em modo de teste ou hotspot isolado) e trabalhe nele. "
    "A plataforma REDVAULT não possui laboratório sem fio: este exercício não é um "
    "lab da plataforma e exige hardware de rádio."
)

m0 = mod(
    "fundamentos-wifi",
    "Fundamentos de Wi-Fi",
    "Entender 802.11 no nível de quadro: associação, autenticação, criptografia e o que cada camada protege.",
    ["802.11", "associação", "beacon", "WPA2", "WPA3", "SAE", "PMF", "CSMA/CA"],
    [
        unit(
            "quadros-e-associacao",
            "Quadros, associação e criptografia",
            "Explicar por que gerenciamento e dados têm modelos de ameaça distintos.",
            ["beacon", "probe", "association", "deauthentication", "PSK", "SAE"],
            [
                act("wl-m0-u1-kb-fund", "theory", "Fundamentos de Wi-Fi",
                    kb=W + "-wifi-fundamentals", minutes=60),
                act("wl-m0-u1-kb-intro", "theory", "Pentest de Wi-Fi — visão geral",
                    kb=W, minutes=40),
                act("wl-m0-u1-kb-open", "theory", "Redes abertas (OPN)",
                    kb=W + "-open-wifi-opn", minutes=25),
                act("wl-m0-u1-kb-owe", "theory", "OWE — Wi-Fi Enhanced Open",
                    kb=W + "-owe", minutes=25),
                act("wl-m0-u1-kb-pmf", "theory", "Protection Management Frames (PMF)",
                    kb=W + "-protected-management-frames-pmf", minutes=35),
                act("wl-m0-u1-ex-quadros", "exercises", "Exercício: classificar quadros 802.11",
                    equipment="required", minutes=50,
                    body_md=(
                        OWN_NETWORK + "\n\n"
                        "Com um adaptador em modo monitor na sua própria rede:\n\n"
                        "1. Capture 30 s de tráfego e classifique os quadros por tipo e "
                        "subtipo (gerenciamento, controle, dados).\n"
                        "2. Identifique os beacons e o intervalo entre eles.\n"
                        "3. Prove que um quadro de desautenticação é **não autenticado** "
                        "olhando o campo correspondente na captura.\n"
                        "4. Repita com PMF habilitado no seu AP e explique o que mudou.\n\n"
                        "Entregável: tabela de subtipos observados e a comparação com e sem PMF."
                    )),
            ],
        ),
        unit(
            "hardware-e-ambiente",
            "Hardware, drivers e reconhecimento",
            "Saber o que o adaptador que você tem consegue fazer antes de prometer um teste.",
            ["monitor mode", "injection", "chipset", "regdomain", "wardriving"],
            [
                act("wl-m0-u2-kb-hw", "theory", "Hardware, drivers e Linux",
                    kb=W + "-wifi-hardware-drivers-and-linux", minutes=60),
                act("wl-m0-u2-kb-recon", "theory", "Reconhecimento e wardriving",
                    kb=W + "-wifi-reconnaissance-and-wardriving", minutes=45),
                act("wl-m0-u2-kb-setup", "theory", "Montagem do ambiente de reconhecimento",
                    kb=W + "-wifi-reconnaissance-setups", minutes=30),
                act("wl-m0-u2-kb-tools", "theory", "Referência de ferramentas de Wi-Fi",
                    kb=W + "-wifi-tools-reference", minutes=20),
                act("wl-m0-u2-ex-capacidade", "exercises", "Exercício: ficha de capacidade do adaptador",
                    equipment="required", minutes=45,
                    body_md=(
                        "Para o adaptador que você **já tem** (sem comprar nada):\n\n"
                        "1. Identifique o chipset (`lsusb`/`lspci` e o driver carregado).\n"
                        "2. Verifique se aceita modo monitor e se permite injeção.\n"
                        "3. Registre as bandas suportadas e o limite regulatório aplicado "
                        "(`iw reg get`).\n"
                        "4. Monte uma tabela: tarefa da trilha → suportado → não suportado.\n\n"
                        "Se o adaptador não fizer injeção, escreva quais exercícios desta "
                        "trilha ficam bloqueados para você — e não os marque como concluídos."
                    )),
            ],
        ),
    ],
    summary="Rádio é física: o adaptador limita o que qualquer ferramenta consegue fazer.",
    completion="Classificação de quadros e ficha de capacidade entregues.",
    minutes=420,
)

m1 = mod(
    "ataques-psk",
    "Ataques a redes pessoais (PSK)",
    "Entender por que WPA2-PSK resiste a captura passiva e onde ele realmente quebra.",
    ["WPA2-PSK", "4-way handshake", "PMKID", "WPA3-SAE", "WPS", "WEP", "historic"],
    [
        unit(
            "wpa2-e-wpa3",
            "WPA2, WPA3 e as variantes antigas",
            "Distinguir ataque de dicionário sobre handshake de falha criptográfica do protocolo.",
            ["dicionário", "PMKID", "SAE", "downgrade", "WPS PIN"],
            [
                act("wl-m1-u1-kb-wpa2", "theory", "WPA2-Personal (PSK)",
                    kb=W + "-wpa2-personal-psk", minutes=60),
                act("wl-m1-u1-kb-wpa3", "theory", "WPA3-Personal (SAE)",
                    kb=W + "-wpa3-personal-sae", minutes=50),
                act("wl-m1-u1-kb-wps", "theory", "WPS",
                    kb=W + "-wps", minutes=30),
                act("wl-m1-u1-kb-tkip", "theory", "WPA-TKIP",
                    kb=W + "-wpa-tkip", minutes=20),
                act("wl-m1-u1-kb-wep", "theory", "WEP",
                    kb=W + "-wep", minutes=40),
                act("wl-m1-u1-ex-crack", "exercises", "Exercício: quebra de PSK na sua rede",
                    equipment="required", minutes=70,
                    body_md=(
                        OWN_NETWORK + "\n\n"
                        "Na **sua** rede WPA2-PSK, com senha de teste que você conhece:\n\n"
                        "1. Capture um handshake de 4 vias (ou um PMKID) e salve.\n"
                        "2. Converta para o formato do hashcat e quebre contra uma wordlist "
                        "própria.\n"
                        "3. Registre tempo, taxa e tamanho da wordlist.\n"
                        "4. Repita com senha longa e aleatória e explique o resultado em termos "
                        "de entropia, não de 'ferramenta falhou'.\n\n"
                        "Conclusão obrigatória: por que trocar de ferramenta não resolve senha "
                        "fraca, e por que WPA3-SAE muda a equação."
                    )),
            ],
        ),
        unit(
            "redes-empresariais-lado-cliente",
            "Redes empresariais: o lado do cliente",
            "Avaliar suplicantes (supplicants) e o que um dispositivo de usuário expõe na rede corporativa.",
            ["supplicant", "evil twin", "certificado", "EAP-TLS", "perfil salvo"],
            [
                act("wl-m1-u2-kb-client", "theory", "Avaliação de cliente e suplicante",
                    kb=W + "-wifi-client-and-supplicant-assessment", minutes=50),
                act("wl-m1-u2-kb-evil", "theory", "Evil twin e associação de cliente",
                    kb=W + "-evil-twin-rogue-ap-and-client-association-attack", minutes=70),
                act("wl-m1-u2-kb-post", "theory", "Pós-associação e isolamento de cliente",
                    kb="ht-generic-methodologies-and-resources-pentesting-wifi-wifi-post-association-and-client-isolation-attac",
                    minutes=80),
                act("wl-m1-u2-kb-frag", "theory", "FragAttacks",
                    kb=W + "-fragattacks", minutes=40),
                act("wl-m1-u2-assess", "assessment", "Avaliação: PSK e cliente",
                    minutes=20, equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Que material de captura permite ataque de dicionário em WPA2-PSK? (nome)",
                         "accepted": ["handshake", "4-way handshake", "four-way handshake", "eapol", "pmkid"]},
                        {"id": "q2", "prompt": "Por que um ataque de dicionário não se aplica da mesma forma a WPA3-SAE?",
                         "accepted": ["offline", "nao offline", "não offline", "verificacao online",
                                      "demonstração de conhecimento igual", "sae e resistente"]},
                        {"id": "q3", "prompt": "Qual configuração de cliente torna evil twin de EAP-TLS ineficaz?",
                         "accepted": ["validacao de certificado", "validação de certificado",
                                      "certificado do servidor", "server certificate validation",
                                      "verificar certificado"]},
                    ]),
            ],
        ),
    ],
    summary="WPA2-PSK não 'quebra': a senha fraca quebra. Essa diferença é o relatório inteiro.",
    completion="Exercício de quebra entregue e avaliação ≥ 70%.",
    requires="fundamentos-wifi",
    minutes=600,
)

m2 = mod(
    "8021x-e-evil-twin",
    "802.1X, EAP e pontos de acesso falsos",
    "Analisar autenticação empresarial e por que clientes mal configurados entregam credencial.",
    ["802.1X", "EAP", "PEAP", "EAP-TLS", "evil twin", "captive portal", "rogue AP"],
    [
        unit(
            "eap-e-certificados",
            "EAP, métodos e certificados",
            "Prever o resultado de um ataque pela configuração do suplicante.",
            ["PEAP-MSCHAPv2", "EAP-TLS", "EAP-TTLS", "relay de certificado", "RADIUS"],
            [
                act("wl-m2-u1-kb-8021x", "theory", "WPA-Enterprise (802.1X)",
                    kb=W + "-wpa-enterprise-8021x", minutes=70),
                act("wl-m2-u1-kb-eap", "theory", "Métodos EAP",
                    kb=W + "-eap-methods", minutes=70),
                act("wl-m2-u1-kb-eviltls", "theory", "Evil twin com EAP-TLS",
                    kb=W + "-evil-twin-eap-tls", minutes=70),
                act("wl-m2-u1-kb-passpoint", "theory", "Passpoint / Hotspot 2.0 e OpenRoaming",
                    kb=W + "-passpoint-hotspot-2-0-and-openroaming", minutes=55),
                act("wl-m2-u1-ex-eap", "exercises", "Exercício: matriz de risco do suplicante",
                    equipment="software", minutes=60,
                    body_md=(
                        "Só com software (leitura e análise), monte a matriz:\n\n"
                        "| Método EAP | Cliente valida certificado? | Resultado de evil twin | Correção |\n"
                        "|---|---|---|---|\n\n"
                        "Cubra PEAP-MSCHAPv2, EAP-TTLS e EAP-TLS. Para o caso em que o cliente "
                        "**não** valida o certificado do servidor, explique exatamente qual "
                        "material criptográfico é capturado e por que ele tem valor fora da sessão.\n\n"
                        "Depois, escreva a política de configuração de suplicante em 5 linhas.\n\n"
                        "Entregável: matriz + política."
                    )),
            ],
        ),
        unit(
            "portais-e-ap-falso",
            "Portais cativos e pontos de acesso falsos",
            "Entender o que o usuário entrega antes de existir sessão.",
            ["captive portal", "DNS spoofing", "rogue AP", "credential capture"],
            [
                act("wl-m2-u2-kb-captive", "theory", "Portais cativos",
                    kb=W + "-captive-portals", minutes=70),
                act("wl-m2-u2-kb-dos", "theory", "DoS e ataques de quadro de gerenciamento",
                    kb=W + "-wifi-dos-and-management-frame-attacks", minutes=80),
                act("wl-m2-u2-kb-defense", "theory", "Defesa, monitoramento e WIDS",
                    kb=W + "-wifi-defense-monitoring-and-wids", minutes=40),
                act("wl-m2-u2-kb-modern", "theory", "Roaming moderno, 6 GHz e MLO",
                    kb=W + "-modern-wifi-roaming-6ghz-and-mlo", minutes=60),
                act("wl-m2-u2-kb-mesh", "theory", "Mesh e EasyMesh",
                    kb=W + "-wifi-mesh-and-easymesh", minutes=40),
                act("wl-m2-u2-kb-privacy", "theory", "Privacidade, rastreamento e canais laterais",
                    kb=W + "-wifi-privacy-tracking-and-side-channels", minutes=35),
                act("wl-m2-u2-kb-android", "theory", "Monitor e injeção no Android (Nexmon)",
                    kb=W + "-enable-nexmon-monitor-and-injection-on-android", minutes=30),
            ],
        ),
    ],
    summary="Em 802.1X, quem decide o risco é a configuração do cliente, não a do controlador.",
    completion="Matriz de risco do suplicante entregue.",
    requires="ataques-psk",
    minutes=600,
)

m3 = mod(
    "iot-e-rfid",
    "IoT, RFID/NFC, BLE e sub-GHz",
    "Aplicar o modelo a dispositivos que não falam IP: etiquetas, chaves, fones e sensores.",
    ["RFID", "NFC", "iButton", "BLE", "sub-GHz", "LoRa", "infravermelho", "provisionamento"],
    [
        unit(
            "rfid-e-nfc",
            "RFID, NFC e iButton",
            "Distinguir clonagem de etiqueta de ataque a sistema de controle.",
            ["125 kHz", "13,56 MHz", "MIFARE", "Proxmark", "emulação", "Wiegand"],
            [
                act("wl-m3-u1-kb-rfid", "theory", "Pentest de RFID",
                    kb=H + "-pentesting-rfid", minutes=60),
                act("wl-m3-u1-kb-proxmark", "theory", "Proxmark 3",
                    kb=H + "-proxmark-3", minutes=25),
                act("wl-m3-u1-kb-ibutton", "theory", "iButton",
                    kb=H + "-ibutton", minutes=20),
                act("wl-m3-u1-kb-lf", "theory", "Flipper — RFID de 125 kHz",
                    kb=H + "-flipper-zero-fz-125khz-rfid", minutes=20),
                act("wl-m3-u1-kb-nfc", "theory", "Flipper — NFC",
                    kb=H + "-flipper-zero-fz-nfc", minutes=25),
                act("wl-m3-u1-kb-cloner", "theory", "Clonador portátil (MaxiProx)",
                    kb=H + "-maxiprox-mobile-cloner", minutes=30),
                act("wl-m3-u1-kb-access-control", "theory", "Uso de RFID no controle de acesso físico",
                    kb=H + "-flipper-zero", minutes=15,
                    equipment="software"),
            ],
        ),
        unit(
            "ble-subghz-e-iot",
            "BLE, sub-GHz e provisionamento IoT",
            "Cobrir os protocolos de rádio que aparecem em sensores, fechaduras e dispositivos domésticos.",
            ["BLE", "GATT", "Sniffing", "OOK", "FSK", "LoRa", "WPA3 DPP", "Wi-Fi Direct"],
            [
                act("wl-m3-u2-kb-ble", "theory", "Pentest de BLE",
                    kb=H + "-pentesting-ble-bluetooth-low-energy", minutes=70),
                act("wl-m3-u2-kb-subghz", "theory", "RF Sub-GHz",
                    kb=H + "-sub-ghz-rf", minutes=35),
                act("wl-m3-u2-kb-fzsub", "theory", "Flipper — Sub-GHz",
                    kb=H + "-flipper-zero-fz-sub-ghz", minutes=25),
                act("wl-m3-u2-kb-lpwan", "theory", "Redes de baixo consumo e longa distância",
                    kb=H + "-low-power-wide-area-network", minutes=30),
                act("wl-m3-u2-kb-dpp", "theory", "Wi-Fi Easy Connect (DPP)",
                    kb=W + "-wifi-easy-connect-dpp", minutes=40),
                act("wl-m3-u2-kb-direct", "theory", "Wi-Fi Direct e provisionamento IoT",
                    kb=W + "-wifi-direct-and-iot-provisioning", minutes=55),
                act("wl-m3-u2-kb-ir", "theory", "Infravermelho",
                    kb=H + "-infrared", minutes=25),
                act("wl-m3-u2-kb-own-sdr", "theory", "SDR na prática: fundamentos e prática sem transmissor",
                    kb="own-hardware-sdr-fundamentos", minutes=60),
                act("wl-m3-u2-project", "project", "Relatório de segurança sem fio (capstone)",
                    equipment="software", minutes=120,
                    body_md=(
                        "Entregue o relatório do **capstone** desta trilha. O escopo é a sua "
                        "rede e os seus dispositivos — a plataforma não tem laboratório sem fio.\n\n"
                        "Estrutura obrigatória:\n\n"
                        "1. **Inventário de rádio**: SSIDs, bandas, criptografia, WPS, PMF, "
                        "e dispositivos BLE/RFID conhecidos.\n"
                        "2. **Configuração avaliada**: por item, o que está exposto e por quê.\n"
                        "3. **Ataque demonstrado** (ou análise documentada, se o hardware "
                        "não suportar): material capturado, método, tempo.\n"
                        "4. **Risco por dispositivo**: qual classe de ataque funciona e qual "
                        "não funciona.\n"
                        "5. **Plano de correção** priorizado: o que trocar hoje, o que "
                        "trocar no próximo ciclo.\n\n"
                        "Critério de aceite: nenhuma afirmação de 'vulnerável' sem o "
                        "mecanismo nomeado."
                    )),
                act("wl-m3-u2-ex-hardware-gap", "exercises", "Exercício: o que você faria com hardware emprestado",
                    equipment="software", minutes=45,
                    body_md=(
                        "Sem comprar nada, escreva o plano de teste para três cenários que "
                        "**exigem** equipamento que você não tem:\n\n"
                        "1. Um WIDS da rede corporativa que precisa ser avaliado — qual "
                        "adaptador faz injeção e por quê.\n"
                        "2. Uma etiqueta MIFARE Classic — qual ferramenta lê e qual só "
                        "escreve.\n"
                        "3. Um sensor sub-GHz de portão — qual receptor basta para gravar "
                        "e qual é preciso para transmitir.\n\n"
                        "Para cada um: requisito mínimo, o que dá para adiantar só com "
                        "software, e o que fica bloqueado até ter o equipamento.\n\n"
                        "Entregável: plano + lista honesta do que está bloqueado."
                    )),
            ],
        ),
    ],
    summary="Fora do IP, o risco está no protocolo: 125 kHz continua clonável hoje.",
    completion="Relatório do capstone e plano de hardware entregues.",
    requires="8021x-e-evil-twin",
    minutes=660,
)

path = default_equipment({
    "slug": "wireless-security",
    "title": "Wireless Security",
    "codename": "WL",
    "domain": "rf",
    "summary": "802.11, PSK, 802.1X, evil twin e os rádios do dia a dia: RFID, BLE, sub-GHz e IoT.",
    "description": (
        "A trilha cobre a base de 802.11, os ataques a redes pessoais e a diferença entre "
        "'quebrar WPA2' e 'quebrar senha fraca', a análise de redes empresariais pelo lado "
        "do suplicante, e os dispositivos que não falam IP: RFID/NFC, BLE, sub-GHz e "
        "provisionamento de IoT. A plataforma não possui laboratório sem fio; todo exercício "
        "prático é declarado como exigindo adaptador próprio e escopo na sua rede."
    ),
    "entry_level": "Linux básico e noções de PCI/802.11",
    "exit_level": "capaz de avaliar uma rede sem fio e um dispositivo IoT e dizer o que é explorável com o hardware disponível",
    "estimated_hours": 38,
    "priority": 55,
    "phase": 2,
    "icon": "route",
    "accent": "green",
    "prerequisites": ["network-pentesting"],
    "competencies": [
        "Classificar quadros 802.11 e explicar PMF",
        "Determinar a capacidade do hardware antes de prometer um teste",
        "Diferenciar ataque de dicionário de falha criptográfica",
        "Avaliar a configuração de um suplicante 802.1X",
        "Comparar RFID, BLE e sub-GHz por modelo de ameaça",
    ],
    "tools": ["aircrack-ng", "hcxdumptool/hcxtools", "hashcat", "iw/iwconfig", "Kismet", "Wireshark", "Proxmark 3", "Flipper Zero", "bettercap", "Nuand/rtl-sdr"],
    "equipment": (
        "Somente software: leitura, análise documentada e exercícios de matriz/plano. "
        "Prática real exige adaptador Wi-Fi com modo monitor e injeção, e — para RFID/BLE/sub-GHz — "
        "hardware próprio. Nada disso é fornecido pela plataforma."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Avaliar a segurança da própria rede sem fio e dos próprios dispositivos de rádio, e entregar plano de correção.",
        "scope_md": (
            "Rede sem fio do operador (AP próprio, AP de teste ou hotspot isolado) e "
            "dispositivos próprios. Nenhum alvo de terceiros."
        ),
        "resources_md": (
            "Adaptador Wi-Fi com monitor/injeção (se tiver), hashcat, aircrack-ng/hcxtools, "
            "Wireshark, e — opcionalmente — Proxmark/Flipper. O relatório pode ser entregue "
            "sem hardware, marcando o que ficou bloqueado."
        ),
        "steps_md": (
            "1. Inventariar SSIDs, bandas, criptografia, WPS e PMF.\n"
            "2. Registrar a capacidade real do adaptador disponível.\n"
            "3. Tentar o ataque demonstrado no módulo 1 ou analisar por documentação.\n"
            "4. Avaliar dispositivos BLE/RFID/sub-GHz do escopo.\n"
            "5. Produzir plano de correção priorizado."
        ),
        "success_criteria": [
            "Inventário completo com configuração de cada SSID",
            "Capacidade do hardware declarada e respeitada",
            "Cada risco com mecanismo nomeado",
            "O que está bloqueado por falta de equipamento, dito explicitamente",
            "Plano de correção priorizado",
        ],
        "evidence": [
            "Tabela de inventário de rádio",
            "Lista de quadros capturados ou referência documental",
            "Saída do hashcat/aircrack-ng, se aplicável",
            "Plano com prazos",
        ],
        "expected_result": "Relatório de segurança sem fio da rede própria, com plano acionável e limitações declaradas.",
        "grading_md": "Precisão técnica 35%, evidência 25%, honestidade sobre limitações 20%, plano 20%.",
        "challenge_slug": "",
    },
})

out = ROOT / "content" / "learning_paths" / "07-wireless-security.json"
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")