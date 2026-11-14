#!/usr/bin/env python3
"""Import an upstream source into the REDVAULT knowledge base.

    # first time: clone the source somewhere outside the project.
    # HackTricks keeps translated editions on per-language branches: `pt` is
    # Brazilian Portuguese (that is the edition we import by default).
    git clone --depth 1 https://github.com/swisskyrepo/PayloadsAllTheThings /tmp/patt
    git clone --depth 1 --branch pt https://github.com/HackTricks-wiki/hacktricks /tmp/hacktricks-pt

    python3 scripts/import_kb.py --source payloads-all-the-things --path /tmp/patt
    python3 scripts/import_kb.py --source hacktricks --path /tmp/hacktricks-pt --rebuild-index

The importer refuses permissive-only sources that do not allow redistribution.
HackTricks (CC BY-NC 4.0) is imported only under its non-commercial terms with
attribution; see app/kb_hacktricks.py for the full rationale.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("REDVAULT_DATA", str(ROOT / "data"))

from app.database import SessionLocal, init_db  # noqa: E402
from app.kb_hacktricks import import_hacktricks  # noqa: E402
from app.kb_import import ImportRefused, import_payloads_all_the_things, register_sources  # noqa: E402
from app.kb_search import rebuild  # noqa: E402
from app.kb_seed import seed_all  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        choices=["payloads-all-the-things", "hacktricks"],
        default="payloads-all-the-things",
        help="qual fonte importar",
    )
    parser.add_argument("--path", required=True, help="clone local do repositório upstream")
    parser.add_argument(
        "--language",
        default=None,
        help="idioma do conteúdo (pt-BR, en). Padrão: detectado pela branch do clone.",
    )
    parser.add_argument("--rebuild-index", action="store_true", help="reindexa a busca FTS5")
    args = parser.parse_args(argv)

    init_db()
    with SessionLocal() as db:
        register_sources(db)
        path = Path(args.path).resolve()
        try:
            if args.source == "hacktricks":
                stats = import_hacktricks(db, path, language=args.language)
            else:
                stats = import_payloads_all_the_things(db, path)
        except (ImportRefused, ValueError) as exc:
            print(f"importação recusada: {exc}", file=sys.stderr)
            return 2
        seed = seed_all(db)
        db.commit()
        print(
            f"fonte: {args.source}\n"
            f"categorias canônicas: {seed['categories']}\n"
            f"payloads extraídos: {seed['payloads']}\n"
            f"labs vinculados: {seed['challenge_links']}"
        )
        print(
            f"documentos criados: {stats['created']}\n"
            f"categorias: {stats['categories']}\n"
            f"atualizados (upsert): {stats.get('updated', 0)}\n"
            f"marcados para revisão: {stats.get('flagged', 0)}\n"
            f"preservados (revisados): {stats.get('skipped_reviewed', stats.get('skipped', 0))}"
        )
        if "images" in stats:
            print(f"imagens localizadas: {stats['images']}")

    if args.rebuild_index:
        total = rebuild()
        print(f"índice de busca: {total} documentos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))