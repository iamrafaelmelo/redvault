#!/usr/bin/env python3
"""Validate every learning-path curriculum and report coverage.

Usage:
    python3 scripts/check_learning_paths.py          # validate + summary
    python3 scripts/check_learning_paths.py --strict # exit 1 on warnings too

Run this after editing anything under ``content/learning_paths/``. It fails with
a precise path when a curriculum points at a lab, KB document or Academy article
that does not exist.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.kb_import import register_sources  # noqa: E402
from app.kb_own import sync_own_documents  # noqa: E402
from app.kb_seed import seed_categories  # noqa: E402
from app.lp_schema import CurriculumError  # noqa: E402
from app.lp_seed import validate_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="tratar avisos como erro")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        register_sources(db)
        seed_categories(db)
        sync_own_documents(db)
        db.commit()
    with SessionLocal() as db:
        try:
            docs, warnings = validate_all(db)
        except CurriculumError as exc:
            print(f"ERRO: {exc}")
            return 1

    print(f"Trilhas válidas: {len(docs)}")
    total_acts = 0
    for doc in docs:
        from app.lp_schema import collect_stats

        s = collect_stats(doc)
        total_acts += s["activities"]
        kinds = " ".join(f"{k}={v}" for k, v in sorted(s["by_kind"].items()))
        print(
            f"  {doc['slug']:32} F{doc.get('phase', 1)} "
            f"mod={s['modules']:2} uni={s['units']:3} act={s['activities']:3} "
            f"labs={s['labs']:2} kb={s['kb_docs']:3} gaps={s['gaps']}  {kinds}"
        )
    print(f"Total de atividades: {total_acts}")

    if warnings:
        print(f"\n{len(warnings)} aviso(s):")
        for w in warnings:
            print(f"  - {w}")
        if args.strict:
            return 1
    else:
        print("\nSem avisos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())