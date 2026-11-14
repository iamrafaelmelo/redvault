---
slug: own-cloud-iam-permissoes
title: "IAM na nuvem: por que \"permissão demais\" raramente aparece como permissão demais"
category: cloud-iam
summary: "Explica o modelo de avaliação de política da AWS (negação explícita, lista de permissões, limites de sessão e de permissões), a diferença entre identidade e recurso, e como um papel com permissão aparentemente restrita pode escalar por meio de permissões de terceiros. Compara com Kubernetes RBAC e com o modelo de identidade de pods. O foco é o raciocínio que sustenta um achado, não o comando de um scanner."
tags: "cloud aws iam permissao policy rbac kubernetes privilegio papel"
severity: info
references:
  - AWS — Lógica de avaliação de políticas | https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
  - AWS — Referência de políticas e elementos | https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies.html
  - Kubernetes — Controle de acesso baseado em papéis (RBAC) | https://kubernetes.io/docs/reference/access-authn-authz/rbac/
  - Prowler — avaliação de postura de cloud | https://github.com/prowler-cloud/prowler
  - CloudFox — enumeração de permissões em cloud | https://github.com/BishopFox/cloudfox
---

O erro mais comum ao avaliar ambientes de nuvem é procurar a palavra
"administrator" no nome da política. Permissão excessiva quase nunca está
escrita com esse nome: está distribuída em dezenas de políticas pequenas, em
papéis que se podem assumir uns aos outros, e em permissões sobre recursos que
concedem acesso a outros recursos.

## O modelo de avaliação da AWS

Toda requisição é decidida pela mesma ordem. A documentação oficial da AWS
descreve a lógica em termos de conjuntos:

1. **Negação explícita** vence tudo. Se qualquer política aplicável tem
   `Effect: "Deny"`, a requisição é negada, mesmo que outra política permita.
2. Sem negação explícita, a requisição é permitida se houver **alguma**
   permissão explícita — em política de identidade, de recurso, de limite de
   permissões ou de sessão.
3. Se nenhuma permissão explicitamente concede, o padrão é **negar**.

O ponto 3 é o que garante que a nuvem comece fechada. O ponto 2 é o que a
torna difícil de auditar: basta **uma** concessão em algum documento de alguma
camada para liberar a ação.

### Velocidade de propagação de alteração de permissão

O ambiente de nuvem é eventualmente consistente na direção de conceder. Quando
uma permissão é adicionada a uma entidade, a alteração pode levar tempo para
propagar, e a documentação da própria AWS descreve esse comportamento. Um teste
que falha imediatamente após a concessão e passa trinta segundos depois não
estava "mal configurado": estava em propagação. Um laudo que afirma "permissão
ausente" sem esperar a propagação afirmou algo falso.

## Identidade ou recurso?

Há dois lugares onde uma permissão pode viver:

- **política de identidade** — anexada a usuário, grupo ou papel. Responde "o
  que esta identidade pode fazer".
- **política de recurso** — anexada ao recurso, como um bucket ou uma fila.
  Responde "quem pode fazer isto neste recurso".

O efeito prático é o acesso cruzado de conta: um bucket com política de recurso
que concede leitura a uma entidade de outra conta permite leitura, mas aquela
entidade não consegue listar o bucket, porque a listagem é uma ação de
identidade. A leitura funciona e a enumeração não — fato frequentemente lido
como "bucket fechado".

## Escalada sem permissão de administrador

Uma entidade pode ter apenas permissões "aparentemente inofensivas" e ainda
escalar, porque algumas permissões têm efeito indireto:

| Permissão aparente | Efeito real |
| --- | --- |
| criar versão de função Lambda | a função executa com o papel dela, não com o seu |
| passar um papel a um serviço | permite que o serviço adote privilégios que você não tem |
| escrever em bucket usado por pipeline | conteúdo influencia quem consome o bucket |
| atualizar política de confiança de papel | permite que outro principal assuma aquele papel |
| alterar recurso de orquestração | dispara execução com outras credenciais |

A pergunta de auditoria deixa de ser "existe permissão de administrador?" e
passa a ser: **"existe caminho de uma identidade de baixo privilégio até uma de
alto privilégio?"** E a resposta exige grafo, não lista.

## Kubernetes: outro modelo, mesmo problema

Kubernetes não usa o modelo de negação explícita da AWS. RBAC é puramente
aditivo: papéis (`Role`/`ClusterRole`) concedem, ligações
(`RoleBinding`/`ClusterRoleBinding`) aplicam a um sujeito, e o que não foi
concedido é negado por padrão. Diversamente da AWS, um `RoleBinding` concede
permissão em **qualquer lugar** dentro do namespace, e isso raramente é o
desejo de quem a criou.

Três permissões merecem atenção especial porque quebram o isolamento:

- **criar pods** — o pod executa com a conta de serviço do namespace.
- **criar recursos** que montam volume de host — o pod acessa o nó.
- **`get/list` em segredos** — o segredo de outra aplicação está ali.

Assim como na AWS, a identidade do workload importa: uma conta de serviço com
permissão de criar pods equivale, na prática, a executar código com as
credenciais daquela conta.

## Como estruturar o achado

Um achado de IAM que sobrevive à revisão tem quatro elementos:

1. **Principal** — qual identidade, com qual política.
2. **Ação** — qual chamada de API exata é permitida.
3. **Recurso** — sobre qual recurso, com qual condição.
4. **Caminho** — qual cadeia de chamadas leva daquela ação até o impacto
   afirmado.

Sem o item 4, "permissão excessiva" é opinião. Com o item 4, é um caminho
reproduzível — e é isso que a organização consegue corrigir.