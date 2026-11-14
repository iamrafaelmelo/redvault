#!/usr/bin/env python3
"""Generate content/learning_paths/11-cloud-containers.json (Cloud e Containers).

A base importada cobre AWS, Azure, Kubernetes e Docker via PayloadsAllTheThings
e o HackTricks de containers. Duas lacunas são declaradas como gap e cobertas por
documento próprio: IAM (avaliação de política e RBAC) e serverless.

Limite honesto: a plataforma não tem conta em nuvem. Todo exercício é análise
documental, modelagem de política ou prática local com Docker. Nada aqui exige
criar conta ou provisionar recurso pago.
"""
from __future__ import annotations

from lp_phase3 import emit
from lp_builders import act, mod, unit

AWS = "patt-methodology-and-resources-cloud-aws-pentest"
AZURE = "patt-methodology-and-resources-cloud-azure-pentest"
K8S = "patt-methodology-and-resources-container-kubernetes-pentest"
DOCKER_P = "patt-methodology-and-resources-container-docker-pentest"
DOCKER2375 = "ht-network-services-pentesting-2375-pentesting-docker"
REGISTRY = "ht-network-services-pentesting-5000-pentesting-docker-registry"
NS = "ht-linux-hardening-containers-namespaces"
NS_SEC = "ht-linux-hardening-containers-namespaces-container-security"
NS_PRIV = "ht-linux-hardening-containers-namespaces-container-security-privileged-containers"
NS_CAP = "ht-linux-hardening-containers-namespaces-container-security-protections-capabilities"
NS_PROT = "ht-linux-hardening-containers-namespaces-container-security-protections"
NS_DISTROLESS = "ht-linux-hardening-containers-namespaces-container-security-distroless"
CTR = "ht-linux-hardening-containers-namespaces-containerd-ctr-privilege-escalation"
SSRF_CLOUD = "ht-pentesting-web-ssrf-server-side-request-forgery-cloud-ssrf"
SSRF_INST = "patt-server-side-request-forgery-ssrf-cloud-instances"
META_LINUX = "ht-linux-hardening-post-exploitation-cloud-instance-metadata"
IAM = "own-cloud-iam-permissoes"
SERVERLESS = "own-cloud-serverless-riscos"
BUCKETS = "ht-network-services-pentesting-pentesting-web-buckets"
DOCKER_FOR = "ht-generic-methodologies-and-resources-basic-forensic-methodology-docker-forensics"

m0 = mod(
    "modelo-de-responsabilidade",
    "Modelo de responsabilidade e identidade",
    "Separar o que é da nuvem do que é do cliente, e por que a identidade é o perímetro.",
    ["responsabilidade compartilhada", "identidade", "metadados de instância"],
    [
        unit(
            "fronteira",
            "A fronteira entre provedor e cliente",
            "Saber qual camada a organização realmente controla.",
            ["IaaS vs PaaS vs serverless", "identidade", "metadados"],
            [
                act("clo-m0-u1-kb-aws", "theory", "Cloud — AWS",
                    kb=AWS, minutes=50),
                act("clo-m0-u1-kb-azure", "theory", "Cloud — Azure",
                    kb=AZURE, minutes=45),
                act("clo-m0-u1-kb-meta", "theory", "Metadados de instância na nuvem a partir de um host Linux",
                    kb=META_LINUX, minutes=40),
                act("clo-m0-u1-ex-fronteira", "exercises",
                    "Exercício: tabela de responsabilidade por serviço",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Sem conta em nuvem.\n\n"
                        "Para quatro serviços (máquina virtual, banco gerenciado, fila, "
                        "função serverless), preencha a tabela:\n\n"
                        "| Serviço | É do provedor | É do cliente | É configurado pelo cliente |\n"
                        "| --- | --- | --- | --- |\n\n"
                        "Depois responda, com essas linhas:\n\n"
                        "1. Em qual serviço a versão do SO é responsabilidade do cliente?\n"
                        "2. Em qual serviço não existe SO para o cliente endurecer?\n"
                        "3. Onde a identidade do workload é o principal controle de segurança?\n\n"
                        "A última resposta é o tema de todo o resto da trilha."
                    )),
            ],
        ),
    ],
    summary="Quem controla o quê. Sem essa base, a auditoria procura vulnerabilidade no lugar errado.",
    completion="Tabela de responsabilidade preenchida e as três perguntas respondidas.",
)

