#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import datetime


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str, force: bool = False) -> bool:
    ensure_parent(path)
    if path.exists() and not force:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def parse_inventory_from_project(project_text: str):
    lines = project_text.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## page/flow inventory"):
            start_idx = i + 1
            break
    items = []
    if start_idx is None:
        return items
    for j in range(start_idx, len(lines)):
        line = lines[j].rstrip()
        if line.startswith("## "):
            break
        if not line.strip().startswith("-"):
            continue
        # Expected formats like:
        # - Home: / — <notes>
        # - Sign in: /login — <notes>
        raw = line.lstrip("- ").strip()
        name = raw
        path = None
        notes = None
        # Try split by em dash
        parts_dash = [p.strip() for p in raw.split("—", 1)]
        if len(parts_dash) == 2:
            raw, notes = parts_dash[0], parts_dash[1]
        # Try split name:path
        parts_colon = [p.strip() for p in raw.split(":", 1)]
        if len(parts_colon) == 2:
            name, path = parts_colon[0], parts_colon[1]
        else:
            name = raw
        if not path:
            path = "/"
        items.append({"name": name, "path": path, "notes": notes or ""})
    return items


def generate_inventory(project_md: Path, out_path: Path, force: bool) -> bool:
    project_text = read_text(project_md)
    items = parse_inventory_from_project(project_text)
    # YAML content
    lines = ["# Page/Flow Inventory", f"# Generated {datetime.datetime.utcnow().isoformat()}Z", "items:"]
    if items:
        for it in items:
            lines.append(f"  - name: {it['name']}")
            lines.append(f"    path: {it['path']}")
            if it['notes']:
                # Escape colon in notes minimally by quoting
                notes = it['notes'].replace('"', '\\"')
                lines.append(f"    notes: \"{notes}\"")
            else:
                lines.append("    notes: \"\"")
    else:
        lines.extend([
            "  - name: Home",
            "    path: /",
            "    notes: \"\"",
        ])
    content = "\n".join(lines) + "\n"
    return write_file(out_path, content, force)


def generate_findings_csv(out_path: Path, force: bool) -> bool:
    header = (
        "id,title,severity,wcag,impact,component,pages,repro,"
        "recommendation,owner,status,created_at\n"
    )
    return write_file(out_path, header, force)


def generate_report(out_path: Path, force: bool) -> bool:
    content = f"""
# Accessibility Audit Report

Generated: {datetime.datetime.utcnow().isoformat()}Z

## Executive Summary
Summarize key accessibility risks, user impact, and priorities.

## Conformance Snapshot
- Target standard: WCAG 2.2 Level AA
- Overall status: <draft>

## Findings Overview
- See `data/findings.csv` for detailed issues.
- Severity distribution: <to be completed>

## Detailed Findings
Track individual issues in the CSV and/or your issue tracker. Include screenshots and repro steps.

## Recommendations
- Code patterns, component fixes, and design guidance.

## Verification Plan
- Re-test after fixes; update statuses in `data/findings.csv`.

## Appendix
- Methodology, tools, and scope defined in `PROJECT.md`.
""".lstrip()
    return write_file(out_path, content, force)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Accessibility report generator")
    parser.add_argument("--all", action="store_true", help="Generate all artifacts")
    parser.add_argument("--report", action="store_true", help="Generate report markdown")
    parser.add_argument("--inventory", action="store_true", help="Generate inventory YAML from PROJECT.md")
    parser.add_argument("--findings", action="store_true", help="Generate findings CSV template")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args(argv)

    project_md = ROOT / "PROJECT.md"
    out_report = ROOT / "docs" / "REPORT.md"
    out_inventory = ROOT / "data" / "inventory.yaml"
    out_findings = ROOT / "data" / "findings.csv"

    if not any([args.all, args.report, args.inventory, args.findings]):
        parser.print_help()
        return 1

    created = []

    if args.all or args.inventory:
        if generate_inventory(project_md, out_inventory, args.force):
            created.append(str(out_inventory))
    if args.all or args.findings:
        if generate_findings_csv(out_findings, args.force):
            created.append(str(out_findings))
    if args.all or args.report:
        if generate_report(out_report, args.force):
            created.append(str(out_report))

    if created:
        print("Generated:")
        for p in created:
            print(f" - {p}")
        return 0
    else:
        print("No files created (already exist). Use --force to overwrite.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

