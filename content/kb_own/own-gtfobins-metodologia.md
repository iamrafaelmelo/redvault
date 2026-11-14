---
slug: own-gtfobins-metodologia
title: "GTFOBins: viver do sistema com binários legítimos"
category: linux-privesc
summary: "Como usar o GTFOBins de forma metódica: entender por que um binário legítimo permite shell, leitura e escrita em contexto sudo, SUID e capabilities, e como validar o achado antes de explorá-lo."
tags: "gtfobins linux privesc suid sudo capabilities"
severity: medium
references:
  - GTFOBins — projeto original | https://gtfobins.github.io/
  - GTFOBins — repositório e critérios | https://github.com/GTFOBins/GTFOBins.github.io
  - GTFOBins — API JSON | https://gtfobins.github.io/api.json
---

O GTFOBins não é uma lista de exploits e não afirma que os binários listados são
vulneráveis. A própria introdução do projeto diz que ele é um compêndio sobre
"viver do sistema" (*living off the land*) quando só existem certos executáveis
disponíveis. O que o projeto documenta são **funções legítimas** de programas
Unix-like — abrir shell, ler arquivo, escrever arquivo, carregar biblioteca,
conectar e ouvir — que, num sistema **mal configurado**, quebram uma restrição
local.

## A premissa que precisa existir

Um binário só é útil para escalar privilégio se **outra coisa** estiver errada.
Três contextos, e apenas três, aparecem no GTFOBins:

| Contexto | O que está errado | O que o binário faz por você |
| --- | --- | --- |
| `sudo` | regra do sudoers permite rodar o binário como outro usuário | executa com a identidade alvo |
| `SUID` | binário tem bit setuid e pertence a root | executa com euid 0 |
| `capabilities` | binário recebeu capability como `cap_setuid` ou `cap_dac_read_search` | age além do seu usuário |

Também existe a saída de shell restrito (rbash, jail de `git`, `vi` em modo
restrito): o binário permite escapar do confinamento, não elevar privilégio.
E `inherit`, quando o binário herda privilégios por um dos três contextos acima.

Se nenhum desses contextos existe, a entrada do GTFOBins é irrelevante. Antes de
consultar o site, você precisa saber **o que** está concedendo privilégio.

## Como enumerar

```bash
# SUID e SGID fora do padrão
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null

# regras de sudo do usuário atual
sudo -l

# capabilities atribuídas a arquivos
getcap -r / 2>/dev/null
```

Compare cada resultado com `GTFOBins` e com a documentação do pacote
(`dpkg -S /caminho/do/binario`) para entender *por que* o binário está ali. Um
`find` com SUID num sistema padrão é esperado; um `vim` com SUID não é.

## O que verificar antes de explorar

1. **O binário é o que parece.** Caminho, dono e bits: `ls -la`. Um wrapper em
   script com SUID não se comporta como o programa original.
2. **A versão permite a função.** Algumas funções documentadas dependem de
   recurso de versão. `git`, por exemplo, removeu o paginador padrão em versões
   recentes; a chamada de shell via paginador deixou de funcionar onde o
   paginador não é configurado.
3. **O contexto é real.** `sudo -l` mostrar o binário não significa que você
   pode usar todos os argumentos: uma regra `sudo vim /var/log/x` te restringe
   a esse arquivo, e a entrada "sudo" do GTFOBins pode não se aplicar.
4. **Não há `secure_path` nem `env_reset`** quando a função depende de variável
   de ambiente (`PATH`, `LD_PRELOAD`, `PAGER`).

## Exemplo trabalhado: um binário com `cap_dac_read_search`

`cap_dac_read_search` permite ler qualquer arquivo ignorando permissão de
leitura. Se `tar` tiver essa capability, ele pode ler `/etc/shadow` mesmo sem
permissão direta. A verificação é:

```bash
getcap /usr/bin/tar
# /usr/bin/tar cap_dac_read_search=ep
tar -cf /dev/null /etc/shadow
```

Se o `getcap` não listar nada, a hipótese morre. Não existe "talvez": capability
é um bit no filesystem estendido, você lê ou não lê.

## Como isso vira relatório

O GTFOBins responde "com este binário e este contexto, dá para fazer X". A
evidência que vale no laudo é outra:

- o comando de enumeração e a **saída crua** (`sudo -l`, `getcap -r /`);
- a linha do arquivo de configuração que causa o problema
  (`/etc/sudoers.d/deploy`), com `sudo -l` correspondente;
- o comando executado e o efeito observado;
- a **correção**: remover a regra, tirar o bit SUID, remover a capability,
  e por que aquilo não era necessário.

## Cuidado com o que o site não te diz

- A lista mistura contextos. Ler a página do binário inteira, não só o link que
  apareceu na busca.
- Muitas entradas assumem shell interativo. Em sessão sem TTY, funções
  interativas (paginador, editor) falham, e você precisa da alternativa de
  execução direta.
- O projeto é comunitário: uma entrada pode estar incompleta para sua versão.
  Quando ela falhar, o caminho é ler a documentação do próprio binário, não
  concluir que o sistema é imune.

## O que este documento não cobre

Binários do Windows (o projeto irmão é o LOLBAS), exploits de kernel, e o
detalhamento de cada binário — são centenas, e o site é a fonte sempre atualizada.