# REDVAULT

**Um laboratório de segurança ofensiva para aprender atacando de verdade.**

Repositório: https://github.com/lunalully/redvault  
Documentação técnica: [README.md](../README.md)

O REDVAULT é o projeto que eu construí para estudar red team na prática. A proposta é bem direta: você abre o navegador, escolhe um alvo e começa a explorar. Nada de teoria solta ou exercício de brinquedo. São aplicações de verdade, feitas para serem vulneráveis de propósito, rodando na sua própria máquina.

Tudo funciona local, sem login, sem nuvem e sem custo. Você liga a plataforma, escolhe por onde começar e vai.

![Painel do REDVAULT](docs/images/painel.jpg)

## Os alvos

Hoje o catálogo tem **97 alvos**, sendo **89 desafios** e **8 máquinas completas**. Os desafios cobrem **12 categorias**, como reconhecimento, autenticação, controle de acesso, SQL injection, XSS, falhas de lógica, upload de arquivos, segurança de API e encadeamento de vulnerabilidades.

A curva de dificuldade também está bem distribuída: 6 alvos para quem está começando, 26 fáceis, 31 médios, 30 difíceis e 4 no nível insano. Dá para evoluir sem pular etapas.

As 8 máquinas são cenários maiores, com começo, meio e fim. Cada uma tem três flags, uma de usuário, uma de API e uma de root, e exige encadear várias falhas até chegar ao objetivo final. Os nomes já dão o tom: Meridian Bank, Nexus Commerce, Horizon Health, Atlas HR, Finch Support, Harbor Claims, Orbit Console e Wayline Logistics.

![Máquinas completas](docs/images/maquinas.jpg)

No total são **113 flags**, **291 dicas progressivas**, **97 walkthroughs completos** e **291 referências** para estudar depois. Em **57 alvos**, a flag só aparece quando o objetivo real é cumprido, então não adianta tentar atalho.

![Biblioteca de desafios](docs/images/desafios.jpg)

## A biblioteca

Uma das partes que eu mais gosto é a biblioteca técnica. São **1.303 documentos**, quase **2,5 milhões de palavras** organizadas em **183 categorias**. Dá para pesquisar um tema, ler a explicação, ver exemplos e voltar para o lab com uma ideia clara.

A base reúne material do HackTricks, do PayloadsAllTheThings e do OWASP Web Security Testing Guide, com as licenças respeitadas, além de **24 documentos próprios** escritos para cobrir assuntos que eu sentia falta.

Junto com isso vem uma coleção de **1.716 payloads** prontos para consulta, distribuídos em **64 linguagens** e **1.060 técnicas diferentes**. É aquele tipo de acervo que economiza tempo na hora de testar uma ideia.

![Leitor da biblioteca](docs/images/biblioteca.jpg)

## As trilhas

Para quem não quer sair escolhendo desafio no escuro, existem **18 programas de trilha**, divididos em **78 módulos** e **151 unidades**. No total, são **788 atividades**: 514 de teoria, 138 exercícios, 89 labs, 29 avaliações e 18 projetos finais.

As trilhas vão de fundamentos de pentest web a red team, passando por cloud, mobile, hardware, rádio, forense, malware, engenharia reversa, criptografia, Linux, Windows, OSINT, IoT e exploração de binários. Além disso, há **10 trilhas curadas** que organizam os desafios em sequência, do mais simples ao mais avançado.

Também fazem parte do projeto a Academy, com **17 artigos**, um glossário com **27 termos** e uma coleção de **10 CVEs** comentadas.

![Trilhas de aprendizado](docs/images/trilhas.jpg)

## As ferramentas e a parte de jogo

O projeto reúne **22 ferramentas** em cinco categorias: reconhecimento, exploração, senhas e hashes, teste web e análise. Cada uma vem com contexto de uso, para não virar só uma lista de nomes.

E como aprender também precisa ser divertido, existem **15 conquistas** para desbloquear ao longo do caminho, com nomes como Primeiro Sangue, Root e Reação em Cadeia. É um detalhe, mas ajuda a manter o ritmo.

![Detalhe de uma trilha](docs/images/trilha.jpg)

## Como tudo funciona

O REDVAULT foi feito para rodar em uma máquina só, sem complicação. Não tem cadastro, não tem senha e não tem painel administrativo para configurar. A plataforma sobe em **127.0.0.1:8000** e trata você como o operador local.

Os labs rodam em portas locais, entre 42000 e 42999, e ficam isolados do resto do sistema. Se quiser mais uma camada de proteção, dá para ativar o sandbox com bubblewrap. As flags são validadas no servidor, com assinatura criptográfica, então o gabarito não fica solto no navegador.

Tem até um bot de navegador para os desafios de XSS, o que permite testar ataques de verdade em vez de só imaginar o que aconteceria.

A interface inteira é em português do Brasil, inclusive os desafios, as dicas, os walkthroughs e a biblioteca. Os termos técnicos que todo mundo usa em inglês continuam em inglês, porque traduzir forçado só atrapalha.

## Para rodar

É bem simples:

```bash
python3 run.py
```

Em cerca de 16 segundos a plataforma está no ar. A partir daí é escolher um alvo e começar.

![Certificado interno de conclusão](docs/images/certificado.jpg)

## Para quem é

O REDVAULT é para quem quer aprender segurança ofensiva de verdade, com as mãos no teclado e sem depender de ambiente de terceiros. Serve para estudo individual, para praticar antes de uma certificação e para entender como as falhas se encadeiam em um cenário real.

No fim, é o projeto que eu gostaria de ter encontrado quando comecei. Um lugar só, organizado, em português e sem atalhos, onde a única forma de passar é entender o que está acontecendo.