---
slug: own-cloud-serverless-riscos
title: "Serverless: superfície de ataque quando não existe servidor para endurecer"
category: cloud-serverless
summary: "Em Lambda, Cloud Functions e equivalentes, a organização não controla o sistema operacional: controla o código, a função que ele executa e a identidade que herda. Este artigo detalha essa fronteira — variáveis de ambiente como cofre de segredos, permissão excessiva do papel de execução, segredo em log, tempo de vida do contêiner reutilizado, e o raciocínio de auditoria de evento de gatilho."
tags: "serverless lambda cloud function papel execucao segredo evento gatilho"
severity: info
references:
  - AWS — Lógica de avaliação de políticas (aplica-se ao papel de execução) | https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
  - AWS — Produtos e documentação de segurança | https://docs.aws.amazon.com/security/
  - MITRE ATT&CK — base de técnicas para nomear comportamento | https://attack.mitre.org/
  - Trivy — varredura de configuração e de dependências | https://github.com/aquasecurity/trivy
  - CloudFox — enumeração de recursos e permissões | https://github.com/BishopFox/cloudfox
---

Em serverless não existe host para o time de segurança endurecer. Não há SSH,
não há `systemd`, não há pacote instalado. O que existe é uma **função** com
código próprio e um **papel de execução** com permissões na conta.

Isso muda a pergunta. Em servidor: "quais serviços rodam e como estão
configurados?". Em serverless: **"quais eventos disparam código, e que
privilégios esse código herda?"**

## A fronteira que pertence à organização

| Camada | Dono |
| --- | --- |
| Kernel, runtime, isolamento físico | provedor |
| Versão de runtime disponível | provedor define, cliente escolhe |
| Código da função e dependências embutidas | cliente |
| Variáveis de ambiente | cliente |
| Papel de execução e permissões | cliente |
| Gatilhos e autorização de quem invoca | cliente |

A vulnerabilidade clássica em serverless está na **última linha**: qualquer
coisa que consiga invocar a função executa o código dela com o papel dela.
A permissão não está no código; está na identidade que o código carrega.

## Vetor 1 — variáveis de ambiente como cofre frágil

A prática difundida de guardar segredos em variáveis de ambiente da função é
uma escolha ruim, por três motivos independentes:

1. **Visibilidade na API de configuração** — quem tem permissão de ler a
   configuração da função lê as variáveis. É frequentemente uma permissão
   "de leitura" considerada inofensiva.
2. **Exposição em logs e relatórios de erro** — um dump de ambiente em caso de
   exceção escreve o segredo no log. Raramente há revisão.
3. **Exposição em artefato de build** — a configuração fica versionada em
   infraestrutura como código e, portanto, no histórico do repositório.

O padrão correto é a função obter o segredo em tempo de execução, de um serviço
de gestão de segredos, com permissão mínima para apenas aquele segredo.

## Vetor 2 — papel de execução com permissão de conta

Quando o papel da função tem `*` em recursos — ou tem permissão ampla o
suficiente para o objetivo — a consequência é que uma falha de entrada na
função (SSRF, injeção, desserialização) se converte em comprometimento de
**todos** os recursos que aquele papel pode alcançar. A função é a nova "caixa
perimetral", e o papel é a chave de tudo atrás dela.

Teste de raciocínio: pegue a política do papel e pergunte "que ação destrutiva
o código da função precisa realizar?". Se a resposta for mais ampla do que o
necessário, é excesso — e o excesso é o ponto de entrada da escalada.

## Vetor 3 — segredo em log

O log da função é frequentemente exportado para um serviço de observabilidade
com acesso de outra equipe, ou retido por meses. Um cabeçalho de autorização
impresso para depuração é um segredo permanente. O controle é técnico —
mascarar por padrão, nunca imprimir objeto de requisição inteiro — e não
depende de disciplina do desenvolvedor.

## Vetor 4 — reutilização do ambiente de execução

O ambiente de execução é reutilizado entre invocações. Isso significa que
estado em memória persistente, arquivo em `/tmp` e conexão aberta podem
sobreviver de uma invocação para a próxima. Duas consequências:

- **cache de credencial** — segredo obtido na invocação 1 permanece em memória
  na invocação 2, inclusive de outro usuário, se o código não isolar escopo.
- **estado sujo** — variável global que guarda dado do usuário anterior é vazamento
  entre requisições, exatamente como num processo de servidor web.

A conclusão é que serverless **não** é "stateless de graça". O ambiente é
stateless por contrato, mas o processo que o serve não é.

## Vetor 5 — gatilho sem autorização

Uma função exposta por API pode ser invocada por qualquer um que consiga
chamar o endpoint. O controle de quem pode invocar é configurado no gatilho,
não na função. Um endpoint de teste esquecido, sem autenticação, invoca a
função com o papel dela — e a pessoa bate direto no banco e nos buckets.

## Auditoria que vale

1. Inventário de funções, runtime, gatilho e papel.
2. Para cada papel: permissões efetivas, não as declaradas.
3. Para cada função: variáveis de ambiente; procurar nome que sugira segredo.
4. Para cada gatilho: existe autenticação? Existe limite de taxa?
5. Para cada log: um campo sensível é impresso?

O item 2 é o único que exige raciocínio do modelo de avaliação lembrado no
artigo de IAM: a permissão efetiva é a interseção entre política de identidade,
limite de permissões e políticas de recurso — e é isso que precisa ser citado
no laudo.