m1 = mod(
    "iam-e-permissoes",
    "IAM e permissões",
    "Ler permissão efetiva em vez de permissão declarada, e encontrar caminho de escalada.",
    ["política", "RBAC", "limite de permissões", "escalada por terceiros"],
    [
        unit(
            "modelo-de-avaliacao",
            "Modelo de avaliação",
            "Saber como a nuvem decide permitir ou negar.",
            ["negação explícita", "permissão explícita", "padrão negar", "propagação"],
            [
                act("clo-m1-u1-own-iam", "theory", "IAM na nuvem: por que permissão demais raramente aparece como permissão demais",
                    kb=IAM, minutes=60),
                act("clo-m1-u1-kb-k8s", "theory", "Container - Kubernetes",
                    kb=K8S, minutes=50),
                act("clo-m1-u1-ex-policy", "exercises",
                    "Exercício: avaliar política e explicar a decisão",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Escreva (em arquivo de política, formato de sua escolha) dois "
                        "documentos: uma política de identidade que permite leitura de um "
                        "bucket, e uma política de recurso que concede escrita a outra conta.\n\n"
                        "Depois:\n\n"
                        "1. Aplique as regras de avaliação: onde há negação explícita? O que "
                        "é permitido?\n"
                        "2. Descreva uma ação que a identidade **não** consegue fazer e explique "
                        "por quê, citando qual camada falta.\n"
                        "3. Responda: por que 'listar' e 'ler um objeto específico' podem ter "
                        "resultados diferentes mesmo quando o objeto é acessível?"
                    )),
            ],
        ),
        unit(
            "caminho-de-escalada",
            "Caminho de escalada",
            "Encontrar a cadeia, não a permissão isolada.",
            ["iam:PassRole", "função lambda", "conta de serviço", "segredo"],
            [
                act("clo-m1-u2-kb-ssrf-inst", "theory", "SSRF para instâncias de cloud",
                    kb=SSRF_INST, minutes=40),
                act("clo-m1-u2-kb-ssrf-cloud", "theory", "SSRF na cloud",
                    kb=SSRF_CLOUD, minutes=40),
                act("clo-m1-u2-ex-escalada", "exercises",
                    "Exercício: desenhar um caminho de três saltos",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Cenário abstrato — desenhe em texto (não exploite recurso real):\n\n"
                        "Um usuário tem apenas permissão de **criar** uma função serverless e "
                        "**passar** um papel a ela. O papel tem permissão de leitura em bucket.\n\n"
                        "1. Descreva a cadeia completa: quem executa, com qual identidade, "
                        "atingindo qual recurso.\n"
                        "2. Nomeie o elo que faz a escalada ser possível sem permissão de "
                        "administrador.\n"
                        "3. Escreva a correção mínima que quebra a cadeia.\n\n"
                        "Entregue o diagrama e uma frase de achado no formato: principal, ação, "
                        "recurso, caminho."
                    )),
                act("clo-m1-u2-ex-k8s-rbac", "exercises",
                    "Exercício: ler um RoleBinding e o que ele realmente concede",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Modelo local, sem cluster.\n\n"
                        "Escreva um `Role` com permissão de criar pods e um `RoleBinding` que o "
                        "aplica a uma conta de serviço.\n\n"
                        "1. Descreva o impacto real: o pod roda com qual identidade?\n"
                        "2. Explique por que permissão de criar pod equivale a executar código "
                        "com a identidade da conta de serviço.\n"
                        "3. Proponha duas reduções que mantêm a função necessária.\n\n"
                        "RBAC é aditivo, como você deve ter concluído no artigo de IAM: o que "
                        "não foi concedido é negado, e o que foi concedido vale em qualquer lugar "
                        "do namespace."
                    )),
            ],
        ),
    ],
    summary="Permissão efetiva, caminho de escalada e o papel da identidade do workload.",
    prereq="modelo-de-responsabilidade",
    completion="Avaliação de política explicada, caminho de escalada desenhado e correção proposta.",
)

