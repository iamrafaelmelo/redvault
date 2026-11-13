#!/usr/bin/env python3
"""Import an upstream source into the REDVAULT knowledge base.

    # first time: clone the source somewhere outside the project
    git clone --depth 1 https://github.com/swisskyrepo/PayloadsAllTheThings /tmp/patt

    python3 scripts/import_kb.py --path /tmp/patt
    python3 scripts/import_kb.py --path /tmp/patt --rebuild-index

The importer refuses sources that do not allow redistribution.
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
from app.kb_import import ImportRefused, import_payloads_all_the_things, register_sources  # noqa: E402
from app.kb_search import rebuild  # noqa: E402
from app.kb_seed import seed_all  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="clone local do PayloadsAllTheThings")
    parser.add_argument("--rebuild-index", action="store_true", help="reindexa a busca FTS5")
    args = parser.parse_args(argv)

    init_db()
    with SessionLocal() as db:
        register_sources(db)
        try:
            stats = import_payloads_all_the_things(db, Path(args.path).resolve())
        except ImportRefused as exc:
            print(f"importação recusada: {exc}", file=sys.stderr)
            return 2
        seed = seed_all(db)
        db.commit()
        print(
            f"categorias canônicas: {seed['categories']}\n"
            f"payloads extraídos: {seed['payloads']}\n"
            f"labs vinculados: {seed['challenge_links']}"
        )
        print(
            f"documentos criados: {stats['created']}\n"
            f"categorias: {stats['categories']}\n"
            f"atualizados (upsert): {stats['updated']}\n"
            f"marcados para revisão: {stats['flagged']}\n"
            f"preservados (revisados): {stats['skipped_reviewed']}"
        )

    if args.rebuild_index:
        total = rebuild()
        print(f"índice de busca: {total} documentos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))