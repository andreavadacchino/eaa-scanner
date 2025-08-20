#!/usr/bin/env python3
import csv
import sys
from pathlib import Path


REQUIRED_COLUMNS = [
    "id",
    "title",
    "severity",
    "wcag",
    "impact",
    "component",
    "pages",
    "repro",
    "recommendation",
    "owner",
    "status",
    "created_at",
]

SEVERITIES = {"Critical", "High", "Medium", "Low"}
STATUSES = {"open", "in_progress", "fixed", "verified", "wontfix"}


def validate(csv_path: Path) -> int:
    if not csv_path.exists():
        print(f"File non trovato: {csv_path}", file=sys.stderr)
        return 2

    errors = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            print("Colonne mancanti:", ", ".join(missing))
            return 1
        for i, row in enumerate(reader, start=2):  # row numbers incl. header
            sev = row.get("severity", "").strip()
            if sev and sev not in SEVERITIES:
                print(f"Riga {i}: severità non valida '{sev}' (ammessi: {sorted(SEVERITIES)})")
                errors += 1
            status = row.get("status", "").strip()
            if status and status not in STATUSES:
                print(f"Riga {i}: status non valido '{status}' (ammessi: {sorted(STATUSES)})")
                errors += 1
            title = row.get("title", "").strip()
            if not title:
                print(f"Riga {i}: 'title' mancante")
                errors += 1
            wcag = row.get("wcag", "").strip()
            if not wcag:
                print(f"Riga {i}: 'wcag' mancante (es. 'WCAG 2.2 - 1.3.1')")
                errors += 1

    if errors:
        print(f"\nValidazione: {errors} problema/i trovati")
        return 1
    print("Validazione: OK")
    return 0


def main(argv=None):
    args = sys.argv[1:]
    if not args:
        print("Uso: python3 tools/validate.py data/findings.csv")
        return 2
    return validate(Path(args[0]))


if __name__ == "__main__":
    sys.exit(main())