m2 = mod(
    "containers",
    "Containers e orquestração",
    "Avaliar o isolamento do container e o que uma conta de serviço pode alcançar.",
    ["namespace", "capabilities", "privileged", "socket docker", "registry"],
    [
        unit(
            "isolamento",
            "Isolamento",
            "Saber o que um container não protege por padrão.",
            ["namespaces", "cgroups", "capabilities", "privileged"],
            [
                act("clo-m2-u1-kb-ns", "theory", "Containers e namespaces",
                    kb=NS, minutes=45),
                act("clo-m2-u1-kb-sec", "theory", "Segurança de containers",
                    kb=NS_SEC, minutes=45),
                act("clo-m2-u1-kb-prot", "theory", "Visão geral das proteções de containers",
                    kb=NS_PROT, minutes=45),
                act("clo-m2-u1-kb-caps", "theory", "Linux capabilities em containers",
                    kb=NS_CAP, minutes=40),
                act("clo-m2-u1-kb-priv", "theory", "Escape de container com --privileged",
                    kb=NS_PRIV, minutes=40),
                act("clo-m2-u1-kb-distroless", "theory", "Containers distroless",
                    kb=NS_DISTROLESS, minutes=30),
                act("clo-m2-u1-ex-isolamento", "exercises",
                    "Exercício: medir o isolamento na sua própria máquina",
                    minutes=60,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Precisa de Docker instalado. Nada fora do seu host.\n\n"
                        "1. Suba um container comum (`docker run --rm -it debian bash` ou similar).\n"
                        "2. Dentro dele, observe: quantos processos aparecem? Qual é o usuário? "
                        "Quais capabilities estão ativas (`capsh --print` ou `/proc/self/status`)?\n"
                        "3. Compare com o host.\n"
                        "4. Suba outro com `--privileged` (só se você entende o risco) e compare "
                        "de novo.\n\n"
                        "Entregue a tabela comparativa. A diferença entre as linhas é o que uma "
                        "configuração errada concede de graça."
                    )),
            ],
        ),
        unit(
            "serviço-exposto",
            "Serviço exposto",
            "Reconhecer superfície de container publicada por engano.",
            ["socket Docker", "registry", "API do daemon"],
            [
                act("clo-m2-u2-kb-docker", "theory", "Container - Docker",
                    kb=DOCKER_P, minutes=45),
                act("clo-m2-u2-kb-2375", "theory", "2375, 2376 — Pentesting Docker",
                    kb=DOCKER2375, minutes=40),
                act("clo-m2-u2-kb-registry", "theory", "5000 — Pentesting Docker Registry",
                    kb=REGISTRY, minutes=35),
                act("clo-m2-u2-kb-ctr", "theory", "Escalada de privilégios do containerd (ctr)",
                    kb=CTR, minutes=35),
                act("clo-m2-u2-ex-varredura", "exercises",
                    "Exercício: descrever o impacto de um socket exposto",
                    minutes=45,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Sem tocar em serviço de terceiro.\n\n"
                        "Descreva, em texto:\n\n"
                        "1. O que acessa quem alcança o socket do Docker do host?\n"
                        "2. Por que 'o container está isolado' é incompatível com socket "
                        "montado dentro dele?\n"
                        "3. Escreva o achado no formato: porta, serviço, impacto, evidência "
                        "necessária para confirmar.\n\n"
                        "Não escaneie nada além da sua própria máquina."
                    )),
            ],
        ),
    ],
    summary="Namespace, capabilities e socket exposto: o que o container não protege por padrão.",
    prereq="iam-e-permissoes",
    completion="Tabela de isolamento de containers e achado de serviço exposto descrito com impacto.",
)

