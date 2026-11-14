#!/usr/bin/env python3
"""Generate content/learning_paths/10-digital-forensics.json (Forense Digital).

A plataforma tem um acervo forte de metodologia forense importada (memória,
registro, pcap, carving, Docker, anti-forense) e dois documentos próprios sobre
cadeia de custódia e memória. Não existe laboratório forense: toda prática roda
sobre o próprio sistema, sobre arquivos que o operador já tem ou sobre material
público. A trilha deixa isso dito no texto de cada exercício.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

FM = "ht-generic-methodologies-and-resources-basic-forensic-methodology"
CUST = "own-forense-cadeia-custodia"
MEM = "own-forense-memoria-volatility"
VOL = FM + "-memory-dump-analysis"
VOL_CHEAT = FM + "-memory-dump-analysis-volatility-cheat"
WIN = FM + "-windows-forensics"
WIN_REG = FM + "-windows-forensics-interesting-windows"
LIN = FM + "-linux-forensics"
IMG = FM + "-image-acquisition-and-mount"
CARVE = FM + "-partitions-file-systems-carving"
CARVE_TOOLS = "ht-generic-methodologies-and-resources-basic-forensic-methodology-partitions-file-systems-carving-file-"
PCAP = FM + "-pcap-inspection"
PCAP_WIRESHARK = FM + "-pcap-inspection-wireshark-tricks"
PCAP_WIFI = FM + "-pcap-inspection-wifi-pcap-analysis"
PCAP_DNS = FM + "-pcap-inspection-dnscat-exfiltration"
DOCKER = FM + "-docker-forensics"
ANTI = FM + "-anti-forensic-techniques"
FIM = FM + "-file-integrity-monitoring"
BROWSER = "ht-generic-methodologies-and-resources-basic-forensic-methodology-specific-software-file-type-tricks-br"
OFFICE = "ht-generic-methodologies-and-resources-basic-forensic-methodology-specific-software-file-type-tricks-of"
PDF = "ht-generic-methodologies-and-resources-basic-forensic-methodology-specific-software-file-type-tricks-pd"
ANDROID = FM + "-android-forensics"

m0 = mod(
    "principios",
    "Princípios, cadeia de custódia e aquisição",
    "Coletar prova de forma que o resultado seja útil: aquisição antes da análise, hash de integridade e registro de posse.",
    ["cadeia de custódia", "hash de integridade", "aquisição de imagem", "montagem somente leitura"],
    [
        unit(
            "custodia",
            "Cadeia de custódia",
            "Entender por que a evidência vale o que vale o processo que a acompanha.",
            ["aquisição", "hash", "registro de posse", "cópia de trabalho"],
            [
                act("for-m0-u1-own-custodia", "theory", "Cadeia de custódia e linha do tempo",
                    kb=CUST, minutes=55),
                act("for-m0-u1-kb-metodologia", "theory", "Metodologia básica de forense",
                    kb=FM, minutes=45),
                act("for-m0-u1-ex-registro", "exercises",
                    "Exercício: montar a ficha de custódia de um arquivo seu",
                    minutes=40,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Escolha um arquivo do sistema e trate-o "
                        "como evidência.\n\n"
                        "Preencha a ficha:\n\n"
                        "1. Identificação do arquivo (caminho, origem, data).\n"
                        "2. Hash calculado na coleta (`sha256sum`).\n"
                        "3. Quem coletou e quando.\n"
                        "4. Cópia de trabalho criada, com o hash da cópia.\n"
                        "5. Confirmação de que os hashes coincidem.\n\n"
                        "Depois, responda: se você alterar uma vírgula no arquivo de trabalho, "
                        "o que a ficha revela? Faça o teste e mostre a divergência de hash."
                    )),
            ],
        ),
        unit(
            "aquisicao",
            "Aquisição de imagem",
            "Coletar disco ou partição sem alterar o objeto.",
            ["dd/dcfldd", "montagem somente leitura", "imagem vs cópia", "partição"],
            [
                act("for-m0-u2-kb-image", "theory", "Aquisição de imagem e montagem",
                    kb=IMG, minutes=50),
                act("for-m0-u2-ex-imagem", "exercises",
                    "Exercício: imagem de um pendrive ou arquivo, montada em somente leitura",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Opção segura: sem pendrive, faça a imagem de "
                        "um arquivo de sistema de arquivos que você mesmo crie (`dd` de um "
                        "arquivo para outro, ou `mkfs` num arquivo).\n\n"
                        "1. Crie a imagem (ou use pendrive só se quiser).\n"
                        "2. Calcule o hash **durante** a aquisição, não depois — mostre o "
                        "comando usado.\n"
                        "3. Monte a imagem com `-o ro`.\n"
                        "4. Liste os arquivos e abra um deles.\n"
                        "5. Desmonte e calcule o hash da imagem novamente.\n\n"
                        "Compare os dois hashes. Se forem diferentes, você não usou somente "
                        "leitura — e é exatamente esse o erro que a cadeia de custódia previne."
                    )),
                act("for-m0-u2-ex-particao", "exercises",
                    "Exercício: identificar sistema de arquivos e partições sem montar",
                    minutes=40,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Na imagem do exercício anterior:\n\n"
                        "1. Identifique tipo de sistema de arquivos e layout de partições "
                        "(`file`, `fdisk -l`, `mmls`).\n"
                        "2. Explique o que é o *offset* de uma partição e por que ele importa "
                        "quando a imagem é do disco inteiro.\n"
                        "3. Monte a partição com offset explícito, em somente leitura.\n\n"
                        "Entregue o comando de montagem com o offset calculado, não copiado."
                    )),
            ],
        ),
    ],
    summary="Sem cadeia de custódia, a análise não vale. Aquisição, hash e registro vêm antes de qualquer ferramenta.",
    completion="Ficha de custódia preenchida, imagem adquirida com hash duplo e montagem somente leitura.",
)

m1 = mod(
    "artefatos-do-sistema",
    "Artefatos do sistema operacional",
    "Saber onde um sistema operacional registra o que aconteceu, e o que cada artefato prova.",
    ["registro do Windows", "artefatos Linux", "navegador", "documento", "docker"],
    [
        unit(
            "windows-e-linux",
            "Windows e Linux",
            "Ler os artefatos nativos de cada sistema com a ressalva correta.",
            ["chaves de registro", "eventos", "logs de sistema", "journal"],
            [
                act("for-m1-u1-kb-win", "theory", "Artefatos do Windows",
                    kb=WIN, minutes=50),
                act("for-m1-u1-kb-win-reg", "theory", "Chaves interessantes do registro do Windows",
                    kb=WIN_REG, minutes=45),
                act("for-m1-u1-kb-linux", "theory", "Forense em Linux",
                    kb=LIN, minutes=45),
                act("for-m1-u1-ex-journal", "exercises",
                    "Exercício: reconstruir uma sequência de eventos do próprio host",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Escolha uma ação que você fez hoje (instalar pacote, abrir serviço).\n"
                        "2. Localize o registro dela em **pelo menos duas** fontes: `journalctl`, "
                        "log de pacote ou log de autenticação.\n"
                        "3. Monte uma tabela com horário, fonte e o que cada uma prova.\n\n"
                        "Responda: qual das duas fontes é de **evento** e qual é de **metadado**? "
                        "Se a conclusão dependesse de uma só, qual você citaria no laudo?"
                    )),
            ],
        ),
        unit(
            "artefatos-de-aplicacao",
            "Artefatos de aplicação",
            "Extrair contexto de navegador, documento e container.",
            ["histórico de navegador", "metadados de documento", "camadas de container"],
            [
                act("for-m1-u2-kb-browser", "theory", "Artefatos do navegador",
                    kb=BROWSER, minutes=40),
                act("for-m1-u2-kb-office", "theory", "Análise de arquivos do Office",
                    kb=OFFICE, minutes=40),
                act("for-m1-u2-kb-pdf", "theory", "Análise de arquivo PDF",
                    kb=PDF, minutes=35),
                act("for-m1-u2-kb-docker", "theory", "Forense de Docker",
                    kb=DOCKER, minutes=40),
                act("for-m1-u2-ex-metadata", "exercises",
                    "Exercício: extrair metadados de um documento e interpretar",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Use um documento seu (PDF, DOCX ou imagem).\n\n"
                        "1. Extraia os metadados (`exiftool` ou equivalente).\n"
                        "2. Para cada campo, classifique: **autoria declarada**, **ferramenta**, "
                        "**data** ou **ruído**.\n"
                        "3. Responda: qual campo sustenta atribuição a uma pessoa? Justifique "
                        "por que os outros não sustentam.\n\n"
                        "Lembre que metadado pode ser herdado de outra ferramenta: atribua ao "
                        "**documento**, não à pessoa."
                    )),
            ],
        ),
    ],
    summary="Registro, logs, navegador, documentos e containers: onde cada sistema guarda o que fez.",
    prereq="principios",
    completion="Sequência de eventos do host reconstruída com duas fontes e metadados classificados.",
)

m2 = mod(
    "memoria-e-rede",
    "Memória e rede",
    "Analisar o único lugar onde processo, conexão e código injetado aparecem juntos — e o tráfego que sobrou.",
    ["dump de memória", "Volatility", "símbolos", "pcap", "exfiltração"],
    [
        unit(
            "memoria",
            "Forense de memória",
            "Interpretar um dump com os símbolos corretos e ordenar os plugins.",
            ["símbolos do kernel", "pslist vs psscan", "netscan", "malfind"],
            [
                act("for-m2-u1-own-memoria", "theory", "Forense de memória: símbolos, plugins e o que a RAM prova",
                    kb=MEM, minutes=55),
                act("for-m2-u1-kb-memdump", "theory", "Análise de dump de memória",
                    kb=VOL, minutes=45),
                act("for-m2-u1-kb-volcheat", "theory", "Volatility — folha de consulta",
                    kb=VOL_CHEAT, minutes=40),
                act("for-m2-u1-ex-simbolos", "exercises",
                    "Exercício: por que um dump sem símbolo não é análise",
                    minutes=40,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Não é preciso dump real.\n\n"
                        "1. Descreva, em passos, o que o Volatility faz ao executar "
                        "`windows.info`.\n"
                        "2. Explique o que acontece quando a tabela de símbolos do kernel "
                        "não está disponível.\n"
                        "3. Escreva as duas conclusões **erradas** que um analista tiraria "
                        "de uma saída vazia nesse caso.\n\n"
                        "Entregue uma frase de alerta pronta para colar no laudo: algo como "
                        "'sem símbolo carregado, ausência de resultado não indica ausência de "
                        "artefato'."
                    )),
                act("for-m2-u1-ex-pslist", "exercises",
                    "Exercício: comparar listagem e varredura de processo",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** No seu host (ou num dump, se tiver):\n\n"
                        "1. Obtenha a lista de processos por caminho 'oficial' (`ps`).\n"
                        "2. Obtenha por varredura direta de `/proc` ou de estruturas internas.\n"
                        "3. Identifique a diferença e explique cada uma com uma causa benigna.\n\n"
                        "Depois, escreva: qual é o **único** cenário em que a diferença vira "
                        "achado — e qual é a segunda evidência necessária para confirmar."
                    )),
            ],
        ),
        unit(
            "rede",
            "Tráfego de rede",
            "Ler pcap e ligar conexão a processo, sem atribuir além do que o registro mostra.",
            ["Wireshark", "filtros", "DNS como canal", "exfiltração"],
            [
                act("for-m2-u2-kb-pcap", "theory", "Inspeção de pcap",
                    kb=PCAP, minutes=45),
                act("for-m2-u2-kb-wireshark", "theory", "Truques do Wireshark",
                    kb=PCAP_WIRESHARK, minutes=40),
                act("for-m2-u2-kb-wifi-pcap", "theory", "Análise de pcap Wi-Fi",
                    kb=PCAP_WIFI, minutes=35),
                act("for-m2-u2-kb-dnscat", "theory", "Análise de pcap do DNSCat",
                    kb=PCAP_DNS, minutes=40),
                act("for-m2-u2-ex-captura", "exercises",
                    "Exercício: capturar o próprio tráfego e responder perguntas objetivas",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Precisa de `tcpdump`/Wireshark e de rede.\n\n"
                        "1. Capture 2 minutos do seu tráfego em `pcap`.\n"
                        "2. Responda com **filtro** (não com busca manual):\n"
                        "   - quantas conexões TCP foram abertas?\n"
                        "   - quais domínios foram consultados?\n"
                        "   - qual conexão transferiu mais bytes?\n"
                        "3. Anote cada filtro usado.\n\n"
                        "Entregue a captura, os filtros e as respostas. O filtro é a prova "
                        "de que a conclusão é reproduzível."
                    )),
            ],
        ),
    ],
    summary="Memória e rede: processo, conexão e exfiltração. Símbolo correto e filtro documentado.",
    prereq="artefatos-do-sistema",
    completion="Explicação do papel do símbolo, comparação de listagem e relatório de captura com filtros.",
)

m3 = mod(
    "timeline-e-antiforense",
    "Linha do tempo, anti-forense e raiz de confiança",
    "Montar a linha do tempo que sustenta a conclusão, reconhecer quem tenta apagá-la e proteger a evidência.",
    ["plaso", "Timesketch", "metadado vs evento", "anti-forense", "integridade de arquivo", "carving"],
    [
        unit(
            "timeline",
            "Linha do tempo",
            "Distinguir evento de metadado e montar a tabela que sustenta o laudo.",
            ["plaso", "Timesketch", "MACB", "fonte por evento"],
            [
                act("for-m3-u1-ex-timeline", "exercises",
                    "Exercício: montar linha do tempo com coluna de fonte",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Reúna eventos de duas fontes diferentes do seu host: um evento de "
                        "log e um metadado de arquivo (`stat`).\n"
                        "2. Monte uma tabela: `horário | fonte | evento | o que prova`.\n"
                        "3. Inclua **uma linha de metadado isolado** e marque como hipótese.\n"
                        "4. Escreva a conclusão que só a linha de evento sustenta.\n\n"
                        "Responda ainda: que ferramenta você usaria para gerar isso em escala, "
                        "e por que ela exige que você declare qual parser produziu cada evento?"
                    )),
                act("for-m3-u1-ex-plaso", "exercises",
                    "Exercício: gerar uma linha do tempo normalizada e inspecionar a fonte",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Precisa de `plaso` instalado (opcional: "
                        "Timesketch para visualizar).\n\n"
                        "1. Gere uma linha do tempo de um diretório de teste.\n"
                        "2. Escolha cinco eventos e identifique, para cada um, o **parser** "
                        "que os produziu.\n"
                        "3. Verifique se algum deles veio de metadado (MACB) e não de evento.\n\n"
                        "O ponto do exercício é que a timeline normaliza tudo para o mesmo "
                        "formato — e é por isso que o laudo precisa carregar a coluna de fonte."
                    )),
            ],
        ),
        unit(
            "anti-forense-e-raiz",
            "Anti-forense e raiz de confiança",
            "Reconhecer tentativa de apagar rastro e garantir que a evidência permaneça íntegra.",
            ["timestomping", "limpeza de log", "carving", "monitoramento de integridade"],
            [
                act("for-m3-u2-kb-anti", "theory", "Técnicas anti-forenses",
                    kb=ANTI, minutes=45),
                act("for-m3-u2-kb-fim", "theory", "Monitoramento de integridade de arquivos",
                    kb=FIM, minutes=40),
                act("for-m3-u2-kb-carving", "theory", "Partições, sistemas de arquivos e carving",
                    kb=CARVE, minutes=45),
                act("for-m3-u2-kb-carve-tools", "theory", "Ferramentas de carving e recuperação",
                    kb=CARVE_TOOLS, minutes=40),
                act("for-m3-u2-ex-carving", "exercises",
                    "Exercício: recuperar arquivo apagado de uma imagem sua",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Crie um arquivo de imagem com sistema de arquivos (`truncate` + "
                        "`mkfs`), monte-o, copie um arquivo com conteúdo reconhecível.\n"
                        "2. Apague o arquivo e desmonte.\n"
                        "3. Rode carving na imagem (`foremost`, `scalpel` ou equivalente).\n"
                        "4. Verifique se o arquivo voltou e se o conteúdo é íntegro (hash).\n\n"
                        "Responda: por que o hash do arquivo recuperado pode **não** bater "
                        "com o original, e como você declara isso no laudo."
                    )),
                act("for-m3-u2-assess", "assessment", "Avaliação: forense digital",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "Qual é a diferença entre linha do tempo de metadado e de evento?",
                         "accepted": ["metadado vem de mtime e é fácil de manipular",
                                      "evento vem de log do sistema e é mais difícil de forjar"],
                         "explanation": "Metadado (MACB) é trivial de alterar; evento vem de registro do próprio sistema e é a base de uma conclusão robusta."},
                        {"id": "q2", "prompt": "Por que a imagem de disco deve ser montada em somente leitura?",
                         "accepted": ["para não alterar a evidência", "para preservar o hash"],
                         "explanation": "Montagem em leitura/escrita altera a própria prova e invalida o hash de integridade."},
                        {"id": "q3", "prompt": "O que um dump de memória consegue provar que o disco não prova?",
                         "accepted": ["execução fileless", "processo executando sem arquivo", "código injetado em memória"],
                         "explanation": "A RAM guarda o código em execução e as conexões abertas, inclusive quando não há arquivo em disco."},
                        {"id": "q4", "prompt": "Por que 'não encontrei o arquivo na imagem' não prova que ele nunca existiu?",
                         "accepted": ["pode ter sido apagado e recuperável por carving", "a evidência pode ter sido sobrescrita"],
                         "explanation": "Arquivo apagado pode estar nos setores livres e ser recuperado por carving; a ausência na tabela do sistema de arquivos não é ausência dos dados."},
                    ]),
                act("for-m3-u2-project", "project",
                    "Capstone: laudo forense de um sistema próprio",
                    minutes=160,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "Alvo: um sistema ou uma imagem que **você** controla e criou, com "
                        "uma ação que você mesmo executou. Não use dado de terceiro.\n\n"
                        "Entregue:\n\n"
                        "1. Ficha de custódia com hashes.\n"
                        "2. Metodologia de aquisição (comando e opção de somente leitura).\n"
                        "3. Artefatos coletados, por fonte.\n"
                        "4. Linha do tempo com coluna de **fonte**.\n"
                        "5. Análise de pelo menos um artefato de memória **ou** de rede.\n"
                        "6. Um cenário anti-forense que você simulou (ex.: apagar arquivo e "
                        "recuperar por carving), com o resultado.\n"
                        "7. Conclusão e limitações explícitas.\n\n"
                        "Recusa: linha do tempo sem fonte por evento, hash de cópia apresentado "
                        "como o da original, conclusão sustentada apenas por `mtime`."
                    )),
            ],
        ),
    ],
    summary="Timeline com fonte, anti-forense, carving e a raiz de confiança que mantém a prova íntegra.",
    prereq="memoria-e-rede",
    completion="Linha do tempo com fonte, recuperação por carving e avaliação aprovada.",
)

path = {
    "slug": "digital-forensics",
    "title": "Forense Digital",
    "codename": "FOR",
    "domain": "forensics",
    "summary": "Custódia, aquisição, artefatos, memória, rede e linha do tempo: responder o que aconteceu de forma que o laudo se sustente.",
    "description": (
        "A trilha cobre forense de sistema, memória, rede e aplicação com o material "
        "importado sobre metodologia forense e dois documentos próprios: cadeia de "
        "custódia e análise de memória. O ponto central não é a ferramenta: é a separação "
        "entre fato observado e inferência, e a coluna de fonte que acompanha cada linha "
        "da linha do tempo. A plataforma não fornece imagem de disco nem dump de memória "
        "de terceiro — toda prática roda sobre o próprio sistema ou sobre material que o "
        "operador cria."
    ),
    "entry_level": "Linux e Windows básicos; linha de comando confortável",
    "exit_level": "capaz de conduzir uma coleta forense de ponta a ponta e emitir laudo com limitações",
    "estimated_hours": 32,
    "priority": 72,
    "phase": 3,
    "icon": "search",
    "accent": "violet",
    "prerequisites": ["linux-security", "network-pentesting"],
    "competencies": [
        "Montar cadeia de custódia e preservar hash de integridade",
        "Adquirir imagem sem alterar a prova",
        "Interpretar artefatos de Windows, Linux, navegador e container",
        "Explicar por que um dump de memória exige a tabela de símbolos correta",
        "Ligar conexão a processo com evidência documentada",
        "Distinguir linha do tempo de metadado de linha do tempo de evento",
        "Reconhecer e testar cenário de anti-forense",
    ],
    "tools": ["dd/dcfldd", "Volatility 3", "plaso", "Timesketch", "Wireshark", "tcpdump", "Sleuth Kit", "Autopsy", "foremost", "plaso/psort", "exiftool", "journalctl"],
    "equipment": (
        "Somente software: o operador usa o próprio host, imagens que ele mesmo cria e "
        "captura da própria rede. Nenhuma imagem de disco ou dump de terceiro é "
        "fornecido pela plataforma."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Conduzir uma coleta forense completa de um sistema próprio e emitir laudo com fontes, custódia e limitações.",
        "scope_md": (
            "Um sistema ou imagem que o próprio operador criou e controla. Nenhum dado de "
            "terceiro, nenhum sistema de produção alheio."
        ),
        "resources_md": (
            "Hipervisor ou máquina própria, ferramentas de aquisição e de imagem, "
            "Volatility 3, plaso/Timesketch, Wireshark/tcpdump, ferramento de carving. "
            "Todo o software é gratuito e já listado na trilha."
        ),
        "steps_md": (
            "1. Descrever escopo, pergunta e limite da coleta.\n"
            "2. Adquirir a imagem com hash calculado durante a aquisição.\n"
            "3. Montar a imagem em somente leitura e documentar o comando.\n"
            "4. Coletar artefatos por fonte (log, metadado, memória, pcap).\n"
            "5. Montar a linha do tempo com coluna de fonte por evento.\n"
            "6. Simular e apresentar um cenário anti-forense com resultado.\n"
            "7. Emitir conclusão e limitações."
        ),
        "success_criteria": [
            "Ficha de custódia completa com hash de original e de cópia",
            "Comando de aquisição reproduzível, com hash calculado na aquisição",
            "Montagem declarada como somente leitura",
            "Cada evento da linha do tempo com a fonte identificada",
            "Pelo menos um artefato de memória ou de rede analisado com método",
            "Cenário anti-forense executado e resultado interpretado",
            "Seção de limitações preenchida",
        ],
        "evidence": [
            "Ficha de custódia",
            "Comandos de aquisição e montagem",
            "Linha do tempo com fonte",
            "Saída da análise de memória ou de pcap",
            "Registro do cenário anti-forense",
            "Laudo final",
        ],
        "expected_result": "Laudo forense de um sistema próprio, com cadeia de custódia e limites explícitos.",
        "grading_md": "Custódia 25%, fidelidade do método 30%, linha do tempo e fontes 25%, limitações 20%.",
        "challenge_slug": "",
    },
}

emit("10-digital-forensics.json", path)