"""Command line entry point.

    runbook-doctor docs/ README.md          # audit, exit 0 clean
    runbook-doctor .                        # every .md under the path
    runbook-doctor --fail-severity MEDIUM . # stricter gate
"""

import argparse
import json
import sys
from pathlib import Path

from .checks import check

SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="runbook-doctor",
        description="Staleness gate for runbooks: dead scripts, dead links, "
                    "undefined variables, TODO rot.")
    ap.add_argument("paths", nargs="+", help="markdown files or directories")
    ap.add_argument("--root", default=".", help="repo root for resolving refs")
    ap.add_argument("--fail-severity", default="HIGH",
                    choices=sorted(SEVERITY_ORDER, key=SEVERITY_ORDER.get),
                    help="exit 1 when a finding reaches this severity")
    ap.add_argument("--format", default="text", choices=["text", "json"])
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    docs = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            for q in p.rglob("*"):
                # Hidden trees (.git, .pytest_cache, .venv) are not runbooks.
                if any(part.startswith(".") for part in q.parts):
                    continue
                if q.suffix.lower() in (".md", ".markdown"):
                    docs.append(q.resolve())
        elif p.suffix.lower() in (".md", ".markdown"):
            docs.append(p.resolve())
        else:
            print("skipping non-markdown %s" % p, file=sys.stderr)
    docs = [d for d in dict.fromkeys(docs)]

    findings = []
    for doc in docs:
        findings.extend(check(doc, root))
    findings.sort(key=lambda f: (-SEVERITY_ORDER[f.severity], f.file, f.rule))

    if args.format == "json":
        print(json.dumps({"scanned": len(docs),
                          "findings": [f.__dict__ for f in findings]}, indent=2))
    else:
        for f in findings:
            print("%-6s %-14s %s" % (f.severity, f.rule, f.file))
            print("       %s" % f.detail)
        counts = {}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        print("%d markdown scanned, %d finding(s): %s"
              % (len(docs), len(findings),
                 ", ".join("%d %s" % (v, k) for k, v in sorted(counts.items()))
                 or "clean"))

    threshold = SEVERITY_ORDER[args.fail_severity]
    hot = [f for f in findings if SEVERITY_ORDER[f.severity] >= threshold]
    if hot:
        return 1
    if not docs:
        print("no markdown found under the given path(s)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