m3 = mod(
    "serverless-e-postura",
    "Serverless e postura",
    "Auditar o que não tem SO — código, papel de execução e gatilho — e medir postura.",
    ["variável de ambiente", "papel de execução", "gatilho", "scanner de postura"],
    [
        unit(
            "serverless",
            "Serverless",
            "Auditar função pelo que ela herda, não pelo que ela escreve.",
            ["segredo", "permissão de execução", "log", "estado entre invocações"],
            [
                act("clo-m3-u1-own-serverless", "theory", "Serverless: superfície de ataque quando não existe servidor",
                    kb=SERVERLESS, minutes=55),
                act("clo-m3-u1-kb-buckets", "theory", "Buckets",
                    kb=BUCKETS, minutes=35),
                act("clo-m3-u1-kb-docker-for", "theory", "Forense de Docker",
                    kb=DOCKER_FOR, minutes=40),
                act("clo-m3-u1-ex-checklist", "exercises",
                    "Exercício: checklist de auditoria de função",
                    minutes=50,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Monte um checklist para auditar uma função serverless, com coluna de "
                        "**evidência exigida** por item:\n\n"
                        "1. Runtime e versão.\n"
                        "2. Variáveis de ambiente com nome suspeito de segredo.\n"
                        "3. Permissões efetivas do papel de execução.\n"
                        "4. Autenticação no gatilho.\n"
                        "5. Campos sensíveis nos logs.\n\n"
                        "Item sem evidência possível não entra: checklist que não se pode "
                        "preencher vira teatro."
                    )),
            ],
        ),
        unit(
            "postura-e-relatorio",
            "Postura e relatório",
            "Medir cobertura, não contar achados.",
            ["scanner", "triagem", "falso positivo", "relatório"],
            [
                act("clo-m3-u2-ex-postura", "exercises",
                    "Exercício: interpretar saída de scanner e separar ruído de achado",
                    minutes=55,
                    body_md=(
                        "**SOMENTE SOFTWARE.**\n\n"
                        "Use um scanner de configuração local (Trivy, Checkov ou equivalente) "
                        "num diretório com manifesto escrito por você.\n\n"
                        "1. Rode o scanner e liste os achados.\n"
                        "2. Classifique cada um: **real**, **ruído** ou **falso positivo** do "
                        "próprio scanner.\n"
                        "3. Para cada real, escreva o impacto em uma frase e a correção mínima.\n\n"
                        "Entregue a tabela de triagem. Scanner que não passa por triagem produz "
                        "relatório que ninguém corrige."
                    )),
                act("clo-m3-u2-assess", "assessment", "Avaliação: cloud e containers",
                    minutes=35,
                    questions=[
                        {"id": "q1", "prompt": "Na AWS, o que acontece se uma política permite e outra nega explicitamente a mesma ação?",
                         "accepted": ["a negação explícita vence", "negação explícita prevalece", "é negado"],
                         "explanation": "Negação explícita vence qualquer permissão, é a regra central da lógica de avaliação documentada pela AWS."},
                        {"id": "q2", "prompt": "Por que guardar segredo em variável de ambiente da função é ruim?",
                         "accepted": ["quem lê a configuração lê o segredo", "aparece em log de erro", "fica visível na API de configuração"],
                         "explanation": "Variável de ambiente é lida por quem tem permissão de configuração e aparece em dump de erro e em artefato de build."},
                        {"id": "q3", "prompt": "O que significa permissão de criar pods num namespace Kubernetes?",
                         "accepted": ["executar código com a identidade da conta de serviço", "executar com a conta de serviço do namespace"],
                         "explanation": "O pod criado executa com a conta de serviço, então criar pods equivale a executar código com aquela identidade."},
                        {"id": "q4", "prompt": "Por que o socket Docker montado dentro do container é crítico?",
                         "accepted": ["o container pode controlar o daemon do host", "fuga do isolamento", "acessa o host como root"],
                         "explanation": "Quem fala com o socket controla o daemon e pode criar container privilegiado — o isolamento deixa de existir."},
                    ]),
                act("clo-m3-u2-project", "project",
                    "Capstone: auditoria de postura de uma arquitetura modelada",
                    minutes=150,
                    body_md=(
                        "**SOMENTE SOFTWARE.** Entrega do capstone.\n\n"
                        "Modele (em documento e, se quiser, em manifesto local) uma arquitetura "
                        "pequena: máquina virtual, bucket, função serverless e container.\n\n"
                        "Entregue:\n\n"
                        "1. Diagrama com a identidade de cada componente.\n"
                        "2. Tabela de permissões **efetivas** por identidade.\n"
                        "3. Um caminho de escalada encontrado, com o elo que o torna possível.\n"
                        "4. Achados de container com a configuração que os provoca.\n"
                        "5. Checklist de função preenchido.\n"
                        "6. Plano de correção priorizado e triagem de scanner.\n\n"
                        "Nada aqui precisa existir em nuvem. O produto é o raciocínio documentado "
                        "— e é o que se leva para uma conta real depois."
                    )),
            ],
        ),
    ],
    summary="Serverless, postura e relatório. Auditar o que não tem SO.",
    prereq="containers",
    completion="Checklist de função, triagem de scanner e avaliação aprovada.",
)

