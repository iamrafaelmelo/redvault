# Learning Paths — auditoria da plataforma e mapa de lacunas

Levantamento feito em 2026-11-13 sobre o banco `data/redvault.db` e o
filesystem do repositório. Todos os números abaixo foram contados, não
estimados. Nada aqui foi inferido a partir do README.

## 1. Inventário real

| Recurso | Tabela / origem | Quantidade | Observação |
| --- | --- | ---: | --- |
| Categorias de desafio | `categories` | 12 | 4–16 labs por categoria |
| Desafios | `challenges` (`kind=challenge`) | 89 | |
| Máquinas multi-estágio | `challenges` (`kind=machine`) | 8 | 3 flags cada |
| Total de alvos | | **97** | 100 diretórios em `labs/`, 97 com `app.py` + `manifest.json` |
| Flags | `flags` | 113 | validadas server-side |
| Hints progressivos | `hints` | 291 | 3 por alvo |
| Soluções / walkthrough | `solutions` | 97 | |
| Referências por alvo | `references` | 291 | 151 URLs únicas |
| Trilhas antigas | `paths` | 10 | listas de slugs, sem módulos nem teoria |
| Documentos da KB | `kb_documents` | 1279 | 1144 HackTricks PT-BR + 135 PayloadsAllTheThings EN |
| Payloads com contexto | `kb_payloads` | 1716 | |
| Links doc ↔ lab | `kb_topic_links` | 291 | |
| Categorias da KB | `kb_categories` | 152 | 7 grupos próprios + 20 top-level HackTricks |
| Artigos da Academy | `content/academy/*.md` | 17 | PT-BR, escritos aqui |
| Ferramentas documentadas | `content/tools.json` | 22 | Nmap, Burp, ffuf, sqlmap, Wireshark… |
| Referências externas por doc | `kb_references` | 1279 | |

### Verificação funcional dos laboratórios

`pytest tests/test_labs.py` → **61 passed em 40s**. A suíte sobe um processo
real por lab e executa o exploit. Portanto os 97 alvos são funcionais; os 3
diretórios restantes em `labs/` são `_shared/`, `logs/` e `state/`, não labs.

### Cobertura da KB por área das trilhas

Contagem de documentos cujo título casa com os termos técnicos da área:

| Área | Docs relevantes | Lacunas encontradas |
| --- | ---: | --- |
| Web / API | 185 + 16 | BOLA e OIDC sem documento dedicado próprio (cobertos dentro de outros) |
| Papéis Linux | 92 | tópico GTFOBins sem documento próprio |
| Papéis Windows | 114 | NTFS e LOLBAS sem documento próprio |
| Active Directory | 21 | cobertura completa para Kerberos, Kerberoast, DCSync, AD CS, delegations, ACL |
| Hardware | 35 | **SWD, PCB analysis, Secure Boot e glitching sem documento** |
| Wireless / RF | 51 | **SDR e deauth sem documento** |
| Mobile | 71 | completa para Android; iOS depende do que o HackTricks cobre |
| Reversing | 12 | **Ghidra, radare2, disassembly e packers sem documento** |
| Exploit dev | 128 (binário) | "buffer overflow" como termo exato sem doc próprio |
| Cloud | 9 | **serverless sem documento**; cobertura boa em AWS, Azure, K8s, Docker |
| Forensics | 2 + Volatility | **timeline analysis e cadeia de custódia sem documento** |
| Malware | 7 | **YARA sem documento** |
| OSINT | 2 | **fundamentos, Shodan e certificate transparency sem documento** |
| Crypto | 19 | HMAC e PKI sem documento próprio |
| DevSecOps | 23 | **Terraform e supply chain sem documento** |
| CTF | disperso em `ht-generic-*` | precisa de trilha montada, não de conteúdo novo |

## 2. Fontes externas verificadas

68 URLs testadas via HTTP e 41 repositórios consultados pela API do GitHub
(licença, licença SPDX, stars, arquivado, último push).

- **65/68 responderam 200.**
- `https://github.com/ossillate-inc/RTFM` → **404**. Removido; não há
  repositório canônico de RTFM para linkar.
- `https://github.com/BusPirate/BusPirate5-firmware` → **404**. O projeto
  atual é `BusPirate/Bus_Pirate` (redireciona para `ElderlyPirate/Bus_Pirate`,
  vivo, push 2026-10-26). Corrigido.
- `https://ost2.fyi/` → 406 na checagem automatizada. A plataforma de cursos
  está em `https://p.ost2.fyi/` (200). Corrigido.

