#!/usr/bin/env python3
"""Generate content/learning_paths/12-mobile-security.json (Segurança Mobile).

A base importada cobre Android em profundidade (decompilação de APK, Frida,
Objection, Drozer, content providers, WebView, instrumentação) e iOS via
backup e binaries. A plataforma não oferece dispositivo nem emulador pronto:
toda prática é feita em AVD ou em app que o operador instale por conta própria.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

A = "ht-mobile-pentesting-android-app-pentesting"
BASICS = A + "-android-applications-basics"
ADB = A + "-adb-commands"
APK = A + "-apk-decompilers"
SMALI = A + "-smali-changes"
AVD = A + "-avd-android-virtual-device"
FRIDA = A + "-frida-tutorial"
OBJECTION = A + "-frida-tutorial-objection-tutorial"
DROZER = A + "-drozer-tutorial"
CONTENT = A + "-content-protocol"
CP = A + "-drozer-tutorial-exploiting-content-providers"
INTENT = A + "-intent-injection"
WEBVIEW = A + "-webview-attacks"
BURP = A + "-install-burp-certificate"
CA = A + "-make-apk-accept-ca-certificate"
PINNING = A + "-android-anti-instrumentation-and-ssl-pinning-bypass"
DEBUGGABLE = A + "-exploiting-a-debuggeable-applciation"
TASK = A + "-android-task-hijacking"
TAP = A + "-tapjacking"
BIO = A + "-bypass-biometric-authentication-android"
NATIVE = A + "-reversing-native-libraries"
MANUAL = A + "-manual-deobfuscation"
REACT = A + "-react-native-application"
FLUTTER = A + "-flutter"
INTEGRITY = A + "-play-integrity-attestation-bypass"
PHYSICAL = A + "-android-physical-attacks"
UNCRACK = A + "-frida-tutorial-owaspuncrackable-1"
IOS_BACKUP = "ht-generic-methodologies-and-resources-basic-forensic-methodology-ios-backup-forensics"

m0 = mod(
    "fundamentos-android",
    "Fundamentos de Android",
    "Entender o modelo de segurança do Android antes de procurar falha.",
    ["componentes", "permissões", "sandbox", "emulador"],
    [
        unit(
            "modelo",
            "Modelo de segurança",
            "Saber o que o sistema garante e o que o app precisa garantir.",
            ["manifest", "exported", "permissões", "UID por app"],
            [
                act("mob-m0-u1-kb-basics", "theory", "Noções básicas sobre aplicações Android",
                    kb=BASICS, minutes=50),
                act("mob-m0-u1-kb-adb", "theory", "Comandos ADB",
                    kb=ADB, minutes=40),
                act("mob-m0-u1-kb-avd", "theory", "AVD — Android Virtual Device",
                    kb=AVD, minutes=40),
                act("mob-m0-u1-ex-manifest", "exercises",
                    "Exercício: ler o manifesto e prever o que é alcançável",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Sem dispositivo: use um APK que você já tenha "
                        "(ou um app de código aberto que você baixe por conta própria).\n\n"
                        "1. Extraia o `AndroidManifest.xml` do APK.\n"
                        "2. Liste cada componente e seu atributo `exported`.\n"
                        "3. Para cada componente exportado, responda: quem pode chamá-lo?\n"
                        "4. Identifique as permissões declaradas e as realmente usadas.\n\n"
                        "Entregue a tabela. `exported=true` sem verificação de chamador é a "
                        "falha mais comum de app Android — e a mais fácil de detectar só "
                        "lendo o manifesto."
                    )),
            ],
        ),
    ],
    summary="Componentes, permissões e o sandbox por app. Antes de atacar, entender o modelo.",
    completion="Mapa de componentes exportados a partir do manifesto.",
)

m1 = mod(
    "analise-estatica",
    "Análise estática do APK",
    "Ler o app sem executá-lo e localizar o que não deveria estar exposto.",
    ["decompilação", "smali", "bibliotecas nativas", "ofuscação"],
    [
        unit(
            "decompilacao",
            "Decompilação",
            "Transformar o APK em código legível e navegar com objetivo.",
            ["dex", "smali", "JADX", "assets"],
            [
                act("mob-m1-u1-kb-apk", "theory", "Decompiladores de APK",
                    kb=APK, minutes=45),
                act("mob-m1-u1-kb-smali", "theory", "Smali — descompilando, modificando e compilando",
                    kb=SMALI, minutes=45),
                act("mob-m1-u1-ex-apk", "exercises",
                    "Exercício: procurar segredo e endpoint no APK",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. Descompile o APK (JADX ou `apktool`).\n"
                        "2. Procure por: URLs, chaves de API, nomes de bucket e strings de "
                        "autenticação.\n"
                        "3. Para cada achado, classifique: **hardcoded real**, **placeholder** "
                        "ou **ruído**.\n"
                        "4. Verifique se a string está também em `res/` ou em recurso "
                        "comprimido.\n\n"
                        "Entregue a lista com caminho do arquivo e linha. Segredo hardcoded sem "
                        "localização citável não é achado."
                    )),
            ],
        ),
        unit(
            "nativo-e-ofuscacao",
            "Código nativo e ofuscação",
            "Reconhecer onde a lógica saiu da linguagem gerenciada.",
            ["JNI", ".so", "obfuscação", "React Native", "Flutter"],
            [
                act("mob-m1-u2-kb-native", "theory", "Reversão de bibliotecas nativas",
                    kb=NATIVE, minutes=45),
                act("mob-m1-u2-kb-manual", "theory", "Técnicas de desofuscação manual",
                    kb=MANUAL, minutes=45),
                act("mob-m1-u2-kb-react", "theory", "Análise de aplicação React Native",
                    kb=REACT, minutes=40),
                act("mob-m1-u2-kb-flutter", "theory", "Flutter",
                    kb=FLUTTER, minutes=40),
                act("mob-m1-u2-ex-nativo", "exercises",
                    "Exercício: localizar a fronteira entre Java e nativo",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "1. No APK descompilado, liste as bibliotecas `.so`.\n"
                        "2. Identifique as chamadas `native` em Java/Kotlin.\n"
                        "3. Escolha uma e diga o que você precisaria fazer para analisá-la.\n\n"
                        "Responda: por que lógica movida para nativo **dificulta** mas não "
                        "**impede** a análise? Cite a técnica de análise estática que continua "
                        "válida no binário."
                    )),
            ],
        ),
    ],
    summary="Decompilação, smali, nativo e ofuscação. Ler o app como código.",
    prereq="fundamentos-android",
    completion="Lista de achados estáticos com localização e fronteira Java/nativo mapeada.",
)

m2 = mod(
    "analise-dinamica",
    "Análise dinâmica",
    "Instrumentar o app em execução e verificar o que ele faz na prática.",
    ["Frida", "Objection", "Drozer", "proxy de interceptação"],
    [
        unit(
            "instrumentacao",
            "Instrumentação",
            "Interceptar chamada e alterar comportamento sem reconstruir o APK.",
            ["Frida", "Objection", "hooks", "UnCrackable"],
            [
                act("mob-m2-u1-kb-frida", "theory", "Tutorial do Frida",
                    kb=FRIDA, minutes=50),
                act("mob-m2-u1-kb-objection", "theory", "Tutorial do Objection",
                    kb=OBJECTION, minutes=45),
                act("mob-m2-u1-ex-uncrackable", "exercises",
                    "Exercício: resolver o UnCrackable nível 1 num AVD",
                    minutes=70,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Precisa de AVD (emulador) e do app de treino "
                        "OWASP UnCrackable, que você baixa por conta própria. A plataforma não "
                        "distribui o APK.\n\n"
                        "1. Suba o AVD e instale o app.\n"
                        "2. Localize a verificação de senha em estático.\n"
                        "3. Use Frida para observar o valor comparado em tempo de execução.\n"
                        "4. Registre o comando usado e a saída.\n\n"
                        "Se não conseguir emular com a aceleração disponível na sua máquina, "
                        "entregue a análise estática da rotina de verificação e diga "
                        "explicitamente que o passo dinâmico ficou bloqueado — não invente "
                        "saída de terminal."
                    )),
            ],
        ),
        unit(
            "superficie-de-componentes",
            "Superfície de componentes",
            "Alcançar componentes expostos e medir o impacto.",
            ["Drozer", "content provider", "intent", "WebView"],
            [
                act("mob-m2-u2-kb-drozer", "theory", "Tutorial do Drozer",
                    kb=DROZER, minutes=45),
                act("mob-m2-u2-kb-content", "theory", "Content Protocol no Android",
                    kb=CONTENT, minutes=40),
                act("mob-m2-u2-kb-cp", "theory", "Explorando Content Providers",
                    kb=CP, minutes=40),
                act("mob-m2-u2-kb-intent", "theory", "Intent Injection",
                    kb=INTENT, minutes=40),
                act("mob-m2-u2-kb-webview", "theory", "Ataques a WebView",
                    kb=WEBVIEW, minutes=40),
                act("mob-m2-u2-kb-debuggable", "theory", "Explorando uma aplicação debuggable",
                    kb=DEBUGGABLE, minutes=35),
                act("mob-m2-u2-ex-inventory", "exercises",
                    "Exercício: inventariar componentes exportados e classificar risco",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Estático, funciona sem emulador.\n\n"
                        "Com o mapa de componentes do módulo 0:\n\n"
                        "1. Classifique cada exportado em: **informativo**, **ação sensível**, "
                        "**confiança implícita**.\n"
                        "2. Para cada ação sensível, escreva o cenário de abuso concreto.\n"
                        "3. Indique a evidência necessária para confirmar em execução.\n\n"
                        "Componente exportado sem cenário de abuso é ruído, não achado. O "
                        "relatório cresce com a segunda coluna, não com a primeira."
                    )),
            ],
        ),
    ],
    summary="Frida, Objection, Drozer e o abuso de componentes expostos.",
    prereq="analise-estatica",
    completion="Instrumentação documentada e inventário de componentes classificado por risco.",
)

m3 = mod(
    "transporte-e-protecoes",
    "Transporte, integridade e proteções evasivas",
    "Verificar o que protege a comunicação e o que é apenas dificuldade de análise.",
    ["certificado", "pinning", "biometria", "tapjacking", "attestation"],
    [
        unit(
            "transporte",
            "Transporte",
            "Distinguir pinning real de configuração frouxa e avaliar o que a rede vê.",
            ["proxy", "certificado de CA", "pinning", "anti-instrumentação"],
            [
                act("mob-m3-u1-kb-burp", "theory", "Instalar certificado do Burp",
                    kb=BURP, minutes=35),
                act("mob-m3-u1-kb-ca", "theory", "Fazer um APK confiar em certificado de CA do usuário",
                    kb=CA, minutes=40),
                act("mob-m3-u1-kb-pinning", "theory", "Anti-instrumentação e SSL pinning bypass",
                    kb=PINNING, minutes=50),
                act("mob-m3-u1-ex-transporte", "exercises",
                    "Exercício: escrever o teste de transporte em cinco passos",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Sem dispositivo obrigatório.\n\n"
                        "Escreva o procedimento para responder 'o app protege a comunicação?' "
                        "em cinco passos, com a evidência de **cada** passo:\n\n"
                        "1. Configurar proxy.\n"
                        "2. Aceitar o certificado de interceptação.\n"
                        "3. Observar a conexão.\n"
                        "4. Se falhar, determinar o motivo (pinning, pinning de CA, "
                        "anti-instrumentação).\n"
                        "5. Documentar o resultado.\n\n"
                        "Regra: 'não consegui interceptar' não é achado de segurança. O achado "
                        "é o mecanismo identificado e o fato de ele ser verificável."
                    )),
            ],
        ),
        unit(
            "protecoes",
            "Outras proteções",
            "Avaliar biometria, sobreposição e atestação como controles reais.",
            ["biometria", "tapjacking", "task hijacking", "Play Integrity"],
            [
                act("mob-m3-u2-kb-bio", "theory", "Bypass da autenticação biométrica (Android)",
                    kb=BIO, minutes=40),
                act("mob-m3-u2-kb-tap", "theory", "Tapjacking",
                    kb=TAP, minutes=30),
                act("mob-m3-u2-kb-task", "theory", "Task Hijacking no Android",
                    kb=TASK, minutes=30),
                act("mob-m3-u2-kb-integrity", "theory", "Bypass da atestação Play Integrity",
                    kb=INTEGRITY, minutes=45),
                act("mob-m3-u2-kb-ios", "theory", "Forense de backup do iOS",
                    kb=IOS_BACKUP, minutes=40),
                act("mob-m3-u2-kb-physical", "theory", "Ataques físicos ao Android",
                    kb=PHYSICAL, minutes=35),
                act("mob-m3-u2-assess", "assessment", "Avaliação: segurança mobile",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "O que `android:exported=\"true\"` significa para um componente?",
                         "accepted": ["outros apps podem chamá-lo", "qualquer app pode invocar"],
                         "explanation": "Exportado significa alcançável por outros apps; sem verificação de chamador, vira superfície de ataque."},
                        {"id": "q2", "prompt": "Por que segredo hardcoded no APK é sempre comprometido?",
                         "accepted": ["o APK é distribuído ao usuário", "o binário pode ser descompilado"],
                         "explanation": "O APK fica com o usuário, que pode descompilá-lo e extrair qualquer string."},
                        {"id": "q3", "prompt": "Pinning SSL impede a análise?",
                         "accepted": ["não", "nao", "dificulta mas não impede", "apenas dificulta"],
                         "explanation": "Pinning dificulta a interceptação, mas contorna-se com instrumentação; é obstáculo, não impossibilidade."},
                        {"id": "q4", "prompt": "Por que 'não consegui interceptar o tráfego' não é um achado?",
                         "accepted": ["falta identificar o mecanismo", "não localiza a proteção nem avalia a falha"],
                         "explanation": "O achado exige o mecanismo identificado e sua consequência; a falha de ferramenta não é prova de segurança."},
                    ]),
                act("mob-m3-u2-project", "project",
                    "Capstone: avaliação de um app",
                    minutes=150,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "Alvo: um APK que **você** escolheu e possui, e que pode analisar. Não "
                        "é alvo de terceiro sem autorização.\n\n"
                        "Entregue:\n\n"
                        "1. Mapa de componentes exportados.\n"
                        "2. Achados estáticos com localização (arquivo e linha).\n"
                        "3. Resultado da análise dinâmica (com o que ficou bloqueado declarado).\n"
                        "4. Avaliação de transporte: mecanismo identificado e evidência.\n"
                        "5. Proteções avaliadas: biometria, atestação, ofuscação.\n"
                        "6. Limitações e riscos priorizados.\n\n"
                        "Recusa: achado sem localização, 'não consegui' apresentado como 'é "
                        "seguro', ou relatório que descreve dispositivo que você não tem."
                    )),
            ],
        ),
    ],
    summary="Transporte, biometria, sobreposição e atestação: controles reais versus dificuldade.",
    prereq="analise-dinamica",
    completion="Procedimento de transporte, avaliação aprovada e proteções avaliadas.",
)

path = {
    "slug": "mobile-security",
    "title": "Segurança Mobile",
    "codename": "MOB",
    "domain": "mobile",
    "summary": "Android de ponta a ponta: manifesto, decompilação, instrumentação com Frida, componentes expostos, transporte e atestação.",
    "description": (
        "A trilha usa o acervo importado de Android, que é extenso e atual: componentes, "
        "Drozer, Frida, Objection, WebView, pinning, atestação e código nativo. A "
        "plataforma não distribui APK nem emulador configurado, e a trilha diz isso: a "
        "análise estática roda sobre qualquer APK que o operador possua, e os passos "
        "dinâmicos ficam marcados como bloqueados quando não há emulador utilizável. iOS "
        "entra pelo que a base cobre — forense de backup."
    ),
    "entry_level": "Linux e linha de comando; noções de Java",
    "exit_level": "capaz de avaliar um app Android completo e declarar o que ficou bloqueado",
    "estimated_hours": 30,
    "priority": 76,
    "phase": 3,
    "icon": "target",
    "accent": "green",
    "prerequisites": ["web-application-pentesting", "linux-security"],
    "competencies": [
        "Ler o manifesto e prever alcançabilidade de componentes",
        "Localizar segredo e endpoint no APK descompilado",
        "Instrumentar app com Frida e documentar o hook",
        "Inventariar componentes exportados e classificar risco",
        "Avaliar transporte distinguindo mecanismo de falha de ferramenta",
        "Reconhecer proteções evasivas e o que elas realmente garantem",
    ],
    "tools": ["jadx", "apktool", "Frida", "Objection", "Drozer", "adb", "Android Studio/AVD", "MobSF", "Burp Suite"],
    "equipment": (
        "Somente software, com ressalva: a análise estática roda na máquina do operador "
        "sem dispositivo. A análise dinâmica exige emulador (AVD) ou aparelho próprio, "
        "que a plataforma não fornece. Onde isso acontece, o exercício declara o limite e "
        "aceita a entrega estática como alternativa."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Produzir avaliação de um app Android com achados localizados, análise dinâmica declarada e riscos priorizados.",
        "scope_md": (
            "Um APK que o operador possui e pode analisar. Não é alvo de terceiro sem "
            "autorização escrita."
        ),
        "resources_md": (
            "jadx/apktool, adb, emulador (se disponível), Frida e Objection (para os passos "
            "dinâmicos), proxy de interceptação. Todos gratuitos."
        ),
        "steps_md": (
            "1. Mapear componentes a partir do manifesto.\n"
            "2. Descompilar e procurar segredo, endpoint e lógica sensível.\n"
            "3. Identificar a fronteira Java/nativo e o que fica bloqueado.\n"
            "4. Rodar análise dinâmica, ou declarar o bloqueio com o motivo.\n"
            "5. Testar transporte e identificar o mecanismo de proteção.\n"
            "6. Avaliar proteções evasivas e atestação.\n"
            "7. Priorizar riscos."
        ),
        "success_criteria": [
            "Cada componente exportado com cenário de abuso ou motivo de descarte",
            "Achado estático com arquivo e linha",
            "Hook documentado ou bloqueio declarado com causa",
            "Mecanismo de transporte identificado, não apenas 'não interceptei'",
            "Proteções avaliadas e classificadas como reais ou dificuldade",
            "Limitações explícitas",
        ],
        "evidence": [
            "Mapa de componentes",
            "Lista de achados estáticos localizados",
            "Log de instrumentação ou registro de bloqueio",
            "Relatório de transporte",
            "Relatório final priorizado",
        ],
        "expected_result": "Avaliação de app Android com achados reproduzíveis e limites declarados.",
        "grading_md": "Fidelidade técnica 35%, localização das evidências 25%, análise dinâmica 20%, honestidade de limites 20%.",
        "challenge_slug": "",
    },
}

emit("12-mobile-security.json", path)