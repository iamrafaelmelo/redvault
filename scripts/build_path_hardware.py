#!/usr/bin/env python3
"""Generate content/learning_paths/08-hardware-hacking.json (Hardware Hacking).

Requirement honoured here: every activity declares its `equipment` class so the
operator never assumes a task runs on their machine when it needs a scope:

* ``software``  — runs on the machine the operator already has.
* ``optional``  — better with a device, but has a software-only equivalent.
* ``simulated`` — needs a device that is emulated in software.
* ``required``  — cannot be done without the named physical device.

The path deliberately does **not** assume any specific equipment. When a task
needs hardware, it either names the cheapest workable option and the
software-only alternative, or tells the operator plainly that it is blocked.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import act, mod, unit  # noqa: E402

H = "ht-hardware-physical-access-hardware-hacking"
FW = "ht-hardware-physical-access-firmware-analysis"
RAD = "ht-hardware-physical-access-radio-hacking"

m0 = mod(
    "fundamentos-eletronicos",
    "Fundamentos eletrônicos para segurança de hardware",
    "Ler uma placa e medir sinais sem danificar o alvo — ou, sem equipamento, aprender a simular o circuito.",
    ["tensão", "terra", "nível lógico", "série", "pull-up", "osciloscópio", "multímetro"],
    [
        unit(
            "eletrica-basica",
            "Eletricidade e níveis lógicos",
            "Distinguir o que é seguro medir do que destrói o alvo.",
            ["VCC/GND", "3,3 V vs 5 V", "conversor de nível", "continuidade"],
            [
                act("hw-m0-u1-own-placa", "theory", "Reconhecimento de placa: identificar componentes e pontos de teste",
                    kb="own-hardware-reconhecimento-placa", minutes=50, equipment="software"),
                act("hw-m0-u1-own-componentes", "theory", "Identificar componentes e ler datasheets sem inventar pinagem",
                    kb="own-hardware-identificar-componentes", minutes=45, equipment="software"),
                act("hw-m0-u1-kb-intro", "theory", "Hacking de hardware — visão geral",
                    kb=H, minutes=30, equipment="software"),
                act("hw-m0-u1-ex-calculo", "exercises", "Exercício: dimensionar um divisor de tensão",
                    equipment="software", minutes=40,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Nenhum componente necessário.\n\n"
                        "Você vai ler um sinal de 5 V com um adaptador de depuração que aceita "
                        "no máximo 3,3 V.\n\n"
                        "1. Calcule o divisor resistivo que leva 5 V a ~3,0 V.\n"
                        "2. Verifique a corrente de fuga sobre o resistor de pull-down e "
                        "explique por que ela importa num barramento com pull-up fraco.\n"
                        "3. Repita o cálculo para um sinal de 1,8 V lido por adaptador de 3,3 V "
                        "e explique por que aqui não se usa resistor.\n"
                        "4. Monte o circuito num simulador livre (por exemplo, adaptador online "
                        "de simulação de circuitos); registre a tensão medida na simulação.\n\n"
                        "Entregável: cálculos, o que a simulação confirmou, e a lista de "
                        "componentes que você precisaria comprar para executar fisicamente."
                    )),
                act("hw-m0-u1-ex-sim", "exercises", "Exercício: simular pull-up e I²C",
                    equipment="simulated", minutes=45,
                    body_md=(
                        "**EQUIPAMENTO SIMULADO.** Roda em simulador de circuito, sem hardware.\n\n"
                        "1. Monte um barramento I²C com dois pull-ups e simule a transmissão de "
                        "um byte `0x48`.\n"
                        "2. Reduza o pull-up a um valor muito alto e mostre o efeito na borda "
                        "de subida.\n"
                        "3. Repita com um dispositivo lento e explique o alongamento de clock.\n\n"
                        "Entregável: capturas do simulador e a relação entre resistência de "
                        "pull-up, capacitância e tempo de subida.\n\n"
                        "Se você tiver osciloscópio, repita num módulo real e compare — mas o "
                        "exercício é aceito apenas com a simulação."
                    )),
            ],
        ),
        unit(
            "medicao-real",
            "Medição real (requer instrumento)",
            "Quando o equipamento existe, aqui está a sequência que não estraga o alvo.",
            ["multímetro", "osciloscópio", "analisador lógico", "terra de referência"],
            [
                act("hw-m0-u2-kb-jtag", "theory", "JTAG — busca de pinos e configuração de hardware",
                    kb=H + "-jtag", minutes=60, equipment="software"),
                act("hw-m0-u2-kb-uart", "theory", "UART",
                    kb=H + "-uart", minutes=50, equipment="software"),
                act("hw-m0-u2-kb-spi", "theory", "SPI",
                    kb=H + "-spi", minutes=45, equipment="software"),
                act("hw-m0-u2-kb-i2c", "theory", "I²C",
                    kb=H + "-i2c", minutes=40, equipment="software"),
                act("hw-m0-u2-ex-multimetro", "exercises", "Exercício: medir sem danificar",
                    equipment="required", minutes=50,
                    body_md=(
                        "**EXIGE EQUIPAMENTO:** multímetro. Use uma placa descartável que você "
                        "comprou ou um equipamento seu.\n\n"
                        "1. Com a placa **desenergizada**, meça continuidade com o plano de "
                        "terra e identifique os pads de GND.\n"
                        "2. Energize e meça a tensão de alimentação em três pontos.\n"
                        "3. Identifique o pino Vtref que o adaptador JTAG usaria.\n"
                        "4. Registre cada medida com o ponto de referência usado.\n\n"
                        "Se você **não** tem multímetro: este exercício fica bloqueado. Não marque "
                        "como concluído — o equivalente em software é o exercício de simulação "
                        "do módulo 0, que já conta para a trilha.\n\n"
                        "Entregável: tabela de medidas + foto da placa."
                    )),
            ],
        ),
    ],
    summary="A metade da trilha que roda sem hardware é a metade que ensina o que medir.",
    completion="Exercícios de cálculo, simulação e (se houver instrumento) de medição entregues.",
    minutes=480,
)

m1 = mod(
    "interfaces-de-debug",
    "Interfaces de depuração e barramentos",
    "Encontrar e usar UART, JTAG/SWD, SPI e I²C — sabendo o que cada um exige.",
    ["UART", "JTAG", "SWD", "OpenOCD", "SPI flash", "I²C", "CoreSight"],
    [
        unit(
            "jtag-swd",
            "JTAG e SWD",
            "Do padrão TAP à sessão de depuração real.",
            ["TAP", "boundary scan", "SWDIO/SWCLK", "OpenOCD", "halting"],
            [
                act("hw-m1-u1-kb-tap", "theory", "O Test Access Port e a cadeia JTAG",
                    kb=H + "-jtag", minutes=40, equipment="software"),
                act("hw-m1-u1-kb-coresight", "theory", "Rastreamento de instruções ARM CoreSight",
                    kb=H + "-arm-coresight-instruction-tracing", minutes=35, equipment="software"),
                act("hw-m1-u1-ex-flashrom-plan", "exercises", "Exercício: planejar a leitura de uma flash SPI",
                    equipment="software", minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Sem placa, sem gravador.\n\n"
                        "Dado um roteador de descarte com uma flash W25Q64 (SOIC-8), escreva o "
                        "plano completo:\n\n"
                        "1. Como identificar o pino 1 e por que inverter VCC/GND é o erro fatal.\n"
                        "2. Decida entre leitura no lugar (in-circuit) e remoção do chip; "
                        "justifique com o que aprendeu sobre o barramento estar compartilhado.\n"
                        "3. Qual tensão o adaptador deve usar e como confirmar.\n"
                        "4. Qual ferramenta livre lê a flash e qual comando de identificação "
                        "você usaria primeiro.\n"
                        "5. Depois de lida, qual é o próximo passo (analisar o firmware).\n\n"
                        "Entregável: plano passo a passo com pontos de decisão. Marque quais "
                        "exigem comprar um gravador (CH341A/clip) e quais não exigem nada."
                    )),
                act("hw-m1-u1-ex-openocd", "exercises", "Exercício: sessão de depuração com OpenOCD",
                    equipment="required", minutes=70,
                    body_md=(
                        "**EXIGE EQUIPAMENTO:** alvo ARM acessível por SWD (qualquer placa de "
                        "desenvolvimento barata que você já tenha) e um adaptador (ST-Link ou "
                        "FT2232H).\n\n"
                        "1. Suba o OpenOCD com o arquivo de configuração do adaptador e do alvo.\n"
                        "2. Interrompa o processador (halt) e leia os registradores.\n"
                        "3. Leia um bloco de memória e salve.\n"
                        "4. Retome a execução e comprove que o alvo continua funcionando.\n\n"
                        "Entregável: log do OpenOCD e o que cada comando fez.\n\n"
                        "Sem adaptador: use o documento JTAG para entregar a análise do arquivo "
                        "de configuração (quais pinos, qual transporte, qual velocidade) — "
                        "isso é aceito com a marcação de que a sessão real ficou bloqueada."
                    )),
            ],
        ),
        unit(
            "spi-i2c-e-boot",
            "Flash, I²C e bootloader",
            "Explorar armazenamento e inicialização como superfície.",
            ["SPI flash", "eMMC", "bootloader", "U-Boot", "secure boot", "UEFI"],
            [
                act("hw-m1-u2-kb-boot", "theory", "Teste de bootloader",
                    kb=FW + "-bootloader-testing", minutes=50, equipment="software"),
                act("hw-m1-u2-kb-integrity", "theory", "Integridade de firmware",
                    kb=FW + "-firmware-integrity", minutes=35, equipment="software"),
                act("hw-m1-u2-kb-uefi", "theory", "UEFI IFR e NVRAM",
                    kb=FW + "-uefi-ifr-nvram-security-setting-patching", minutes=30, equipment="software"),
                act("hw-m1-u2-kb-mediatek", "theory", "MediaTek bl2_ext — bypass de Secure Boot",
                    kb="ht-hardware-physical-access-firmware-analysis-android-mediatek-secure-boot-bl2-ext-bypass-el3",
                    minutes=30, equipment="software"),
                act("hw-m1-u2-kb-xflash", "theory", "MediaTek XFlash Carbonara DA2",
                    kb="ht-hardware-physical-access-firmware-analysis-mediatek-xflash-carbonara-da2-hash-bypass",
                    minutes=25, equipment="software"),
                act("hw-m1-u2-kb-synology", "theory", "Decriptação de arquivos PAT/SPK",
                    kb="ht-hardware-physical-access-firmware-analysis-synology-encrypted-archive-decryption",
                    minutes=25, equipment="software"),
            ],
        ),
    ],
    summary="JTAG, SWD, SPI e I²C são barramentos; quem não sabe o nível lógico queima o alvo.",
    completion="Plano de leitura de flash entregue e (se houver adaptador) sessão de depuração.",
    requires="fundamentos-eletronicos",
    minutes=600,
)

m2 = mod(
    "analise-de-firmware",
    "Análise de firmware (100% software)",
    "Do binário à vulnerabilidade sem tocar em hardware.",
    ["binwalk", "squashfs", "Ghidra", "binário ARM/MIPS", "emulação", "secrets"],
    [
        unit(
            "extracao",
            "Extração e sistema de arquivos",
            "Reconhecer o formato, extrair e ler o sistema de arquivos.",
            ["binwalk", "squashfs", "cramfs", "entropia", "credenciais embutidas"],
            [
                act("hw-m2-u1-kb-fw", "theory", "Análise de firmware (documento completo)",
                    kb=FW, minutes=150, equipment="software"),
                act("hw-m2-u1-kb-linux", "theory", "Linux e o que esperar de um sistema embarcado",
                    kb="ht-linux-hardening", minutes=30, equipment="software"),
                act("hw-m2-u1-own-ghidra", "theory", "Análise de binário de firmware com Ghidra",
                    kb="own-hardware-firmware-ghidra", minutes=70, equipment="software"),
                act("hw-m2-u1-ex-extract", "exercises", "Exercício: extrair e inventariar um firmware",
                    equipment="software", minutes=90,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Escolha um firmware que você tenha o direito de "
                        "analisar: uma imagem de atualização pública do fabricante, ou uma "
                        "distribuição de firmware vulnerável para treino.\n\n"
                        "1. Identifique o formato e as assinaturas (`binwalk`).\n"
                        "2. Extraia o sistema de arquivos e confirme o tipo.\n"
                        "3. Liste os binários com bit SETUID.\n"
                        "4. Procure credenciais, chaves e URLs embutidas.\n"
                        "5. Registre cada achado com caminho e trecho.\n\n"
                        "Entregável: inventário com evidência. Nada de 'parece que tem senha'."
                    )),
            ],
        ),
        unit(
            "binarios-e-emulacao",
            "Binários, símbolos e emulação",
            "Ler código sem símbolos e confirmar comportamento fora do dispositivo.",
            ["Ghidra", "radare2", "qemu-user", "strings", "NX/ASLR/canary"],
            [
                act("hw-m2-u2-ex-ghidra", "exercises", "Exercício: mapa de funções de um daemon",
                    equipment="software", minutes=90,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Pegue o binário principal de um serviço do firmware extraído no "
                        "exercício anterior.\n\n"
                        "1. Importe no Ghidra com a arquitetura correta e **o endereço base** "
                        "do binário.\n"
                        "2. Identifique a função que trata a entrada de rede/arquivo.\n"
                        "3. Meça os buffers: onde há `strcpy` ou `memcpy` com tamanho fixo?\n"
                        "4. Verifique presença de canary, NX e PIE.\n"
                        "5. Para cada candidato, escreva **por que** é explorável ou não, "
                        "citando o trecho.\n\n"
                        "Entregável: mapa de funções + análise. \"Parece vulnerável\" não é "
                        "entregável."
                    )),
                act("hw-m2-u2-ex-emulacao", "exercises", "Exercício: emulação com qemu-user",
                    equipment="software", minutes=75,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Rode um binário do firmware extraído no seu host com `qemu-user` "
                        "(e as bibliotecas do próprio sistema de arquivos extraído).\n\n"
                        "1. Resolva a arquitetura (o binário é ARM/MIPS?).\n"
                        "2. Forneça as bibliotecas necessárias (use o `LD_LIBRARY_PATH` do "
                        "rootfs extraído).\n"
                        "3. Faça o binário responder a uma entrada de teste.\n"
                        "4. Registre o que falhou por depender de hardware (I/O, NVRAM) e "
                        "o que funcionou.\n\n"
                        "Entregável: linha de comando completa + saída, e a lista de "
                        "dependências que impediram a emulação."
                    )),
                act("hw-m2-u2-assess", "assessment", "Avaliação: firmware sem decoreba",
                    minutes=25, equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Por que carregar um binário de firmware no endereço errado estraga a análise?",
                         "accepted": ["ponteiros", "endereco base", "endereço base", "base address",
                                      "desalinha", "image base"]},
                        {"id": "q2", "prompt": "Qual ferramenta de código aberto da NSA descompila binários de firmware?",
                         "accepted": ["ghidra"]},
                        {"id": "q3", "prompt": "O que verificar num binário antes de afirmar que um overflow é explorável? (3 nomes)",
                         "accepted": ["nx", "aslr", "pie", "canary", "stack canary"]},
                    ]),
            ],
        ),
    ],
    summary="A parte mais profunda da trilha não precisa de nenhum equipamento — só da imagem de firmware.",
    completion="Firmware inventariado, binário analisado, avaliação ≥ 70%.",
    requires="interfaces-de-debug",
    minutes=660,
)

m3 = mod(
    "sinais-e-rf",
    "Sinais, analisador lógico e rádio",
    "Capturar e decodificar comunicação — e fazer metade disso sem aparelho.",
    ["sigrok", "PulseView", "decodificador", "SDR", "I/Q", "OOK", "FSK", "BLE"],
    [
        unit(
            "analisador-logico",
            "Analisador lógico",
            "Do sinal bruto à mensagem decodificada.",
            ["samplerate", "trigger", "protocol decoder", "stacked decoders", "export"],
            [
                act("hw-m3-u1-own-sigrok", "theory", "Analisador lógico com sigrok",
                    kb="own-hardware-analisador-logico-sigrok", minutes=70, equipment="software"),
                act("hw-m3-u1-ex-demo", "exercises", "Exercício: decodificar com o driver demo",
                    equipment="software", minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.** O sigrok-cli inclui um driver `demo`, um "
                        "dispositivo virtual com canais lógicos e analógicos.\n\n"
                        "1. Rode `sigrok-cli --scan` e confirme o demo.\n"
                        "2. Escolha um decodificador (UART, SPI, I²C) e uma taxa de amostragem "
                        "adequada.\n"
                        "3. Capture com o demo e decodifique com `-P`.\n"
                        "4. Repita empilhando um segundo decodificador (ex.: `spi` → `spiflash`).\n"
                        "5. Exporte a saída para CSV.\n\n"
                        "Entregável: as linhas de comando completas e a interpretação da saída. "
                        "Prove que a taxa de amostragem mudou o resultado, capturando duas vezes "
                        "com taxas diferentes."
                    )),
                act("hw-m3-u1-ex-captura-real", "exercises", "Exercício: capturar UART de um dispositivo",
                    equipment="required", minutes=70,
                    body_md=(
                        "**EXIGE EQUIPAMENTO:** analisador lógico barato (fx2lafw/CH341A em "
                        "modo lógico) ou osciloscópio com decodificação, e um dispositivo que "
                        "você pode abrir legitimamente.\n\n"
                        "1. Identifique TX/RX/GND com multímetro.\n"
                        "2. Capture na inicialização.\n"
                        "3. Encontre o baud rate correto.\n"
                        "4. Salve o log de boot e extraia o que o aparelho informa sobre si.\n\n"
                        "Entregável: captura `.sr` + parâmetros + transcrição.\n\n"
                        "Se não tem analisador: o exercício fica bloqueado. Não invente uma "
                        "captura."
                    )),
            ],
        ),
        unit(
            "sdr",
            "SDR e rádio",
            "Entender I/Q e modulação, e praticar com sinal sintetizado.",
            ["I/Q", "Goertzel", "OOK", "FSK", "GNU Radio", "RTL-SDR"],
            [
                act("hw-m3-u2-own-sdr", "theory", "SDR: fundamentos e prática sem transmissor",
                    kb="own-hardware-sdr-fundamentos", minutes=70, equipment="software"),
                act("hw-m3-u2-kb-radio", "theory", "Rádio — análise de IQ com SigDigger",
                    kb=H + "-radio", minutes=40, equipment="software"),
                act("hw-m3-u2-kb-fissure", "theory", "FISSURE — framework de RF",
                    kb=RAD + "-fissure-the-rf-framework", minutes=30, equipment="software"),
                act("hw-m3-u2-kb-vsat", "theory", "Injeção em forward link VSAT",
                    kb=RAD + "-vsat-forward-link-injection", minutes=20, equipment="software"),
                act("hw-m3-u2-ex-goertzel", "exercises", "Exercício: implementar detecção de tom",
                    equipment="software", minutes=75,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Gere 1 s de amostras I/Q de um tom em 1 kHz, taxa 48 kHz.\n"
                        "2. Implemente o algoritmo de Goertzel (sem FFT) e detecte o tom.\n"
                        "3. Confirme que um tom em 3 kHz **não** é detectado pelo mesmo bin.\n"
                        "4. Gere um sinal OOK `1010...` e recupere os bits por envelope.\n"
                        "5. Quebre o item 4 usando um `T` (duração de símbolo) errado, e "
                        "explique por que o resultado parece 'funcionar'.\n\n"
                        "Entregável: código + gráficos + a lição do item 5."
                    )),
                act("hw-m3-u2-ex-rtl", "exercises", "Exercício: captura real com RTL-SDR",
                    equipment="required", minutes=60,
                    body_md=(
                        "**EXIGE EQUIPAMENTO:** receptor SDR (RTL-SDR é o mais barato).\n\n"
                        "1. `rtl_test` para confirmar o dispositivo.\n"
                        "2. `rtl_power -f 433M:435M:100k -i 10 sweep.csv` e identifique picos.\n"
                        "3. `rtl_sdr -f <freq> -s 2048000 -n 2048000 cap.iq` e abra numa "
                        "ferramenta de análise IQ.\n"
                        "4. Explique o spike no centro do espectro e como corrigi-lo.\n\n"
                        "Entregável: captura + explicação.\n\n"
                        "Sem receptor: use o exercício de sinal sintetizado, que cobre o mesmo "
                        "conceito. Este fica bloqueado."
                    )),
                act("hw-m3-u2-assess", "assessment", "Avaliação: rádio e amostragem",
                    minutes=20, equipment="software",
                    questions=[
                        {"id": "q1", "prompt": "Por que um rádio SDR precisa de dois canais (I e Q)?",
                         "accepted": ["amplitude e fase", "fase", "distinguir frequencias",
                                      "distinguir frequências", "complexo"]},
                        {"id": "q2", "prompt": "Quantas amostras por símbolo no mínimo se recomenda em protocolo síncrono?",
                         "accepted": ["2", "4", "2x", "4x"]},
                        {"id": "q3", "prompt": "O que o Goertzel calcula?",
                         "accepted": ["energia", "potencia", "potência", "tom", "frequencia especifica",
                                      "frequência específica"]},
                    ]),
            ],
        ),
    ],
    summary="Decodificar é software; capturar é hardware. A trilha separa as duas coisas.",
    completion="Exercícios de decodificação e de sinal sintetizado entregues; avaliação ≥ 70%.",
    requires="analise-de-firmware",
    minutes=600,
)

m4 = mod(
    "exploracao-fisica",
    "Exploração física e injeção de falhas",
    "Avaliar o que só se prova no hardware — e saber quando o custo não justifica.",
    ["side-channel", "fault injection", "glitch", "Cold Boot", "DMA", "BadUSB", "UEFI"],
    [
        unit(
            "canais-laterais",
            "Canais laterais e injeção de falhas",
            "Entender a primitiva antes de comprar um equipamento de mil dólares.",
            ["DPA", "CPA", "glitch de clock", "glitch de tensão", "ChipWhisperer"],
            [
                act("hw-m4-u1-kb-sca", "theory", "Análise de canal lateral",
                    kb=H + "-side-channel-analysis", minutes=50, equipment="software"),
                act("hw-m4-u1-kb-fi", "theory", "Injeção de falhas",
                    kb=H + "-fault-injection-attacks", minutes=20, equipment="software"),
                act("hw-m4-u1-ex-plano", "exercises", "Exercício: decidir se vale o esforço",
                    equipment="software", minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Um fabricante diz que a chave AES é segura porque está em hardware. "
                        "Escreva a análise em três partes:\n\n"
                        "1. Quais hipóteses de ataque existem (canal lateral, glitch, leitura "
                        "direta de fusível, extração de memória).\n"
                        "2. Para cada uma: equipamento mínimo, custo aproximado, tempo, e "
                        "que tipo de acesso físico é necessário.\n"
                        "3. Qual hipótese um atacante racional escolheria e por quê.\n\n"
                        "Entregável: tabela. O ponto é **descartar** as hipóteses que não se "
                        "sustentam."
                    )),
                act("hw-m4-u1-ex-simula", "exercises", "Exercício: canal lateral por software",
                    equipment="software", minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Simule o vazamento sem medir nenhum sinal "
                        "elétrico:\n\n"
                        "1. Escreva um detector que consome tempo proporcional ao primeiro bit "
                        "da chave.\n"
                        "2. Meça o tempo real de cada tentativa (por exemplo, 10 000 amostras).\n"
                        "3. Mostre estatisticamente qual bit é 0 e qual é 1.\n"
                        "4. Explique a diferença entre este modelo didático e um ataque real "
                        "(ruído, alinhamento, consumo elétrico).\n\n"
                        "Entregável: código + gráfico + a comparação com o caso real."
                    )),
            ],
        ),
        unit(
            "fisico-hostil",
            "Acesso físico ao host",
            "Avaliar o que o acesso físico entrega, com escopo escrito.",
            ["BadUSB", "Cold Boot", "Thunderbolt DMA", "BitLocker", "UEFI", "kiosk"],
            [
                act("hw-m4-u2-kb-phys", "theory", "Ataques físicos",
                    kb="ht-hardware-physical-access-physical-attacks", minutes=90, equipment="software"),
                act("hw-m4-u2-kb-kiosk", "theory", "Escapando de KIOSK",
                    kb="ht-hardware-physical-access-escaping-from-gui-applications", minutes=50,
                    equipment="software"),
                act("hw-m4-u2-project", "project", "Relatório de hardware (capstone)",
                    equipment="software", minutes=120,
                    body_md=(
                        "Entregue o relatório do **capstone** desta trilha, sobre um dispositivo "
                        "que é **seu** (ou uma imagem de firmware pública). O relatório deve "
                        "ser honesto sobre o que você conseguiu e o que ficou bloqueado por "
                        "falta de equipamento.\n\n"
                        "Estrutura obrigatória:\n\n"
                        "1. **Inventário**: placa, chips, interface de serviço encontrada.\n"
                        "2. **Acesso obtido**: UART, JTAG, SPI, ou apenas firmware extraído.\n"
                        "3. **Análise de firmware**: sistema de arquivos, binários, segredos.\n"
                        "4. **Vulnerabilidades**: cada uma com mecanismo e evidência (ou "
                        "hipótese, se não confirmada).\n"
                        "5. **Matriz de equipamento**: por atividade da trilha, software-only, "
                        "opcional, simulado ou exigia equipamento — e o que ficou bloqueado.\n"
                        "6. **Recomendações** ao fabricante/dono.\n\n"
                        "Critério de aceite: nenhuma afirmação sem evidência **ou** marcação "
                        "explícita de hipótese."
                    )),
                act("hw-m4-u2-ex-fisico", "exercises", "Exercício: análise de acesso físico",
                    equipment="software", minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Escolha um cenário (notebook corporativo com BitLocker, workstation "
                        "com BIOS travada, kiosk):\n\n"
                        "1. Liste as vias de acesso físico possíveis.\n"
                        "2. Para cada uma, o que o atacante ganha e o que fica registrado.\n"
                        "3. Qual controle reduz o **impacto** e qual reduz a **probabilidade**.\n"
                        "4. O que muda se a chave de recuperação estiver no AD vs. no TPM apenas.\n\n"
                        "Entregável: análise com escopo e limites."
                    )),
            ],
        ),
    ],
    summary="A parte mais cara da trilha é a que mais exige decidir o que não vale fazer.",
    completion="Relatório do capstone entregue e análises de custo/hipótese entregues.",
    requires="sinais-e-rf",
    minutes=540,
)

path = {
    "slug": "hardware-hacking",
    "title": "Hardware Hacking",
    "codename": "HW",
    "domain": "hardware",
    "summary": "Interfaces de depuração, análise de firmware, sinais e rádio — com separação explícita entre o que roda só em software e o que exige equipamento.",
    "description": (
        "A trilha é montada para ser feita sem assumir equipamento. Três dos cinco módulos "
        "são integralmente executáveis na máquina que você já tem: reconhecimento a partir de "
        "foto e datasheet, análise de firmware com Ghidra/qemu e decodificação com o driver "
        "demo do sigrok. Só quando o exercício exige um instrumento (multímetro, analisador "
        "lógico, receptor SDR, adaptador de depuração) ele está marcado como tal, com a "
        "alternativa em software e o custo mínimo declarados no próprio enunciado."
    ),
    "entry_level": "Linux e linha de comando; não exige experiência com eletrônica",
    "exit_level": "capaz de analisar firmware, decodificar sinais e decidir com honestidade o que exige hardware",
    "estimated_hours": 48,
    "priority": 60,
    "phase": 2,
    "icon": "cpu",
    "accent": "amber",
    "prerequisites": ["linux-security"],
    "competencies": [
        "Identificar componentes e pontos de teste a partir de documentação",
        "Distinguir o que exige instrumento do que roda em software",
        "Extrair e analisar firmware sem hardware",
        "Ler binário de firmware com Ghidra",
        "Decodificar barramentos e sinais sintetizados",
        "Justificar quando explorar hardware não compensa",
    ],
    "tools": ["Ghidra", "radare2", "binwalk", "qemu-user", "sigrok-cli/PulseView", "OpenOCD", "flashrom", "CH341A", "RTL-SDR", "GNU Radio", "simulador de circuitos"],
    "equipment": (
        "Nada é pressuposto. Os módulos 0 (parte), 2 e 3 (parte) rodam só com software. "
        "Atividades de medição, captura e SDR exigem equipamento e estão marcadas com a "
        "etiqueta EXIGE EQUIPAMENTO; cada uma diz o mínimo necessário e qual alternativa em "
        "software dá o mesmo aprendizado."
    ),
    "modules": [m0, m1, m2, m3, m4],
    "capstone": {
        "objective": "Analisar um dispositivo próprio (ou firmware público) e entregar relatório com matriz honesta de equipamento.",
        "scope_md": (
            "Um dispositivo que é seu, comprado para descarte, ou uma imagem de firmware pública "
            "que você tem o direito de analisar. Nada de terceiros."
        ),
        "resources_md": (
            "Obrigatório: Ghidra, binwalk, qemu-user, sigrok-cli (com demo) — todos livres. "
            "Opcional: multímetro, analisador lógico, RTL-SDR, adaptador SWD. O relatório pode "
            "ser entregue sem nenhum item opcional."
        ),
        "steps_md": (
            "1. Inventariar a placa ou a imagem de firmware.\n"
            "2. Extrair o sistema de arquivos e inventariar binários e segredos.\n"
            "3. Analisar o principal binário e verificar mitigações.\n"
            "4. Decodificar qualquer sinal que você tenha conseguido capturar.\n"
            "5. Preencher a matriz de equipamento.\n"
            "6. Escrever recomendações."
        ),
        "success_criteria": [
            "Inventário de firmware com evidência (caminho e trecho)",
            "Pelo menos uma análise de binário com justificativa de explorabilidade",
            "Matriz de equipamento preenchida para todas as atividades da trilha",
            "Toda afirmação com evidência ou marcada como hipótese",
            "Recomendações acionáveis",
        ],
        "evidence": [
            "Saída de binwalk e árvore do sistema de arquivos",
            "Relatório do Ghidra com funções e buffers",
            "Captura de sinal, quando houver equipamento",
            "Matriz software/equipamento",
        ],
        "expected_result": "Relatório de análise de hardware com limites declarados e sem suposição de equipamento.",
        "grading_md": (
            "Análise de firmware 35%, evidência 25%, honestidade sobre equipamento 25%, "
            "recomendações 15%."
        ),
        "challenge_slug": "",
    },
}

out = ROOT / "content" / "learning_paths" / "08-hardware-hacking.json"
out.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"escrito: {out}")