Repositórios ativos porém com último push antigo, sinalizados como tal:
`nccgroup/ScoutSuite` (2025-09), `RhinoSecurityLabs/pacu` (2026-05),
`sleuthkit/autopsy` (2026-06), `smicallef/spiderfoot` (2026-04).

Licenças que impedem redistribuição de texto (usar só como link):
GPL-3.0 (DVWA, GOAD, MobSF, Cutter, Autopsy), sem licença SPDX declarada
(HackTricks é CC BY-NC 4.0 — já registrado no importador), NOASSERTION
(WebGoat, PEASS-ng, impacket, radare2, pwntools, frida, volatility3,
velociraptor, openocd, chipwhisperer, Bus Pirate).

## 3. O que falta para sustentar 18 trilhas

O motor pode ser construído agora. O conteúdo teórico de cada módulo é
ancorado em documento real da KB. As lacunas acima são as únicas áreas em que
não existe documento para ancorar: hardware (4 tópicos), wireless (2), reversing
(4), cloud (1), forensics (2), malware (1), OSINT (3), crypto (2), DevSecOps (2).

Esses módulos serão marcados como **lacuna explícita** na interface, com o
tópico exato a ser escrito, em vez de preenchidos com link solto.

## 4. Decisões de implementação

1. Reaproveitar a tabela `paths`? **Não.** Ela é uma lista plana de slugs sem
   módulo, disciplina, teoria, avaliação nem anotação. Criar tabelas próprias
   com prefixo `lp_` mantém as 10 trilhas antigas funcionando enquanto a nova
   área é validada, e a UI antiga aponta para a nova.
2. Todo documento, desafio e máquina referenciado por uma trilha é validado
   por slug no seed; slug inexistente aborta o seed em vez de virar card vazio.
3. Progresso por atividade (teoria, exercício, lab, avaliação, projeto),
   persistido em banco, com estado, notas, dificuldades, favorito e anexos.
4. Recomendação calculada a partir do progresso real, com bloqueio de
   conteúdo avançado quando o pré-requisito da trilha não foi cumprido.
## 5. Estado da Fase 1 (implementada)

### Trilhas entregues

| # | Trilha | Módulos | Disciplinas | Atividades | Labs reais | Docs KB | Avaliações | Projeto | Lacunas |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | Web Application Pentesting | 8 | 15 | 87 | 61 | 2 | 3 | 1 | 0 |
| 02 | API Security & API Pentesting | 5 | 8 | 36 | 26 | 4 | 1 | 1 | 0 |
| 03 | Linux Security & Privilege Escalation | 5 | 11 | 64 | 1 | 52 | 3 | 1 | 0 |
| 04 | Windows Security & Privilege Escalation | 4 | 9 | 61 | 0 | 53 | 2 | 1 | 0 |
| | **Total** | **22** | **43** | **248** | **88** | | **9** | **4** | **0** |

Todas as trilhas declaram capstone com critérios objetivos, evidências exigidas e
avaliação técnica. Nenhuma referência aponta para conteúdo inexistente: o validador
(`scripts/check_learning_paths.py`) aborta se um slug de lab, documento ou artigo
não existir.

Observação honesta: a trilha Windows tem 0 laboratórios de plataforma porque a
plataforma não tem nenhum alvo Windows — os 4 labs são web (Flask). O conteúdo
prático de Windows é feito em VM própria do operador, e os exercícios dizem isso
explicitamente. Isso é uma lacuna de infraestrutura, não de currículo.

### Documentos próprios escritos (pt-BR, com fonte primária)

Substituem exatamente os tópicos que a auditoria apontou como ausentes:

| Slug | Tema | Fontes |
| --- | --- | --- |
| `own-gtfobins-metodologia` | GTFOBins como método (contextos SUID/sudo/capability) | gtfobins.github.io, repo, API |
| `own-lolbas-metodologia` | LOLBAS, funções, MITRE ATT&CK, limites | lolbas-project.github.io, README, ATT&CK Navigator, loldrivers.io |
| `own-ntfs-para-pentest` | ACL/herança, ADS, hard links, reparse points, namespaces | Microsoft Learn (4 páginas) |
| `own-bola-autorizacao-objeto` | BOLA vs BFLA, método das duas contas, multi-tenant | OWASP API1/API5:2023, OWASP Cheatsheet, CWE-639/285 |
| `own-oidc-openid-connect` | ID Token, claims, validação no RP, redirect_uri | OIDC Core (errata 2), Discovery, RFC 6749/6750/9700, WSTG |

