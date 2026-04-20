#!/usr/bin/env python3

import os
import sqlite3
import sys
from pathlib import Path


EXPECTED_DB_FILES = {
    "term_db.sqlite3": ["term", "term2term"],
    "weight_db.sqlite3": ["weight"],
    "taxid_db_wP.sqlite3": ["taxid"],
    "estimate.sqlite3": ["AllSifterData", "ErrorHistogramBars", "Percentiles"],
    "idmap_db.sqlite3": ["idmap"],
    "pfam_db.sqlite3": ["pfam"],
    "sifter_results_cmp_050715.sqlite3": ["sifter_results"],
    "sifter_results_cmp_ready_leaves_050715.sqlite3": ["sifter_results"],
}


def get_env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser().resolve()


def check_sqlite_tables(db_path: Path, expected_tables: list[str]) -> tuple[bool, str]:
    try:
        connection = sqlite3.connect(str(db_path))
    except sqlite3.Error as exc:
        return False, f"failed to open sqlite db: {exc}"

    try:
        cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
    except sqlite3.Error as exc:
        return False, f"failed to inspect sqlite schema: {exc}"
    finally:
        connection.close()

    missing = [table for table in expected_tables if table not in tables]
    if missing:
        return False, "missing tables: " + ", ".join(missing)
    return True, "ok"


def print_status(prefix: str, path: Path, detail: str) -> None:
    print(f"{prefix:<8} {path} {detail}")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    db_dir = get_env_path("SIFTER_DB_DIR", str(repo_root / "my_dbs"))
    input_dir = get_env_path("SIFTER_INPUT_DIR", str(repo_root / "sifter_web" / "input"))
    output_dir = get_env_path("SIFTER_OUTPUT_DIR", str(repo_root / "sifter_web" / "output"))

    print(f"repo_root: {repo_root}")
    print(f"db_dir:    {db_dir}")
    print(f"input_dir: {input_dir}")
    print(f"output_dir:{output_dir}")
    print("")

    failures = 0

    if not db_dir.exists():
        print_status("MISSING", db_dir, "directory does not exist")
        return 1

    temp_files = sorted(path.name for path in db_dir.iterdir() if path.name.startswith("."))
    if temp_files:
        failures += 1
        print_status("PARTIAL", db_dir, "temporary copy files present: " + ", ".join(temp_files))

    for filename, tables in EXPECTED_DB_FILES.items():
        db_path = db_dir / filename
        if not db_path.exists():
            failures += 1
            print_status("MISSING", db_path, "expected sqlite file not found")
            continue
        if db_path.stat().st_size == 0:
            failures += 1
            print_status("INVALID", db_path, "file is empty")
            continue

        ok, detail = check_sqlite_tables(db_path, tables)
        if ok:
            print_status("OK", db_path, detail)
        else:
            failures += 1
            print_status("INVALID", db_path, detail)

    for path in (input_dir, output_dir):
        if path.exists() and path.is_dir():
            print_status("OK", path, "directory exists")
        else:
            failures += 1
            print_status("MISSING", path, "directory missing")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
