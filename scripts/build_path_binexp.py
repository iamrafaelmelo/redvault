#!/usr/bin/env python3
"""Generate content/learning_paths/13-binary-exploitation.json (Exploit Development).

A base importada sobre corrupção de memória é a mais completa do acervo:
pilha, heap (bins, tcache, unlink, house of *), proteções e bypasses, shellcode.
A trilha organiza esse material em progressão de dificuldade e acrescenta um
documento próprio sobre leitura de proteções.

Limite declarado: a plataforma não tem laboratório de pwn. Todo exercício usa
binário que o operador compila na própria máquina — o que é, na prática, o
ambiente padrão de treino de exploit.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

B = "ht-binary-exploitation"
PROT = B + "-common-binary-protections-and-bypasses"
PROT_OWN = "own-binario-protecoes-e-bypass"
NX = PROT + "-no-exec-nx"
CANARY = PROT + "-stack-canaries"
CANARY_PRINT = PROT + "-stack-canaries-print-stack-canary"
CANARY_BF = PROT + "-stack-canaries-bf-forked-stack-canaries"
PIE = PROT + "-pie"
ASLR = PROT + "-aslr"
RET2PLT = PROT + "-aslr-ret2plt"
RET2RET = PROT + "-aslr-ret2ret"
RELRO = PROT + "-relro"
PROT_LIBC = PROT + "-libc-protections"
CET = PROT + "-cet-and-shadow-stack"
STACK = B + "-stack-overflow"
RET2WIN = STACK + "-ret2win"
SHELLCODE = STACK + "-stack-shellcode"
PIVOT = STACK + "-stack-pivoting"
PTR = STACK + "-pointer-redirecting"
HEAP = B + "-libc-heap"
HEAP_BINS = HEAP + "-bins-and-memory-allocations"
HEAP_FUNCS = HEAP + "-heap-memory-functions"
HEAP_CHECKS = HEAP + "-heap-memory-functions-heap-functions-security-checks"
HEAP_FREE = HEAP + "-heap-memory-functions-free"
UAF = HEAP + "-use-after-free"
DOUBLE_FREE = HEAP + "-double-free"
TCACHE = HEAP + "-tcache-bin-attack"
FASTBIN = HEAP + "-fast-bin-attack"
UNSORTED = HEAP + "-unsorted-bin-attack"
LSB = HEAP + "-large-bin-attack"
OVERLAP = HEAP + "-overwriting-a-freed-chunk"
OFFBYONE = HEAP + "-off-by-one-overflow"
AW2E = B + "-arbitrary-write-2-exec"
GOTPLT = AW2E + "-aw2exec-got-plt"
HOOKS = AW2E + "-aw2exec-malloc-hook"
DTORS = AW2E + "-www2exec-dtors-and-fini-array"
METHOD = B + "-basic-stack-binary-exploitation-methodology"
ELF = METHOD + "-elf-tricks"
TOOLS = METHOD + "-tools"
PWNTOOLS = TOOLS + "-pwntools"

m0 = mod(
    "fundamentos",
    "Fundamentos de memória e ferramentas",
    "Entender o modelo de memória de um processo e montar o ambiente de treino.",
    ["pilha", "heap", "ELF", "gdb", "pwntools"],
    [
        unit(
            "memoria-e-elf",
            "Memória e ELF",
            "Saber onde cada coisa mora antes de corromper.",
            ["segmentos", "pilha", "registrador", "convenção de chamada"],
            [
                act("bex-m0-u1-kb-method", "theory", "Metodologia básica de exploração de binários",
                    kb=METHOD, minutes=50),
                act("bex-m0-u1-kb-elf", "theory", "Informações básicas sobre ELF",
                    kb=ELF, minutes=45),
                act("bex-m0-u1-ex-pilha", "exercises",
                    "Exercício: desenhar a pilha de uma chamada de função",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Compile na sua máquina.\n\n"
                        "1. Escreva uma função com dois parâmetros e uma variável local. "
                        "Compile com `-O0 -g`.\n"
                        "2. No gdb, pare na função e imprima: registrador de pilha, endereço "
                        "dos parâmetros, endereço da variável local e endereço de retorno.\n"
                        "3. Desenhe o mapa da pilha com os endereços reais.\n\n"
                        "Entregue o desenho e o comando usado para obter cada endereço. "
                        "Exploit sem mapa de pilha é chute."
                    )),
            ],
        ),
        unit(
            "ferramentas",
            "Ferramentas",
            "Usar depurador e biblioteca de exploit com método.",
            ["gdb", "pwndbg", "pwntools", "checksec"],
            [
                act("bex-m0-u2-kb-tools", "theory", "Ferramentas de exploração",
                    kb=TOOLS, minutes=40),
                act("bex-m0-u2-kb-pwntools", "theory", "Pwntools",
                    kb=PWNTOOLS, minutes=45),
                act("bex-m0-u2-ex-pwntools", "exercises",
                    "Exercício: script de interação com processo",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Escreva um script pwntools que:\n\n"
                        "1. Abre um binário seu em modo local.\n"
                        "2. Lê a primeira linha de saída.\n"
                        "3. Envia entrada e recebe a resposta.\n"
                        "4. Imprime o valor do registro de pilha depois da entrada.\n\n"
                        "O objetivo não é o exploit: é ter um harness reproduzível. Todo "
                        "exploit posterior usa este mesmo esqueleto."
                    )),
            ],
        ),
    ],
    summary="Pilha, heap, ELF, gdb e pwntools antes de qualquer corrupção.",
    completion="Mapa de pilha desenhado e harness de pwntools funcionando.",
)

m1 = mod(
    "exploracao-de-pilha",
    "Exploração de pilha",
    "Explorar corrupção de pilha em progressão: sem proteção, com NX e com canário.",
    ["overflow", "ret2win", "ret2plt", "canário", "shellcode"],
    [
        unit(
            "protecoes",
            "Ler as proteções",
            "Saber qual técnica aquele binário permite.",
            ["NX", "canário", "PIE", "ASLR", "RELRO", "CET"],
            [
                act("bex-m1-u1-own-protecoes", "theory", "Proteções de binário: ler o que está ligado antes de procurar o que explorar",
                    kb=PROT_OWN, minutes=55),
                act("bex-m1-u1-kb-prots", "theory", "Proteções e bypasses comuns",
                    kb=PROT, minutes=45),
                act("bex-m1-u1-kb-nx", "theory", "No-exec / NX",
                    kb=NX, minutes=35),
                act("bex-m1-u1-kb-pie", "theory", "PIE",
                    kb=PIE, minutes=35),
                act("bex-m1-u1-kb-aslr", "theory", "ASLR",
                    kb=ASLR, minutes=40),
                act("bex-m1-u1-kb-relro", "theory", "RELRO",
                    kb=RELRO, minutes=35),
                act("bex-m1-u1-kb-cet", "theory", "CET e Shadow Stack",
                    kb=CET, minutes=40),
                act("bex-m1-u1-kb-libcprot", "theory", "Proteções do libc",
                    kb=PROT_LIBC, minutes=35),
            ],
        ),
        unit(
            "primeiros-exploits",
            "Primeiros exploits",
            "Do overflow simples à reorientação de chamada.",
            ["offset", "ret2win", "shellcode", "stack pivoting"],
            [
                act("bex-m1-u2-kb-overflow", "theory", "Stack Overflow",
                    kb=STACK, minutes=45),
                act("bex-m1-u2-kb-ret2win", "theory", "Ret2win",
                    kb=RET2WIN, minutes=40),
                act("bex-m1-u2-kb-shellcode", "theory", "Stack Shellcode",
                    kb=SHELLCODE, minutes=40),
                act("bex-m1-u2-kb-pivot", "theory", "Stack Pivoting",
                    kb=PIVOT, minutes=40),
                act("bex-m1-u2-ex-offset", "exercises",
                    "Exercício: encontrar o offset do endereço de retorno",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Compile um programa com `gets`/`strcpy` num buffer pequeno, sem "
                        "proteções (`-fno-stack-protector -no-pie -z execstack`).\n\n"
                        "1. Encontre o offset com um padrão cíclico (técnica de padrão "
                        "de Bruijn).\n"
                        "2. Confirme no gdb com o valor que caiu no registro de instrução.\n"
                        "3. Redirecione para uma função existente que você adicionou "
                        "intencionalmente (ret2win).\n\n"
                        "Entregue o offset, o comprovante do gdb e o script. O comprovante "
                        "é o que separa exploit de cópia."
                    )),
                act("bex-m1-u2-ex-ret2plt", "exercises",
                    "Exercício: ret2plt com NX ligado",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Compile o mesmo programa com NX ligado (`-z noexecstack`).\n"
                        "2. Confirme que o shellcode na pilha falha.\n"
                        "3. Reoriente a execução para a PLT de uma função já importada.\n\n"
                        "Responda: por que o ataque deixa de ser 'executar bytes' e passa a "
                        "ser 'encadear chamadas'? Cite a proteção que obriga a mudança."
                    )),
            ],
        ),
        unit(
            "canario",
            "Canário e vazamento",
            "Lidar com verificação de integridade da pilha.",
            ["vazamento", "brute-force", "fork", "leak"],
            [
                act("bex-m1-u3-kb-canary", "theory", "Stack Canaries",
                    kb=CANARY, minutes=40),
                act("bex-m1-u3-kb-canary-print", "theory", "Print Stack Canary",
                    kb=CANARY_PRINT, minutes=35),
                act("bex-m1-u3-kb-canary-bf", "theory", "BF Forked & Threaded Stack Canaries",
                    kb=CANARY_BF, minutes=35),
                act("bex-m1-u3-ex-canary", "exercises",
                    "Exercício: vazar o canário antes de escrever",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Compile o programa com `-fstack-protector-all`.\n"
                        "2. Mostre a verificação no código descompilado.\n"
                        "3. Use uma primitiva de leitura para obter o canário.\n"
                        "4. Monte a payload: canário correto + endereço de retorno.\n\n"
                        "Responda: o que acontece se o canário for sobrescrito com valor "
                        "errado, e qual é a única forma de contornar isso sem vazamento "
                        "(cite o cenário de processo com fork)."
                    )),
            ],
        ),
    ],
    summary="Overflow, ret2win, NX, ret2plt, canário e vazamento — em progressão medida.",
    prereq="fundamentos",
    completion="Pilha sem proteção explorada, ret2plt com NX e canário vazado.",
)

m2 = mod(
    "heap-e-escrita-arbitraria",
    "Heap e escrita arbitrária",
    "Explorar estado de heap e converter escrita em execução.",
    ["bins", "tcache", "use-after-free", "GOT", "hooks"],
    [
        unit(
            "heap",
            "Modelo de heap",
            "Entender alocação e liberação antes de corromper.",
            ["chunk", "bin", "tcache", "metadata"],
            [
                act("bex-m2-u1-kb-heap", "theory", "Heap da libc",
                    kb=HEAP, minutes=45),
                act("bex-m2-u1-kb-bins", "theory", "Bins e alocações de memória",
                    kb=HEAP_BINS, minutes=45),
                act("bex-m2-u1-kb-funcs", "theory", "Funções de memória do heap",
                    kb=HEAP_FUNCS, minutes=45),
                act("bex-m2-u1-kb-checks", "theory", "Verificações de segurança das funções de heap",
                    kb=HEAP_CHECKS, minutes=40),
                act("bex-m2-u1-kb-free", "theory", "free",
                    kb=HEAP_FREE, minutes=35),
                act("bex-m2-u1-ex-chunks", "exercises",
                    "Exercício: desenhar chunks antes e depois de free",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Escreva programa que aloca três chunks de tamanhos diferentes e "
                        "libera dois.\n"
                        "2. No gdb (com extensão de heap), inspecione o cabeçalho de cada chunk.\n"
                        "3. Desenhe o estado: tamanho, flags, ponteiro de lista.\n"
                        "4. Repita com um chunk maior (sai do tcache) e compare.\n\n"
                        "Entregue os dois desenhos. Toda exploração de heap começa por saber "
                        "em qual bin o chunk caiu."
                    )),
            ],
        ),
        unit(
            "vetores",
            "Vetores clássicos",
            "Reconhecer cada padrão de falha de heap pelo nome.",
            ["UAF", "double free", "tcache", "fastbin", "unsorted", "overlap"],
            [
                act("bex-m2-u2-kb-uaf", "theory", "Use-After-Free",
                    kb=UAF, minutes=40),
                act("bex-m2-u2-kb-double", "theory", "Double Free",
                    kb=DOUBLE_FREE, minutes=40),
                act("bex-m2-u2-kb-tcache", "theory", "Tcache Bin Attack",
                    kb=TCACHE, minutes=40),
                act("bex-m2-u2-kb-fastbin", "theory", "Fast Bin Attack",
                    kb=FASTBIN, minutes=40),
                act("bex-m2-u2-kb-unsorted", "theory", "Unsorted Bin Attack",
                    kb=UNSORTED, minutes=40),
                act("bex-m2-u2-kb-lsb", "theory", "Large Bin Attack",
                    kb=LSB, minutes=40),
                act("bex-m2-u2-kb-overlap", "theory", "Sobrescrevendo um chunk liberado",
                    kb=OVERLAP, minutes=35),
                act("bex-m2-u2-kb-offbyone", "theory", "Off-by-one overflow",
                    kb=OFFBYONE, minutes=35),
                act("bex-m2-u2-ex-uaf", "exercises",
                    "Exercício: demonstrar UAF controlado",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Escreva programa que aloca um objeto, libera e **continua usando** "
                        "o ponteiro.\n"
                        "2. Mostre no gdb que o ponteiro ainda aponta para memória válida.\n"
                        "3. Demonstre que um novo chunk alocado do mesmo tamanho ocupa o local.\n\n"
                        "Entregue a saída que prova a sobreposição. Este é o mecanismo por trás "
                        "de quase toda exploração de heap moderna."
                    )),
            ],
        ),
        unit(
            "escrita-em-execucao",
            "De escrita a execução",
            "Converter escrita arbitrária em execução.",
            ["GOT/PLT", "hooks", ".fini_array", "ponteiro de função"],
            [
                act("bex-m2-u3-kb-aw2e", "theory", "Escrita arbitrária para execução de código",
                    kb=AW2E, minutes=45),
                act("bex-m2-u3-kb-got", "theory", "WWW2Exec — GOT/PLT",
                    kb=GOTPLT, minutes=40),
                act("bex-m2-u3-kb-hooks", "theory", "WWW2Exec — __malloc_hook e __free_hook",
                    kb=HOOKS, minutes=40),
                act("bex-m2-u3-kb-dtors", "theory", "WWW2Exec — .dtors e .fini_array",
                    kb=DTORS, minutes=35),
                act("bex-m2-u3-kb-ptr", "theory", "Redirecionamento de ponteiros",
                    kb=PTR, minutes=40),
            ],
        ),
    ],
    summary="Bins, tcache, UAF e a ponte entre escrita arbitrária e execução.",
    prereq="exploracao-de-pilha",
    completion="Estado de heap desenhado, UAF demonstrado e vetores de escrita mapeados.",
)

m3 = mod(
    "metodologia-e-prova",
    "Metodologia, reprodutibilidade e prova",
    "Transformar exploit em resultado reproduzível e defensável.",
    ["reprodutibilidade", "libc", "reversão de proteção", "relatório"],
    [
        unit(
            "reprodutibilidade",
            "Reprodutibilidade",
            "Garantir que o exploit funciona onde deve funcionar.",
            ["versão de libc", "patchelf", "offsets", "ASLR"],
            [
                act("bex-m3-u1-kb-ret2ret", "theory", "Ret2ret & Ret2pop",
                    kb=RET2RET, minutes=35),
                act("bex-m3-u1-ex-libc", "exercises",
                    "Exercício: provar dependência de versão de libc",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Pegue um exploit do módulo 2 que usa endereço de função de libc.\n"
                        "2. Rode com a libc do sistema.\n"
                        "3. Troque a libc por outra versão (via `patchelf` ou ambiente "
                        "equivalente) e rode de novo.\n\n"
                        "1. O exploit funcionou das duas vezes?\n"
                        "2. Qual offset mudou?\n"
                        "3. Como você declara isso num relatório de exploração?\n\n"
                        "Um exploit sem versão de libc declarada é um resultado que não se "
                        "reproduz — e essa é a primeira pergunta que alguém faz ao ler."
                    )),
                act("bex-m3-u1-ex-aslr", "exercises",
                    "Exercício: medir o efeito do ASLR",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Rode o mesmo binário 10 vezes e registre o endereço de uma "
                        "biblioteca em cada execução.\n"
                        "2. Repita com ASLR desligado.\n"
                        "3. Calcule a variação.\n\n"
                        "Responda: por que uma única execução que 'funcionou' **não** prova que "
                        "o exploit é estável? Quantas execuções você considera mínimas para "
                        "declarar estabilidade?"
                    )),
            ],
        ),
        unit(
            "entrega",
            "Entrega",
            "Escrever a análise que sustenta o exploit.",
            ["relatório", "criticidade", "framing", "correção"],
            [
                act("bex-m3-u2-ex-relatorio", "exercises",
                    "Exercício: relatório de exploração com contexto de correção",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Escreva o relatório do exploit do capstone, contendo:\n\n"
                        "1. Alvo (binário, hash, libc, versão de toolchain).\n"
                        "2. Proteções lidas, com **como** foram lidas.\n"
                        "3. Falha: tipo, função, endereço.\n"
                        "4. Técnica em uma frase.\n"
                        "5. Estabilidade medida (execuções e taxa).\n"
                        "6. Impacto realista.\n"
                        "7. Correção mínima e por que ela resolve.\n\n"
                        "O item 6 é o mais mal escrito habitualmente: 'RCE' não é impacto "
                        "sem dizer sobre qual contexto de privilégio."
                    )),
                act("bex-m3-u2-project", "project",
                    "Capstone: exploit reproduzível com técnica justificada",
                    minutes=180,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "Escolha um conjunto de proteções (por exemplo: NX + canário + PIE "
                        "+ RELRO completo) e escreva o binário com uma falha de pilha ou heap.\n\n"
                        "Entregue:\n\n"
                        "1. Código-fonte e comando de compilação.\n"
                        "2. Inventário de proteções com o método usado.\n"
                        "3. Justificativa da técnica escolhida **em função** das proteções.\n"
                        "4. Offset confirmado no depurador.\n"
                        "5. Script de exploit com saída controlada.\n"
                        "6. Tabela de estabilidade (execuções e taxa).\n"
                        "7. Libc/toolchain e correção mínima.\n\n"
                        "Recusa: offset copiado sem comprovação, exploit que só funciona uma "
                        "vez, ou relatório que afirma 'RCE' sem dizer o contexto de privilégio."
                    )),
                act("bex-m3-u2-assess", "assessment", "Avaliação: exploit development",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "O que NX impede?",
                         "accepted": ["executar código na pilha ou no heap", "execução de dados na pilha"],
                         "explanation": "NX marca a pilha e o heap como não executáveis, obrigando a reorientar para código já mapeado."},
                        {"id": "q2", "prompt": "Qual teste distingue PIE de ASLR?",
                         "accepted": ["pie é do binário e aslr do sistema"],
                         "explanation": "PIE é propriedade do executável; ASLR é comportamento do sistema. Um binário sem PIE ainda tem ASLR nas bibliotecas."},
                        {"id": "q3", "prompt": "Por que um exploit com offset de libc fixo falha em outro host?",
                         "accepted": ["a versão de libc muda os offsets"],
                         "explanation": "Endereços e offsets de funções mudam entre versões de libc; o exploit precisa declarar a versão."},
                        {"id": "q4", "prompt": "O que caracteriza Use-After-Free?",
                         "accepted": ["usar ponteiro depois de liberar", "memória liberada e reutilizada"],
                         "explanation": "O programa continua usando um ponteiro cujo objeto já foi liberado; a memória pode ser realocada e controlada."},
                    ]),
            ],
        ),
    ],
    summary="Versionamento de libc, estabilidade e o relatório que sustenta a exploração.",
    prereq="heap-e-escrita-arbitraria",
    completion="Dependência de libc demonstrada, ASLR medido e avaliação aprovada.",
)

path = {
    "slug": "binary-exploitation",
    "title": "Exploit Development",
    "codename": "BEX",
    "domain": "binexp",
    "summary": "Corrupção de memória do início ao fim: pilha, canário, heap, bins e escrita arbitrária — sempre com leitura de proteções e reprodutibilidade declarada.",
    "description": (
        "A trilha usa o acervo mais profundo da base importada sobre corrupção de memória "
        "e acrescenta um documento próprio sobre leitura de proteções. A progressão é "
        "deliberada: overflow sem proteção, ret2win, NX e ret2plt, canário com vazamento, "
        "heap com bins e tcache, e a conversão de escrita arbitrária em execução. A "
        "plataforma não tem laboratório de pwn: todo exercício compila o próprio binário, "
        "que é o ambiente padrão de treino e não exige nada além do compilador."
    ),
    "entry_level": "C e assembly básicos; Linux com gdb",
    "exit_level": "capaz de ler as proteções de um binário, explorar falha de pilha ou heap reproduzível e documentar o resultado",
    "estimated_hours": 44,
    "priority": 78,
    "phase": 3,
    "icon": "code",
    "accent": "red",
    "prerequisites": ["linux-security"],
    "competencies": [
        "Ler proteções e dizer qual técnica elas permitem ou bloqueiam",
        "Encontrar offset e reorientar execução de pilha",
        "Vazar canário e montar payload correto",
        "Explicar o modelo de heap e o bin onde um chunk caiu",
        "Demonstrar Use-After-Free controlado",
        "Converter escrita arbitrária em execução",
        "Declarar versão de libc e estabilidade do exploit",
    ],
    "tools": ["gdb", "pwndbg", "pwntools", "ROPgadget", "patchelf", "checksec", "how2heap", "gcc"],
    "equipment": (
        "Somente software: compilador e depurador na máquina do operador. Não há "
        "laboratório remoto de pwn nem alvo fornecido pela plataforma."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Explorar uma falha de memória em binário compilado pelo operador, com técnica escolhida pelas proteções e resultado reproduzível.",
        "scope_md": (
            "Binário escrito e compilado pelo próprio operador. Nenhum binário de terceiro, "
            "nenhum serviço de terceiro."
        ),
        "resources_md": (
            "gcc, gdb/pwndbg, pwntools, ROPgadget, patchelf. Todo o software é livre e já "
            "está listado na trilha."
        ),
        "steps_md": (
            "1. Escrever o binário com a falha e compilar com o conjunto de proteções escolhido.\n"
            "2. Inventariar as proteções e justificar a técnica.\n"
            "3. Encontrar o offset e validar no depurador.\n"
            "4. Construir a payload e obter execução controlada.\n"
            "5. Medir estabilidade em execuções repetidas.\n"
            "6. Declarar libc, versão de toolchain e correção mínima."
        ),
        "success_criteria": [
            "Proteções listadas com o método de leitura",
            "Técnica compatível com as proteções identificadas",
            "Offset confirmado no depurador, não copiado",
            "Execução controlada demonstrada",
            "Estabilidade medida com número de execuções",
            "Libc e toolchain declaradas",
            "Correção mínima proposta e justificada",
        ],
        "evidence": [
            "Código-fonte do binário e comando de compilação",
            "Saída do inventário de proteções",
            "Prova de offset no depurador",
            "Script do exploit e saída",
            "Tabela de estabilidade",
            "Relatório final",
        ],
        "expected_result": "Exploit reproduzível em binário próprio, com técnica justificada pelas proteções.",
        "grading_md": "Justificativa técnica 30%, exploit funcionando 35%, reprodutibilidade 20%, relatório 15%.",
        "challenge_slug": "",
    },
}

emit("13-binary-exploitation.json", path)