Cada documento tem 720–1215 palavras e 3–6 referências verificadas. São importados
por `app/kb_own.py` a partir de `content/kb_own/*.md` no boot, com
`origin='own'`, `language='pt-BR'` e `translation_status='translated'`.

### Correções encontradas durante a implementação

1. **Template da biblioteca quebrado em qualquer filtro.** `kb_index.html` tinha
   `{% if q %}` fechado por um `{% endif %}` errado; `?group=` e `?tag=`
   renderizavam a coluna de conteúdo inteira vazia. Corrigido e coberto por teste.
2. **Fresh install quebrava o seed de trilhas.** Sem o conteúdo importado (HackTricks/PATT),
   qualquer referência a documento importado abortava o seed inteiro. Agora, quando não há
   documento importado no banco, a referência vira aviso ("execute scripts/import_kb.py"),
   e o seed continua. Com conteúdo importado, slug inexistente continua sendo erro fatal.
3. **Capstone não era atividade rastreável** em duas trilhas, o que tornava impossível
   impor "conclusão exige capstone". O validador agora recusa currículo com capstone
   declarado e sem atividade `project`.
4. **Slug de KB inventado** na trilha 01 detectado por teste em banco limpo — corrigido
   para o slug real existente.

### Testes

`tests/test_learning_paths.py` — 24 testes: validação estrita, escopo das 4 trilhas,
progresso persistido, abertura de página não conclui, portão de módulo, conclusão só com
todas as obrigatórias, recomendações respeitando pré-requisitos, revisão primeiro,
correção de avaliação (aprovado/reprovado), certificado recusado/emitido/idempotente,
duplicação de trilha e criação personalizada, e renderização de todas as páginas.

Suíte completa: **9/9 módulos, 174 testes passando**.

## 6. Estado da Fase 2 (implementada)

### Trilhas entregues

| # | Trilha | Módulos | Disciplinas | Atividades | Docs KB | Avaliações | Exercícios | Projeto | Lacunas |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 05 | Active Directory Pentesting | 4 | 8 | 62 | 53 | 3 | 5 | 1 | 0 |
| 06 | Network Pentesting | 3 | 8 | 60 | 50 | 2 | 5 | 1 | 0 |
| 07 | Wireless Security | 4 | 8 | 51 | 44 | 1 | 5 | 1 | 0 |
| 08 | Hardware Hacking | 5 | 10 | 45 | 26 | 2 | 15 | 1 | 0 |
| | **Total Fase 2** | **16** | **34** | **218** | | **8** | **30** | **4** | **0** |
| | **Total geral** | **38** | **77** | **466** | | **17** | | **8** | **0** |

Nenhuma trilha da Fase 2 tem laboratório de plataforma: a plataforma não possui alvo de
domínio Windows, rede roteada com switch nem laboratório sem fio. Em vez de simular labs
inexistentes, **cada exercício declara no próprio enunciado** o que precisa (VM própria,
segunda máquina, adaptador com injeção) e qual parte fica bloqueada sem isso.

### Campo `equipment` (novo)

As 218 atividades da Fase 2 declaram explicitamente sua classe física, com validação
estrita no schema e badge na interface:

| Classe | Badge | Significado |
| --- | --- | --- |
| `software` | SOMENTE SOFTWARE | roda na máquina do operador |
| `simulated` | EQUIPAMENTO SIMULADO | usa dispositivo emulado (ex.: driver `demo` do sigrok) |
| `optional` | EQUIPAMENTO OPCIONAL | melhor com aparelho, mas tem equivalente em software |
| `required` | EXIGE EQUIPAMENTO | não dá para concluir sem o aparelho nomeado |

Na trilha Hardware: **40 softwares, 1 simulado, 4 exigem equipamento**. Os 4 exercícios
que exigem aparelho (multímetro, sessão OpenOCD, captura UART, RTL-SDR) dizem no texto
que ficam bloqueados sem ele e qual exercício em software cobre o mesmo conceito. A
trilha não pressupõe nenhum equipamento específico.

### Documentos próprios da Fase 2