path = {
    "slug": "cloud-containers",
    "title": "Cloud e Containers",
    "codename": "CLO",
    "domain": "cloud",
    "summary": "Identidade, containers e serverless: ler permissão efetiva, encontrar caminho de escalada e auditar o que não tem sistema operacional para endurecer.",
    "description": (
        "A trilha trata cloud pelo que a organização realmente controla: identidade, "
        "configuração, código e gatilho. Cruza o material importado sobre AWS, Azure, "
        "Kubernetes e Docker com dois documentos próprios feitos para preencher lacunas "
        "específicas — avaliação de política IAM e riscos de serverless. A plataforma "
        "não tem conta em nuvem e a trilha não finge que tem: a prática é análise de "
        "política, modelagem de arquitetura e exercícios locais com Docker."
    ),
    "entry_level": "Linux básico, containers, noções de redes",
    "exit_level": "capaz de auditar identidade e configuração em nuvem e apresentar caminho de escalada reproduzível",
    "estimated_hours": 34,
    "priority": 74,
    "phase": 3,
    "icon": "layers",
    "accent": "amber",
    "prerequisites": ["linux-security", "api-security"],
    "competencies": [
        "Explicar o modelo de responsabilidade compartilhada por tipo de serviço",
        "Ler permissão efetiva em vez de permissão declarada",
        "Encontrar caminho de escalada por permissão de terceiros",
        "Avaliar isolamento de container por capabilities e namespaces",
        "Reconhecer serviço de container exposto e seu impacto",
        "Auditar função serverless pelo papel de execução e pelo gatilho",
        "Triar resultado de scanner separando ruído de achado",
    ],
    "tools": ["trivy", "checkov", "prowler", "cloudfox", "pacu", "ScoutSuite", "kubectl", "docker", "docker-compose", "grype", "syft"],
    "equipment": (
        "Somente software. Docker e scanners rodam na máquina do operador; nenhuma conta "
        "em nuvem é necessária e nenhum recurso pago é provisionado."
    ),
    "modules": [m0, m1, m2, m3],
    "capstone": {
        "objective": "Auditar uma arquitetura de cloud modelada, com identificação de um caminho de escalada e plano de correção priorizado.",
        "scope_md": (
            "Arquitetura modelada pelo próprio operador (documento e/ou manifesto local). "
            "Nenhuma conta real, nenhum recurso de terceiro."
        ),
        "resources_md": (
            "Editor de texto, Docker local, scanner de configuração (Trivy ou Checkov). "
            "Documentação importada e os dois documentos próprios sobre IAM e serverless."
        ),
        "steps_md": (
            "1. Desenhar a arquitetura com a identidade de cada componente.\n"
            "2. Levantar permissões efetivas por identidade.\n"
            "3. Procurar caminho de escalada e documentar cada elo.\n"
            "4. Avaliar containers por isolamento e socket.\n"
            "5. Preencher o checklist de serverless.\n"
            "6. Triar scanner e priorizar correção."
        ),
        "success_criteria": [
            "Diagrama com identidade por componente",
            "Tabela de permissões efetivas, não declaradas",
            "Caminho de escalada com principal, ação, recurso e cadeia",
            "Achado de container com a configuração que o provoca",
            "Checklist de função preenchido com evidência por item",
            "Plano de correção priorizado e triagem de ruído",
        ],
        "evidence": [
            "Diagrama de arquitetura",
            "Tabela de permissões efetivas",
            "Descrição do caminho de escalada",
            "Saída do scanner com classificação",
            "Checklist de serverless",
            "Plano de correção",
        ],
        "expected_result": "Relatório de postura de uma arquitetura modelada, com caminho de escalada e correção.",
        "grading_md": "Modelo de identidade 30%, raciocínio de escalada 30%, triagem e correção 40%.",
        "challenge_slug": "",
    },
}

emit("11-cloud-containers.json", path)