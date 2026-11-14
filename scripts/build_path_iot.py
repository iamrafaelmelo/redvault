#!/usr/bin/env python3
"""Generate content/learning_paths/18-iot-embedded.json (IoT e Embarcados).

A base cobre muito bem os protocolos de dispositivo (Modbus, MQTT, OPC UA,
BACnet, DNP3, PROFINET, EtherNet/IP, RTSP, SNMP, TFTP) e Bluetooth Low Energy.
Firmware tem documento importado e artigo próprio.

Regra de equipamento explícita nesta trilha (mesma da trilha de hardware): cada
atividade declara o que exige. `software` = roda na máquina do operador;
`optional` = melhor com dispositivo, mas tem caminho só com software;
`simulated` = dispositivo emulado em software; `required` = exige aparelho.
Nada aqui pressupõe que o operador tenha qualquer aparelho.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

ICS = "ht-industrial-control-systems"
MODBUS = "ht-network-services-pentesting-pentesting-modbus"
MQTT = "ht-network-services-pentesting-1883-pentesting-mqtt-mosquitto"
RTSP = "ht-network-services-pentesting-554-8554-pentesting-rtsp"
SNMP = "ht-network-services-pentesting-pentesting-snmp"
SNMP_RCE = "ht-network-services-pentesting-pentesting-snmp-snmp-rce"
TFTP = "ht-network-services-pentesting-69-udp-tftp"
UPNP = "ht-generic-methodologies-and-resources-pentesting-network-spoofing-ssdp-and-upnp-devices"
OPCUA = "ht-network-services-pentesting-4840-pentesting-opc-ua"
BACNET = "ht-network-services-pentesting-47808-udp-bacnet"
DNP3 = "ht-network-services-pentesting-20000-pentesting-dnp3"
PROFINET = "ht-network-services-pentesting-pentesting-profinet"
ETHERNETIP = "ht-network-services-pentesting-44818-ethernetip"
IEC104 = "ht-network-services-pentesting-2404-pentesting-iec-60870-5-104"
IEC61850 = "ht-network-services-pentesting-102-pentesting-iec-61850-mms"
BLE = "ht-hardware-physical-access-radio-hacking-pentesting-ble-bluetooth-low-energy"
FWW = "ht-hardware-physical-access-firmware-analysis"
FW_INT = FWW + "-firmware-integrity"
FW_BOOT = FWW + "-bootloader-testing"
FW_OWN = "own-hardware-firmware-ghidra"
WIFI_IOT = "ht-generic-methodologies-and-resources-pentesting-wifi-wifi-direct-and-iot-provisioning"
PCAP = "ht-generic-methodologies-and-resources-basic-forensic-methodology-pcap-inspection"

m0 = mod(
    "contexto-e-escopo",
    "Contexto e escopo",
    "Entender o ambiente de dispositivo e o que muda em relação a um sistema tradicional.",
    ["dispositivo restrito", "ciclo de vida", "protocolo industrial", "escopo"],
    [
        unit(
            "o-que-muda",
            "O que muda em IoT e OT",
            "Reconhecer as restrições que tornam um teste diferente.",
            ["recursos limitados", "ausência de agente", "disponibilidade", "ciclo de vida longo"],
            [
                act("iot-m0-u1-kb-ics", "theory", "Hacking de sistemas de controle industrial",
                    kb=ICS, minutes=55),
                act("iot-m0-u1-ex-diferenca", "exercises",
                    "Exercício: tabela de diferenças entre alvo tradicional e dispositivo",
                    equipment="software", minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Sem dispositivo.\n\n"
                        "Preencha a tabela comparando um servidor Linux com um controlador "
                        "industrial ou câmera IP:\n\n"
                        "| Aspecto | Servidor | Dispositivo | Consequência para o teste |\n"
                        "| --- | --- | --- | --- |\n"
                        "| Acesso a terminal | sim | | |\n"
                        "| Instalação de agente | sim | | |\n"
                        "| Reinício seguro | sim | | |\n"
                        "| Janela de atualização | ampla | | |\n\n"
                        "Responda: por que **negação de serviço não intencional** é risco maior "
                        "aqui do que num servidor comum?"
                    )),
                act("iot-m0-u1-ex-escopo", "exercises",
                    "Exercício: escrever escopo de teste com dispositivo de produção",
                    equipment="software", minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Descreva o que se faz — e o que não se faz — ao testar um dispositivo "
                        "que está **em operação**:\n\n"
                        "1. Testes passivos permitidos sem risco.\n"
                        "2. Testes que exigem janela de manutenção.\n"
                        "3. Testes que só se fazem em réplica de laboratório.\n"
                        "4. Procedimento de parada imediata.\n\n"
                        "Entregue as quatro listas. Dispositivo de produção não é alvo de "
                        "teste exploratório sem réplica."
                    )),
            ],
        ),
    ],
    summary="Recursos limitados, disponibilidade e ciclo de vida: por que OT não é servidor.",
    completion="Tabela de diferenças e escopo de teste com dispositivo em produção.",
)

m1 = mod(
    "protocolos-de-dispositivo",
    "Protocolos de dispositivo",
    "Reconhecer protocolo por porta e comportamento, e entender o que a ausência de autenticação significa.",
    ["Modbus", "MQTT", "RTSP", "SNMP", "UPnP", "TFTP"],
    [
        unit(
            "protocolos-simples",
            "Protocolos simples e sem autenticação",
            "Ler protocolo de campo e descrever o que expõe.",
            ["registrador Modbus", "tópico MQTT", "stream RTSP", "SNMP community"],
            [
                act("iot-m1-u1-kb-modbus", "theory", "502/tcp — Modbus",
                    kb=MODBUS, equipment="software", minutes=45),
                act("iot-m1-u1-kb-mqtt", "theory", "1883 — MQTT (Mosquitto)",
                    kb=MQTT, equipment="software", minutes=45),
                act("iot-m1-u1-kb-rtsp", "theory", "554, 8554 — RTSP",
                    kb=RTSP, equipment="software", minutes=40),
                act("iot-m1-u1-kb-snmp", "theory", "161/udp — SNMP",
                    kb=SNMP, equipment="software", minutes=45),
                act("iot-m1-u1-kb-snmp-rce", "theory", "SNMP RCE",
                    kb=SNMP_RCE, equipment="software", minutes=35),
                act("iot-m1-u1-kb-tftp", "theory", "69/udp — TFTP",
                    kb=TFTP, equipment="software", minutes=30),
                act("iot-m1-u1-kb-upnp", "theory", "Spoofing de dispositivos SSDP e UPnP",
                    kb=UPNP, equipment="software", minutes=35),
                act("iot-m1-u1-ex-mqtt", "exercises",
                    "Exercício: subir broker MQTT local e documentar o que vaza",
                    equipment="software", minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Broker local na sua máquina (Mosquitto ou "
                        "equivalente que você instale). Sem dispositivo.\n\n"
                        "1. Suba o broker sem autenticação.\n"
                        "2. Publique mensagens em dois tópicos.\n"
                        "3. Assine o curinga `#` e mostre tudo que é recebido.\n"
                        "4. Registre o que um interlocutor na rede veria.\n\n"
                        "Responda: por que broker sem autenticação em rede de dispositivo é "
                        "**insight direto** sobre operação — sensores, comandos e estado?\n\n"
                        "Limite: broker escutando só em `127.0.0.1`; não exponha na LAN."
                    )),
            ],
        ),
        unit(
            "protocolos-industriais",
            "Protocolos industriais",
            "Reconhecer os protocolos de OT e o que cada um controla.",
            ["OPC UA", "BACnet", "DNP3", "PROFINET", "EtherNet/IP", "IEC 60870-5-104", "IEC 61850"],
            [
                act("iot-m1-u2-kb-opcua", "theory", "4840 — OPC UA",
                    kb=OPCUA, equipment="software", minutes=40),
                act("iot-m1-u2-kb-bacnet", "theory", "47808/udp — BACnet",
                    kb=BACNET, equipment="software", minutes=35),
                act("iot-m1-u2-kb-dnp3", "theory", "20000 — DNP3",
                    kb=DNP3, equipment="software", minutes=35),
                act("iot-m1-u2-kb-profinet", "theory", "PROFINET",
                    kb=PROFINET, equipment="software", minutes=35),
                act("iot-m1-u2-kb-enip", "theory", "44818 — EtherNet/IP (CIP)",
                    kb=ETHERNETIP, equipment="software", minutes=35),
                act("iot-m1-u2-kb-iec104", "theory", "2404 — IEC 60870-5-104",
                    kb=IEC104, equipment="software", minutes=35),
                act("iot-m1-u2-kb-iec61850", "theory", "102 — IEC 61850 MMS",
                    kb=IEC61850, equipment="software", minutes=35),
                act("iot-m1-u2-ex-matriz", "exercises",
                    "Exercício: matriz de protocolo, porta, transporte e o que controla",
                    equipment="software", minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Leitura dos documentos da unidade.\n\n"
                        "Preencha:\n\n"
                        "| Protocolo | Porta/transporte | Autenticação nativa | O que controla |\n"
                        "| --- | --- | --- | --- |\n\n"
                        "Para os oito protocolos da unidade.\n\n"
                        "Depois responda: em quais deles a ausência de autenticação é **por "
                        "desenho** e não configuração errada? Por que isso muda a "
                        "recomendação de correção?"
                    )),
            ],
        ),
    ],
    summary="Protocolo por porta e comportamento. O que a ausência de autenticação realmente expõe.",
    prereq="contexto-e-escopo",
    completion="Broker MQTT documentado e matriz de protocolos preenchida.",
)

m2 = mod(
    "firmware",
    "Firmware",
    "Analisar firmware por software e distinguir o que exige o aparelho.",
    ["extração", "integridade", "bootloader", "Ghidra"],
    [
        unit(
            "analise-de-firmware",
            "Análise de firmware",
            "Extrair, verificar e ler firmware quando o arquivo já existe.",
            ["imagem", "integridade", "bootloader", "binário ARM/MIPS"],
            [
                act("iot-m2-u1-kb-fw", "theory", "Análise de firmware",
                    kb=FWW, equipment="software", minutes=45),
                act("iot-m2-u1-kb-int", "theory", "Integridade do firmware",
                    kb=FW_INT, equipment="software", minutes=40),
                act("iot-m2-u1-kb-boot", "theory", "Teste do bootloader (leitura)",
                    kb=FW_BOOT, equipment="software", minutes=40),
                act("iot-m2-u1-own-fw", "theory", "Análise de binário de firmware com Ghidra",
                    kb=FW_OWN, equipment="software", minutes=55),
                act("iot-m2-u1-ex-binwalk", "exercises",
                    "Exercício: extrair sistema de arquivos de uma imagem de firmware",
                    equipment="software", minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Precisa de uma imagem de firmware que você já "
                        "tenha (update publicado por fabricante é material público).\n\n"
                        "1. Identifique o formato (`file`, `binwalk`).\n"
                        "2. Extraia os sistemas de arquivos embutidos.\n"
                        "3. Procure: servidor web, scripts de inicialização, credencial "
                        "padrão.\n"
                        "4. Registre o hash da imagem original.\n\n"
                        "Entregue a estrutura extraída e os achados com caminho dentro da "
                        "imagem. Se não tiver imagem nenhuma, declare o bloqueio — não invente "
                        "saída."
                    )),
                act("iot-m2-u1-ex-bootloader", "exercises",
                    "Exercício: descrever o que exige o aparelho para ler o bootloader",
                    equipment="required", minutes=45,
                    body_md=(
                        "**EXIGE EQUIPAMENTO.** Intervenção física com acesso a UART ou a "
                        "pontos de teste na placa.\n\n"
                        "Alternativa só com software: escreva o procedimento **e** a lista do "
                        "que é necessário para executá-lo, sem executar.\n\n"
                        "1. Passos para identificar a interface de depuração.\n"
                        "2. Riscos de tornar a placa inutilizável.\n"
                        "3. Como documentar antes de mexer.\n\n"
                        "Entregue o procedimento. O exercício mede se você sabe **o que falta** "
                        "para executar — e isso é legítimo sem equipamento."
                    )),
            ],
        ),
    ],
    summary="Firmware por software, integridade e o que exige aparelho.",
    prereq="protocolos-de-dispositivo",
    completion="Firmware extraído com achados, ou bloqueio declarado com o que falta.",
)

m3 = mod(
    "radio-e-deteccao",
    "Rádio, detecção e relatório",
    "Cobrir o que não é IP, medir detecção e entregar avaliação honesta.",
    ["BLE", "provisionamento Wi-Fi", "pcap", "deteccao", "relatorio"],
    [
        unit(
            "radio",
            "Rádio",
            "Reconhecer BLE e provisionamento e o que exige adaptador.",
            ["GATT", "BLE", "Wi-Fi Direct", "provisionamento"],
            [
                act("iot-m3-u1-kb-ble", "theory", "Pentesting BLE — Bluetooth Low Energy",
                    kb=BLE, equipment="optional", minutes=45),
                act("iot-m3-u1-kb-wifi", "theory", "Wi-Fi Direct, Aware, AWDL e provisionamento de IoT",
                    kb=WIFI_IOT, equipment="optional", minutes=40),
                act("iot-m3-u1-ex-ble", "exercises",
                    "Exercício: planejar enumeração BLE sem adaptador",
                    equipment="optional", minutes=45,
                    body_md=(
                        "**EQUIPAMENTO OPCIONAL.** Com adaptador BLE: enumere serviço e "
                        "característica de um dispositivo seu.\n\n"
                        "**Somente software:** escreva o plano completo de enumeração — "
                        "adaptador necessário, ferramenta, o que coletar (endereço, "
                        "serviço, característica, propriedade de escrita), e como registrar.\n\n"
                        "Entre uma das duas entregas. O plano vale tanto quanto a execução "
                        "quando o objetivo é aprender o método."
                    )),
            ],
        ),
        unit(
            "deteccao-e-relatorio",
            "Detecção e relatório",
            "Medir o que o ambiente detectaria e entregar avaliação com limites.",
            ["pcap", "detecção", "priorização", "limitações"],
            [
                act("iot-m3-u2-kb-pcap", "theory", "Inspeção de pcap",
                    kb=PCAP, equipment="software", minutes=40),
                act("iot-m3-u2-ex-pcap", "exercises",
                    "Exercício: detectar dispositivo por tráfego",
                    equipment="software", minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Com um pcap que você gere ou já tenha.\n\n"
                        "1. Liste os protocolos de dispositivo visíveis na captura.\n"
                        "2. Monte um filtro que isole um deles.\n"
                        "3. Escreva a regra de detecção que alertaria para dispositivo "
                        "falando fora do padrão.\n\n"
                        "Entregue filtros e regra. Detecção sem filtro documentado é "
                        "anedota."
                    )),
                act("iot-m3-u2-assess", "assessment", "Avaliação: IoT e embarcados",
                    equipment="software", minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "Por que uma varredura agressiva em rede industrial é risco?",
                         "accepted": ["o dispositivo pode parar de operar", "disponibilidade é crítica"],
                         "explanation": "Controladores antigos podem travar com pacote inesperado; disponibilidade vem antes da coleta."},
                        {"id": "q2", "prompt": "O que um broker MQTT sem autenticação permite?",
                         "accepted": ["assinar todos os tópicos", "ler mensagens de sensores e comandos"],
                         "explanation": "O curinga `#` permite ler o que passa por ali, incluindo estado e comando."},
                        {"id": "q3", "prompt": "Qual é a diferença entre 'exige equipamento' e 'não faço ideia de como fazer'?",
                         "accepted": ["o primeiro tem plano e o aparelho falta", "exige equipamento tem procedimento definido"],
                         "explanation": "Exigir equipamento significa que o método existe e só falta o aparelho; o segundo é lacuna de competência."},
                        {"id": "q4", "prompt": "Por que firmware é analisável sem o aparelho?",
                         "accepted": ["a imagem é arquivo", "pode ser extraída e lida com ferramentas"],
                         "explanation": "A imagem é um arquivo; extração, sistema de arquivos e binário podem ser analisados por software."},
                    ]),
                act("iot-m3-u2-project", "project",
                    "Capstone: avaliação de um dispositivo ou de sua imagem",
                    equipment="optional", minutes=170,
                    body_md=(
                        "**EQUIPAMENTO OPCIONAL.** Entrega do capstone.\n\n"
                        "Escolha um **dispositivo seu** (roteador, câmera, placa) ou apenas "
                        "sua **imagem de firmware**.\n\n"
                        "Entregue:\n\n"
                        "1. Inventário: protocolo, porta, transporte, autenticação.\n"
                        "2. Para cada exposição, o que ela revela ou permite.\n"
                        "3. Análise de firmware, se houver imagem.\n"
                        "4. O que exige aparelho e ficou bloqueado, com o plano.\n"
                        "5. Detecção: como o ambiente identificaria uso anômalo.\n"
                        "6. Correção priorizada e limitações.\n\n"
                        "Recusa: inventário sem plano para item bloqueado, ou relatório que "
                        "afirma ter testado protocolo sem ter tido como testá-lo."
                    )),
            ],
        ),
    ],
    summary="BLE, provisionamento, pcap e o relatório com plano para o que ficou bloqueado.",
    prereq="firmware",
    completion="Plano de BLE, detecção em pcap e avaliação aprovada.",
)

path = {
    "slug": "iot-embedded",
    "title": "IoT e Embarcados",
    "codename": "IOT",
    "domain": "iot",
    "summary": "Protocolos de dispositivo, firmware, rádio e detecção: avaliar um dispositivo ou apenas a imagem de firmware, com o que exige aparelho declarado.",
    "description": (
        "A trilha cobre o que a base tem de mais forte em dispositivo: Modbus, MQTT, RTSP, "
        "SNMP, OPC UA, BACnet, DNP3, PROFINET, EtherNet/IP, IEC 60870-5-104, IEC 61850, "
        "BLE e provisionamento Wi-Fi. Firmware é analisável inteiramente por software. "
        "Cada atividade declara o que exige: nada pressupõe que você tenha qualquer "
        "aparelho, e onde um teste exige dispositivo físico o exercício aceita o plano "
        "como entrega legítima."
    ),
    "entry_level": "Redes e Linux; leitura de binário ajudam",
    "exit_level": "capaz de avaliar protocolo, firmware e detecção de um dispositivo próprio, declarando o que ficou bloqueado",
    "estimated_hours": 30,
    "priority": 88,
    "phase": 3,
    "icon": "cpu",
    "accent": "green",
    "prerequisites": ["network-pentesting", "hardware-hacking"],
    "competencies": [
        "Distinguir risco de OT de risco de servidor tradicional",
        "Reconhecer protocolo por porta e o que ele expõe",
        "Extrair e analisar firmware sem o aparelho",
        "Avaliar BLE e provisionamento declarando o que exige adaptador",
        "Detectar comportamento anômalo por tráfego",
        "Entregar avaliação com plano explícito para o que está bloqueado",
    ],
    "tools": ["nmap scripts (mqtt, modbus)", "mosquitto", "binwalk", "Ghidra", "tshark", "Wireshark", "bettercap", "rtl-sdr", "nRF Connect"],
    "equipment": (
        "Somente software é suficiente para a maior parte da trilha: protocolo, broker "
        "local, extração de firmware e análise de pcap. Para BLE e rádio é necessário "
        "adaptador próprio, que a plataforma não fornece — e o exercício correspondente "
        "aceita o plano como entrega."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Avaliar um dispositivo próprio ou a imagem de firmware dele, com inventário de protocolo, análise de firmware, detecção e plano para o que ficou bloqueado.",
        "scope_md": (
            "Dispositivo de propriedade do operador, ou imagem de firmware publicada pelo "
            "fabricante. Nenhum dispositivo em produção de terceiro."
        ),
        "resources_md": (
            "nmap, tshark/Wireshark, binwalk, Ghidra, broker local (opcional). Adaptador "
            "BLE apenas se o operador já tiver."
        ),
        "steps_md": (
            "1. Inventariar protocolos, portas e autenticação.\n"
            "2. Descrever o que cada exposição revela ou permite.\n"
            "3. Extrair e analisar a imagem de firmware, se houver.\n"
            "4. Registrar o que exige aparelho e o plano para isso.\n"
            "5. Escrever regra de detecção.\n"
            "6. Priorizar correções e declarar limitações."
        ),
        "success_criteria": [
            "Inventário de protocolo, porta e autenticação",
            "Impacto declarado por exposição",
            "Análise de firmware com hash e caminho interno dos achados",
            "Itens bloqueados com plano e equipamento necessário",
            "Regra ou filtro de detecção documentado",
            "Correção priorizada e limitações",
        ],
        "evidence": [
            "Inventário de protocolo",
            "Saída de extração de firmware",
            "Registro de item bloqueado com plano",
            "Filtro de detecção",
            "Relatório final",
        ],
        "expected_result": "Avaliação de dispositivo ou firmware com limites declarados e plano para o bloqueado.",
        "grading_md": "Inventário e impacto 30%, análise de firmware 30%, detecção 20%, honestidade de limites 20%.",
        "challenge_slug": "",
    },
}

emit("18-iot-embedded.json", path)