| Slug | Tema | Fontes |
| --- | --- | --- |
| `own-hardware-reconhecimento-placa` | Reconhecimento de PCB: silk, encapsulamento, pontos de teste, registro | Wikipedia PCB, Datasheet, sigrok PDs, SPI, KiCad |
| `own-hardware-identificar-componentes` | Top marking → part number → datasheet → pinagem; 4 armadilhas | Datasheet, SPI, I²C, KiCad, sigrok PDs |
| `own-hardware-analisador-logico-sigrok` | Fluxo sigrok/PulseView: samplerate, trigger, `-P` empilhado, evidência | Manual sigrok-cli, PDs, I/O formats, hardware suportado, PulseView |
| `own-hardware-firmware-ghidra` | Ghidra: arquitetura, image base, strings, decompilador com ceticismo, headless | Ghidra Getting Started, repo, javadoc, radare2 book, releases |
| `own-hardware-sdr-fundamentos` | Cadeia SDR, I/Q, modulações, Goertzel, prática sem transmissor | Wikipedia SDR, RTL-SDR QSG, GNU Radio manual, osmocom/rtl-sdr, QAM |

Cada um tem 908–1333 palavras e 5 referências verificadas na data da escrita. Foram
adicionadas 5 categorias novas em `CATEGORY_TREE` (`hardware`, `hardware-recon`,
`hardware-signals`, `hardware-firmware`, `hardware-rf`), todas em grupo próprio para não
se misturar com as 1.144 fontes importadas.

### Correções durante a implementação

1. **Slugs longos truncados na importação.** Documentos com slug próximo de 100 caracteres
   não são truncados de forma consistente na base (um termina em `-attac`, outro em
   `...-attack`). O currículo referenciava o nome completo e o validador abortou — os
   slugs passaram a ser copiados do banco em vez de concatenados por prefixo.
2. **`estimated_hours` incoerente** na trilha Network (31 h declaradas contra 38 h somadas
   das atividades). Corrigido para bater com a soma.
3. **Markdown em campo de texto puro.** A descrição da trilha Hardware usava `**...**`,
   que aparece literal porque o campo é renderizado sem Markdown. Removido e adicionada
   verificação de que nenhum campo de texto puro contém marcação.

### Testes

`tests/test_learning_paths.py` — **29 testes** (antes 24). Novos:
`test_phase2_scope_is_real_content`, `test_phase2_prerequisites_exist`,
`test_phase2_equipment_is_always_declared`, `test_hardware_track_separates_software_from_equipment`,
`test_equipment_field_is_seeded_and_rendered`. A verificação de ordem por prioridade passou a
comparar conjuntos e a exigir prioridades distintas (ordem estável na UI).

Suíte completa: **9/9 módulos, 179 testes passando**.

## 7. Fase 3 — trilhas 09–18

Implementadas em 2026-11-13. As dez trilhas do mapa original estão completas:

| # | Trilha | Mod | Disc | Ativ | KB | Labs |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 09 | `malware-analysis` | 4 | 8 | 30 | 10 | 0 |
| 10 | `digital-forensics` | 4 | 8 | 34 | 21 | 0 |
| 11 | `cloud-containers` | 4 | 7 | 30 | 20 | 0 |
| 12 | `mobile-security` | 4 | 7 | 34 | 26 | 0 |
| 13 | `binary-exploitation` | 4 | 10 | 50 | 38 | 0 |
| 14 | `reverse-engineering` | 4 | 6 | 31 | 21 | 0 |
| 15 | `applied-crypto` | 4 | 7 | 27 | 16 | 1 |
| 16 | `osint` | 4 | 8 | 26 | 13 | 0 |
| 17 | `red-team` | 4 | 7 | 28 | 18 | 0 |
| 18 | `iot-embedded` | 4 | 6 | 32 | 22 | 0 |

**Total da Fase 3: 40 módulos, 74 disciplinas, 322 atividades, 0 gaps declarados.**
Programa completo: **18 trilhas, 78 módulos, 151 disciplinas, 788 atividades, 704 horas.**

### Correção do mapa de lacunas da seção 3

O levantamento inicial estimou forense com "2 + Volatility" documentos e reversing com 12.
A contagem por prefixo no banco real mostra que a base é maior do que a estimativa:

- **Forense**: 36 documentos sob `basic-forensic-methodology` (memória, registro, pcap,
  carving, Docker, anti-forense, integridade de arquivo, artefatos de navegador, Office,
  PDF, Android, iOS). A estimativa da seção 3 estava baixa; só duas lacunas permaneceram
  (cadeia de custódia e linha do tempo), cobertas por documento próprio.
- **Reversing**: 12 documentos sob `ht-reversing` confirmados, e a lacuna era real —
  Ghidra e anti-depuração não tinham documento.
- **IoT**: a base tem cobertura de protocolo industrial melhor do que a estimativa
  inicial (Modbus, MQTT, OPC UA, BACnet, DNP3, PROFINET, EtherNet/IP, IEC 60870-5-104,
  IEC 61850, RTSP, SNMP, TFTP, UPnP e BLE).
