#!/usr/bin/env python3
"""Learning Paths — Fase 3 (trilhas 09–18).

Trilhas independentes e opcionais: cada uma exige apenas os pré-requisitos
declarados, e nenhuma trava a conclusão do programa da Fase 1/2.

Regras seguidas por todas as trilhas desta fase (as mesmas da Fase 2):

* Todo destino (``kb_slug``/``academy_slug``/``challenge_slug``) é lido do banco
  real — nenhum slug é inventado.
* Quando o assunto não tem documento na base, a atividade declara ``gap`` e o
  texto diz o que falta. Não se escreve conteúdo falso para preencher.
* A plataforma não tem laboratório para malware, forense, cloud, mobile, binário,
  reversing, criptografia, OSINT, Red Team nem IoT. Onde aparece ``lab``, o slug
  é de um alvo web/platforma que de fato existe; o restante é exercício guiado
  sobre material que o operador já tem na máquina.
* Todo texto visível é pt-BR; só termos técnicos (nomes de ferramenta, ataque,
  protocolo, sigla) permanecem em inglês.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lp_builders import default_equipment  # noqa: E402

OUT = ROOT / "content" / "learning_paths"


def emit(filename: str, path: dict) -> None:
    default_equipment(path, "software")
    dest = OUT / filename
    dest.write_text(json.dumps(path, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mods = len(path["modules"])
    units = sum(len(m["units"]) for m in path["modules"])
    acts = sum(len(u["activities"]) for m in path["modules"] for u in m["units"])
    print(f"escrito: {dest.name}  {mods} módulos / {units} unidades / {acts} atividades")