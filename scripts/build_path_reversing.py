#!/usr/bin/env python3
"""Generate content/learning_paths/14-reverse-engineering.json (Engenharia Reversa).

A base importada de reversing é menor que a de exploit, mas cobre o essencial:
ferramentas e métodos, angr, Z3, desofuscação de bytecode, anti-debug, macros e
macro de Office. Dois documentos próprios cobrem a lacuna que o audit apontou
(Ghidra e anti-depuração).

A prática usa binários do próprio sistema e binários que o operador compila —
nunca software proprietário de terceiro.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

GHIDRA = "own-ghidra-metodologia-reversing"
ANTIDEBUG = "own-reversing-anti-depuracao"
TOOLS = "ht-reversing-reversing-tools-basic-methods"
ANGR = TOOLS + "-angr"
ANGR_EX = TOOLS + "-angr-angr-examples"
Z3 = TOOLS + "-satisfiability-modulo-theories-smt-z3"
CHEAT = TOOLS + "-cheat-engine"
NODEV8 = TOOLS + "-nodejs-v8-cached-bytecode"
WINDBG = TOOLS + "-windbg-automation"
BLORB = TOOLS + "-blobrunner"
EXC = "ht-reversing-windows-exception-driven-control-flow"
WORD = "ht-reversing-word-macros"
API = "ht-reversing-common-api-used-in-malware"
STEGO = "ht-stego"
STEGO_IMG = "ht-stego-images"
STEGO_AUD = "ht-stego-audio"
STEGO_DOC = "ht-stego-documents"
STEGO_TXT = "ht-stego-text"
STEGO_WF = "ht-stego-workflow"
CTF_WF = "ht-crypto-ctf-workflow"
OFFICE = "ht-generic-methodologies-and-resources-basic-forensic-methodology-specific-software-file-type-tricks-of"

m0 = mod(
    "como-o-binario-e-construido",
    "Como o binário é construído",
    "Entender tradução de código para instrução e o vocabulário mínimo de assembly.",
    ["compilação", "assembly", "registrador", "convenção de chamada", "otimização"],
    [
        unit(
            "do-codigo-ao-binario",
            "Do código-fonte à instrução",
            "Reconhecer estruturas de alto nível decompiladas.",
            ["if/else", "laço", "switch", "inlining"],
            [
                act("rev-m0-u1-kb-tools", "theory", "Ferramentas de reversing e métodos básicos",
                    kb=TOOLS, minutes=50),
                act("rev-m0-u1-ex-assembly", "exercises",
                    "Exercício: compilar a mesma função com três níveis de otimização",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Escreva uma função com condição e laço. Compile três vezes: "
                        "`-O0`, `-O2` e `-Os`.\n\n"
                        "1. Desassemble as três versões.\n"
                        "2. Localize o laço e a condição em cada uma.\n"
                        "3. Responda: em qual versão o código é mais parecido com a fonte? "
                        "Em qual há menos instruções?\n\n"
                        "O ponto: a decompilação de binário otimizado **não** é a função "
                        "original. É uma reconstrução possível."
                    )),
                act("rev-m0-u1-ex-structs", "exercises",
                    "Exercício: recuperar estrutura de dados a partir do acesso a memória",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Compile um programa com uma estrutura de três campos (inteiro, "
                        "ponteiro, array pequeno).\n\n"
                        "1. Sem ver o código, desassemble uma função que acessa a estrutura.\n"
                        "2. Deduza o **layout**: ordem dos campos e tamanhos aparentes.\n"
                        "3. Recrie a estrutura e compare com a original.\n\n"
                        "Entregue a dedução e a comparação. Recuperar tipo a partir de acesso "
                        "é a habilidade central do reversing — mais do que ler o nome da função."
                    )),
            ],
        ),
    ],
    summary="Compilador, assembly e o que a otimização apaga. Sem isso, decompilação engana.",
    completion="Função desassembleada em três níveis e estrutura recuperada.",
)

m1 = mod(
    "ferramentas",
    "Ferramentas de análise estática",
    "Escolher o analisador pela pergunta e cruzar resultado entre ferramentas.",
    ["Ghidra", "radare2/rizin", "referências cruzadas", "símbolos"],
    [
        unit(
            "desassemblador",
            "Desassemblador e decompilador",
            "Navegar por string e referência cruzada, confirmando no assembly.",
            ["importação", "análise automática", "xref", "renomear", "tipos"],
            [
                act("rev-m1-u1-own-ghidra", "theory", "Ghidra: importar, achar a lógica e registrar o que se provou",
                    kb=GHIDRA, minutes=60),
                act("rev-m1-u1-ex-ghidra", "exercises",
                    "Exercício: encontrar a rotina de validação a partir da mensagem de erro",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Use um binário seu ou compilado para o exercício.\n\n"
                        "1. Compile um programa que pede senha e imprime mensagem de erro "
                        "quando errada.\n"
                        "2. No Ghidra, localize a string da mensagem.\n"
                        "3. Siga as referências cruzadas até a função que decide a resposta.\n"
                        "4. Confirme a comparação **no assembly**, não no pseudocódigo.\n\n"
                        "Entregue: endereço da função, a instrução da comparação e uma frase "
                        "dizendo o que ela realmente compara."
                    )),
                act("rev-m1-u1-ex-radare", "exercises",
                    "Exercício: verificação cruzada com um segundo desassemblador",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Use um segundo desassemblador (radare2, rizin ou equivalente) no "
                        "mesmo binário do exercício anterior.\n\n"
                        "1. Encontre a mesma função.\n"
                        "2. Compare o fluxo de controle que cada ferramenta reconhece.\n"
                        "3. Identifique qualquer diferença e explique-a.\n\n"
                        "Dois desassembladores concordando é o padrão mínimo de confiança. "
                        "Discrepância significa que pelo menos um perdeu referência — e o "
                        "assembly resolve."
                    )),
            ],
        ),
    ],
    summary="Ghidra, segundo desassemblador e verificação cruzada.",
    prereq="como-o-binario-e-construido",
    completion="Rotina de validação localizada com confirmação em assembly.",
)

m2 = mod(
    "analise-automatica-e-dinamica",
    "Análise automática e dinâmica",
    "Automatizar o que é repetitivo e observar o que a análise estática não mostra.",
    ["angr", "Z3", "depurador", "trace", "anti-debug"],
    [
        unit(
            "execucao-simbolica",
            "Execução simbólica e solvers",
            "Resolver caminho de entrada com ferramenta, entendendo o limite delas.",
            ["angr", "Z3", "restrição", "explosão de caminhos"],
            [
                act("rev-m2-u1-kb-angr", "theory", "Angr",
                    kb=ANGR, minutes=45),
                act("rev-m2-u1-kb-angr-ex", "theory", "Angr — exemplos",
                    kb=ANGR_EX, minutes=40),
                act("rev-m2-u1-kb-z3", "theory", "SMT e Z3",
                    kb=Z3, minutes=40),
                act("rev-m2-u1-ex-angr", "exercises",
                    "Exercício: resolver uma verificação simples com angr",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Compile um programa que compara a entrada com um valor calculado "
                        "(não uma string fixa).\n"
                        "2. Use angr para encontrar um caminho até a mensagem de sucesso, sem "
                        "resolver manualmente.\n"
                        "3. Confirme a entrada encontrada executando o binário.\n\n"
                        "Responda: por que execução simbólica funciona bem aqui e falha em "
                        "binário com criptografia por bloco? O que muda na sua estratégia?"
                    )),
            ],
        ),
        unit(
            "depurador-e-anti-analise",
            "Depurador e anti-análise",
            "Comparar comportamento com e sem depurador e contornar de forma registrada.",
            ["trace", "ponto de parada", "exceção", "detecção de ambiente"],
            [
                act("rev-m2-u2-own-antidebug", "theory", "Anti-depuração e anti-análise: reconhecer antes de contornar",
                    kb=ANTIDEBUG, minutes=55),
                act("rev-m2-u2-kb-exc", "theory", "Fluxo de controle baseado em exceções e anti-debug",
                    kb=EXC, minutes=45),
                act("rev-m2-u2-kb-windbg", "theory", "Automação do WinDbg para instrumentação direcionada",
                    kb=WINDBG, minutes=40),
                act("rev-m2-u2-kb-blobrunner", "theory", "Blobrunner",
                    kb=BLORB, minutes=30),
                act("rev-m2-u2-kb-api", "theory", "APIs comuns usadas em malware",
                    kb=API, minutes=40),
                act("rev-m2-u2-ex-comparar", "exercises",
                    "Exercício: comparar comportamento com e sem depurador",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Compile um programa que mede o tempo entre duas chamadas e imprime "
                        "mensagem diferente se o intervalo for grande.\n\n"
                        "1. Rode sem depurador e registre a saída.\n"
                        "2. Rode no depurador, pause entre as chamadas e registre a saída.\n"
                        "3. Identifique o endereço da checagem e contorne com ponto de parada "
                        "único.\n\n"
                        "Registre o contorno: onde, o que foi alterado e o efeito. Contorno "
                        "sem registro produz conclusão irreproduzível."
                    )),
            ],
        ),
    ],
    summary="angr, Z3, trace e anti-depuração. Automatizar o repetitivo e contornar com registro.",
    prereq="ferramentas",
    completion="Entrada resolvida por angr e contorno de anti-análise registrado.",
)

m3 = mod(
    "formatos-especificos",
    "Formatos específicos",
    "Aplicar o método a código não nativo: script, documento, bytecode e esteganografia.",
    ["macro", "VBS", "bytecode", "esteganografia"],
    [
        unit(
            "código-interpretado",
            "Código interpretado",
            "Ler script ofuscado e bytecode sem cair em armadilha.",
            ["macro VBA", "VBS", "JavaScript/V8", "ofuscação"],
            [
                act("rev-m3-u1-kb-word", "theory", "Macros do Word",
                    kb=WORD, minutes=45),
                act("rev-m3-u1-kb-office", "theory", "Análise de arquivos do Office",
                    kb=OFFICE, minutes=45),
                act("rev-m3-u1-kb-node", "theory", "Desofuscação estática de bytecode em cache do Node.js/V8",
                    kb=NODEV8, minutes=40),
                act("rev-m3-u1-kb-cheat", "theory", "Cheat Engine",
                    kb=CHEAT, minutes=35),
                act("rev-m3-u1-ex-macro", "exercises",
                    "Exercício: analisar uma macro passo a passo",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Use um documento seu com macro simples, criado "
                        "por você — nunca documento recebido de terceiro.\n\n"
                        "1. Extraia a macro do documento.\n"
                        "2. Identifique a primeira operação: leitura, escrita, download, "
                        "execução.\n"
                        "3. Descreva o que ela faz sem executá-la.\n"
                        "4. Simplifique a ofuscação manualmente e reescreva a versão legível.\n\n"
                        "Entregue a versão simplificada e a lista de chamadas perigosas. "
                        "Executar macro alheia é a forma mais comum de se infectar durante "
                        "análise."
                    )),
            ],
        ),
        unit(
            "esteganografia",
            "Esteganografia",
            "Encontrar dado escondido em mídia e declarar o método.",
            ["imagem", "áudio", "documento", "texto"],
            [
                act("rev-m3-u2-kb-stego", "theory", "Stego",
                    kb=STEGO, minutes=35),
                act("rev-m3-u2-kb-stego-img", "theory", "Esteganografia em imagens",
                    kb=STEGO_IMG, minutes=40),
                act("rev-m3-u2-kb-stego-aud", "theory", "Esteganografia de áudio",
                    kb=STEGO_AUD, minutes=35),
                act("rev-m3-u2-kb-stego-doc", "theory", "Esteganografia em documentos",
                    kb=STEGO_DOC, minutes=35),
                act("rev-m3-u2-kb-stego-txt", "theory", "Esteganografia de texto",
                    kb=STEGO_TXT, minutes=30),
                act("rev-m3-u2-kb-stego-wf", "theory", "Fluxo de Stego",
                    kb=STEGO_WF, minutes=30),
                act("rev-m3-u2-kb-ctf", "theory", "Fluxo de trabalho de Crypto CTF",
                    kb=CTF_WF, minutes=40),
                act("rev-m3-u2-ex-stego", "exercises",
                    "Exercício: esconder e recuperar dado numa imagem",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Esconda uma mensagem numa imagem com uma técnica (LSB ou equivalente).\n"
                        "2. Calcule o hash antes e depois.\n"
                        "3. Recupere a mensagem com outra ferramenta.\n"
                        "4. Responda: qual mudança visual a imagem sofreu?\n\n"
                        "Entregue a mensagem, os hashes e a resposta. O ponto de forense é "
                        "que a imagem 'parece normal' — o que sustenta o achado é o hash "
                        "diferente, não o olho."
                    )),
                act("rev-m3-u2-assess", "assessment", "Avaliação: engenharia reversa",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "Por que o pseudocódigo do decompilador não é a fonte original?",
                         "accepted": ["a otimização altera a estrutura", "é uma reconstrução possível"],
                         "explanation": "O compilador transforma a lógica; o decompilador reconstrói uma versão possível, não a original."},
                        {"id": "q2", "prompt": "O que a instrução de comparação no assembly confirma que o pseudocódigo não?",
                         "accepted": ["o valor exato comparado e o registro usado"],
                         "explanation": "O assembly mostra operandos e registrador exatos; o pseudocódigo é aproximação."},
                        {"id": "q3", "prompt": "Quando a execução simbólica falha?",
                         "accepted": ["com criptografia por bloco", "explosão de caminhos", "quando há muitas restrições"],
                         "explanation": "Caminhos que passam por criptografia por bloco geram restrições intratáveis para o solver."},
                        {"id": "q4", "prompt": "Por que dois desassembladores concordando é padrão mínimo de confiança?",
                         "accepted": ["discrepância indica falha de análise", "reduz erro de uma só ferramenta"],
                         "explanation": "Erro de uma ferramenta aparece como discrepância; a confirmação em assembly resolve."},
                    ]),
                act("rev-m3-u2-project", "project",
                    "Capstone: análise completa de um binário compilado por você",
                    minutes=170,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "1. Escreva um binário com lógica não trivial (validação, decodificação, "
                        "ou protocolo simples) e compile com `-O2`.\n"
                        "2. Entregue o binário **sem** o código-fonte a uma segunda análise "
                        "(a sua, do zero):\n\n"
                        "   - funções principais e ponto de entrada;\n"
                        "   - estrutura de dados recuperada;\n"
                        "   - rotina de validação localizada por referência cruzada;\n"
                        "   - alguma restrição resolvida por angr ou descrita;\n"
                        "   - um contorno de anti-análise, se você adicionou um.\n\n"
                        "3. Compare a reconstrução com o código original e liste o que você "
                        "errou ou não conseguiu.\n"
                        "4. Escreva as limitações.\n\n"
                        "O item 3 é o coração: analista que nunca confere a própria análise não "
                        "sabe qual é a taxa de erro dela."
                    )),
            ],
        ),
    ],
    summary="Macro, bytecode, esteganografia e a confissão de erro do capstone.",
    prereq="analise-automatica-e-dinamica",
    completion="Macro analisada sem execução, esteganografia demonstrada e avaliação aprovada.",
)

path = {
    "slug": "reverse-engineering",
    "title": "Engenharia Reversa",
    "codename": "REV",
    "domain": "reversing",
    "summary": "De assembly a angr: entender como o binário foi construído, localizar lógica por referência cruzada e converter análise em conclusão que se sustenta.",
    "description": (
        "A trilha ensina reversing como método e não como coleção de atalhos: como o "
        "compilador transforma código, como confirmar no assembly o que o decompilador "
        "sugere, quando automatizar com execução simbólica e quando evitar, como lidar "
        "com anti-depuração sem confundir com defeito, e como aplicar o mesmo método a "
        "macro, bytecode e esteganografia. A prática usa binário que o operador compila."
    ),
    "entry_level": "C ou Python confortável; conceitos de memória",
    "exit_level": "capaz de analisar um binário desconhecido e registrar conclusões com evidência",
    "estimated_hours": 36,
    "priority": 80,
    "phase": 3,
    "icon": "crosshair",
    "accent": "violet",
    "prerequisites": ["linux-security"],
    "competencies": [
        "Explicar o efeito da otimização na decompilação",
        "Localizar lógica por string e referência cruzada",
        "Confirmar conclusão em assembly em vez de pseudocódigo",
        "Decidir quando execução simbólica ajuda e quando falha",
        "Distinguir ofuscação de anti-análise de defeito",
        "Analisar macro e bytecode sem executá-los",
        "Reconhecer dado escondido em mídia e provar por hash",
    ],
    "tools": ["Ghidra", "radare2/rizin", "gdb", "angr", "Z3", "Detect It Easy", "capa", "exiftool", "binwalk", "oletools"],
    "equipment": "Somente software: ferramentas livres na máquina do operador; binários são compilados ou locais.",
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Analisar um binário sem o código-fonte e confrontar a reconstrução com a fonte original, medindo os próprios erros.",
        "scope_md": (
            "Binário compilado pelo próprio operador, analisado sem acesso à fonte até a "
            "reconstrução estar registrada."
        ),
        "resources_md": (
            "Ghidra, segundo desassemblador, gdb, angr (opcional), compilador. Todo o software "
            "é livre."
        ),
        "steps_md": (
            "1. Compilar o alvo com lógica não trivial e otimização.\n"
            "2. Registrar a reconstrução: funções, estruturas, validação e restrições.\n"
            "3. Resolver ou descrever ao menos uma restrição com ferramenta de análise.\n"
            "4. Contornar e registrar uma proteção anti-análise, se houver.\n"
            "5. Comparar com a fonte original e listar erros.\n"
            "6. Declarar limitações e taxa de acerto."
        ),
        "success_criteria": [
            "Reconstrução registrada antes de consultar a fonte",
            "Validação localizada com confirmação em assembly",
            "Estrutura de dados recuperada e comparada",
            "Pelo menos uma restrição resolvida ou explicada",
            "Confronto com a fonte com erros listados honestamente",
            "Limitações explícitas",
        ],
        "evidence": [
            "Binário e comando de compilação",
            "Notas de reconstrução",
            "Lista de erros do confronto",
            "Relatório final",
        ],
        "expected_result": "Reconstrução de binário com medição de erro conferida contra a fonte.",
        "grading_md": "Método 30%, fidelidade das conclusões 30%, confronto honesto 25%, limitações 15%.",
        "challenge_slug": "",
    },
}

emit("14-reverse-engineering.json", path)