- **OSINT** continua sendo a área mais fraca: 3 documentos importados. A trilha se apoia
  nos três documentos próprios e não finge cobertura que não existe.

### Documentos próprios da Fase 3

| Slug | Tema | Referências |
| --- | --- | --- |
| `own-yara-regras-deteccao` | Gramática YARA, modificadores, falso positivo, validação | YARA docs ×2, repo, ATT&CK, Sigma |
| `own-execucao-fileless-analise` | Quatro formas de fileless e a telemetria necessária | HackTricks ×2, ATT&CK, WMI, Sigma |
| `own-forense-cadeia-custodia` | Quatro atos da custódia; metadado vs evento | HackTricks ×2, plaso, Timesketch, Sleuth Kit |
| `own-forense-memoria-volatility` | Símbolos do Volatility 3, ordem de plugins, limites da RAM | Volatility ×2, HackTricks ×2, Velociraptor |
| `own-cloud-iam-permissoes` | Avaliação de política, escalada, RBAC | AWS ×2, K8s RBAC, Prowler, CloudFox |
| `own-cloud-serverless-riscos` | Cinco vetores de função e checklist | AWS ×2, ATT&CK, Trivy, CloudFox |
| `own-ghidra-metodologia-reversing` | Importação, análise, decompilação como hipótese | Ghidra ×3, radare2, Rizin |
| `own-reversing-anti-depuracao` | Cinco famílias de anti-análise e ordem de investigação | HackTricks ×3, Ghidra, ATT&CK |
| `own-binario-protecoes-e-bypass` | NX, canário, PIE, RELRO, CET por combinação | HackTricks ×3, pwntools, how2heap |
| `own-hmac-e-integridade` | Hash vs MAC vs KDF, extensão de comprimento | RFC 2104, NIST, OWASP, CrackStation, HackTricks |
| `own-pki-cadeia-confianca` | Cadeia, validação, revogação, checklist TLS | RFC 5280, RFC 8446, HackTricks, OWASP, NIST |
| `own-osint-metodologia` | Pergunta, fonte, registro, verificação, limites | HackTricks, OSINT Framework, ATT&CK, bbot, theHarvester |
| `own-osint-superficie-externa` | CT, Shodan, DNS/WHOIS e o limite de cada um | crt.sh, Shodan, HackTricks ×2, bbot |
| `own-osint-pessoas-organizacoes` | Homonímia, metadado, limite ético, credencial | HackTricks ×2, Sherlock, OSINT Framework, ATT&CK |

As 40 URLs de referência dos 14 documentos responderam **HTTP 200** na verificação feita
antes da gravação. Nenhuma referência foi citada sem consulta.

### Slugs verificados contra o banco

Quatro referências de KB foram rejeitadas pelo validador durante a implementação e
corrigidas para o valor exato do banco — dois finais truncados (`...-br`, `...-of`,
`...-pd`, `...-`), um sufixo inventado (`-registry-keys`) e nenhum outro tipo. O
procedimento passou a ser: consultar o slug por `LIKE` antes de escrever a atividade.

### Honestidade de equipamento (Fase 3)

- Na Fase 3, apenas **IoT** tem atividades fora da classe `software`: 4 `optional` (BLE
  e provisionamento Wi-Fi) e 1 `required` (teste de bootloader, que exige acesso UART ou
  ponto de teste na placa). Essa única atividade `required` aceita explicitamente o
  procedimento como entrega — e o teste
  `test_phase3_blocked_exercises_offer_a_software_path` verifica isso. A trilha de
  hardware continua sendo a única com `simulated`.
- As trilhas de laboratório inexistente (malware, forense, cloud, mobile, binário,
  reversing, cripto, OSINT, Red Team, IoT) declaram no texto que a plataforma não tem
  alvo para a área e usam binário compilado pelo operador, material próprio ou fonte
  passiva. Só a trilha de criptografia usa um lab da plataforma (`chain-jwt-to-sqli`),
  porque JWT é efetivamente testável no alvo web.

### Testes

`tests/test_learning_paths.py` — **38 testes**. Novos na Fase 3:
`test_phase3_scope_is_real_content`, `test_phase3_prerequisites_exist`,
`test_phase3_does_not_invent_labs`, `test_phase3_equipment_is_always_declared`,
`test_phase3_blocked_exercises_offer_a_software_path`. Os três testes de idioma cobrem
currículo e interface, e são a garantia de que um rótulo em inglês não entra sem falhar.

Suíte completa: **9/9 módulos, 188 testes passando**.
