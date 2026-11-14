---
slug: own-osint-pessoas-organizacoes
title: "Pessoas e organizações em OSINT: correlação de identidade e o limite ético"
category: osint-people
summary: "Trata a correlação de identidade como problema de hipótese e evidência: o que sustenta um vínculo entre contas, o que apenas sugere, e por que o nome de usuário repetido é evidência fraca. Cobre o uso de metadados de documento e repositório, o risco de falso positivo por homonímia, e o limite ético e legal de investigar pessoas sem base autorizada."
tags: "osint identidade correlacao usuario metadata homonimia etica pessoas"
severity: info
references:
  - HackTricks — Metodologia de Reconhecimento Externo | https://github.com/HackTricks-wiki/hacktricks
  - HackTricks — Wide Source Code Search | https://github.com/HackTricks-wiki/hacktricks
  - Sherlock — busca de mesmo nome de usuário em plataformas | https://github.com/sherlock-project/sherlock
  - OSINT Framework — índice de fontes públicas | https://osintframework.com/
  - MITRE ATT&CK — Reconnaissance (TA0043) | https://attack.mitre.org/
---

Investigação de pessoa em contexto de segurança tem uma pergunta legítima: por
exemplo, "quais contas corporativas expõem credencial ou informação interna?".
A pergunta ilegítima é "quem é esta pessoa e o que ela faz na vida privada", e
não existe ferramenta que a torne aceitável.

O técnico aqui é correlação: decidir se duas informações apontam para a mesma
entidade. E a correlação é exatamente onde os erros acontecem.

## Homonímia é a regra, não a exceção

Um nome completo, sozinho, não identifica. Em qualquer organização de porte
médio existem homônimos. Um perfil em rede social com o mesmo nome de um
funcionário é hipótese, não vinculação.

O que sustenta um vínculo, em ordem de força:

| Evidência | Sustenta? |
| --- | --- |
| documento oficial com identificador | sim, com fonte primária |
| e-mail corporativo publicado pela organização | sim, para o vínculo profissional |
| atividade pública citando a organização no mesmo período | sugere |
| mesmo nome de usuário em várias plataformas | sugere fortemente |
| mesmo nome de perfil | apenas sugere |
| coincidência de nome completo | não |

A regra: o vínculo precisa de **pelo menos dois elementos independentes**. Nome
de usuário repetido é um elemento — a ferramenta de busca de nome de usuário
faz isso bem, e serve para **propor** hipótese, não para concluí-la. A conclusão
vem da confirmação na origem.

## Metadados: o que sobrevive

Documento publicado costuma carregar metadados: ferramenta que o criou, nome de
usuário do sistema que o editou, data de modificação. Imagem publicada pode
carregar coordenada embutida pela câmera.

Três cuidados:

1. **Remoção é comum**, e a ausência de metadado não prova nada.
2. **Metadado pode ser herdado** — o arquivo pode ter passado por uma ferramenta
   que reescreveu o autor. Atribua ao **documento**, não à pessoa.
3. **Repositório de código é o lugar mais rico** — histórico de commits associa
   autor declarado a endereço de e-mail, e a busca por credencial em arquivo de
   configuração é uma das falhas de vazamento mais frequentes.

O HackTricks documenta a busca ampla por código como técnica de reconhecimento;
é a mesma técnica usada para auditoria defensiva de exposição acidental.

## O limite: quando a coleta deixa de ser justificada

Um exercício de OSINT tem alvo e escopo. O que está fora do escopo não se
coleta, mesmo que seja público e mesmo que seja fácil.

Sinais de que se cruzou o limite:

- a investigação passou de "serviço exposto" para "rotina de pessoa";
- o dado coletado não serve para a conclusão que o exercício precisa;
- a coleta envolveria contas de pessoa que não é o alvo;
- a conclusão a ser publicada nomeia pessoa sem evidência de vínculo forte.

O último é o dano prático: um laudo que atribui uma ação a uma pessoa errada,
com base em homonímia, causa prejuízo a quem não tem relação com o caso.

## O que se pode publicar

- Alvo organizacional: sim, com fonte.
- Identidade de papel — "a conta administrativa X" — sim, quando é o objeto
  técnico.
- Identidade de pessoa: somente quando é indispensável à conclusão, com o
  mínimo de dados e confiança declarada.
- Nenhum dado pessoal em relatório de teste: o padrão.

## Credencial encontrada

Quando a coleta encontra credencial real — token em repositório, senha em
arquivo publicado — a ação correta não é usar. É:

1. documentar onde estava e quando foi vista;
2. notificar o responsável pelo canal apropriado;
3. não usar, não ampliar e não publicar além do necessário.

Usar credencial encontrada converte um reconhecimento legítimo em acesso não
autorizado, com todos os efeitos legais que isso tem. É o erro de maior custo
que existe nesta área.