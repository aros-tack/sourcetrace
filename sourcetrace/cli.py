from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import check_report, load_source


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sourcetrace", description="Check that a report's quotations and numbers really come from its sources.")
    ap.add_argument("report", help="the report to check (text or markdown)")
    ap.add_argument("-s", "--source", action="append", required=True, help="a source file (txt, md, csv, html, docx, pdf); repeat for several")
    ap.add_argument("--min-chars", type=int, default=20, help="shortest quotation to check (default 20 characters)")
    ap.add_argument("--no-numbers", action="store_true", help="check quotations only")
    ap.add_argument("--years", action="store_true", help="also check four-digit years as numbers")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--version", action="version", version="%(prog)s " + __import__("sourcetrace").__version__)
    a = ap.parse_args(argv)
    try:
        report = Path(a.report).read_text(encoding="utf-8", errors="replace")
        sources = {Path(s).name: load_source(s) for s in a.source}
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"sourcetrace: {exc}", file=sys.stderr)
        return 2
    res = check_report(report, sources, min_chars=a.min_chars, ignore_years=not a.years, check_numbers=not a.no_numbers)
    if a.json:
        print(json.dumps(res.as_dict(), indent=2))
    else:
        for q in res.quotes:
            if q.status == "verbatim":
                continue
            print(f"line {q.quote.line}: QUOTE {q.status.upper()}: “{q.quote.text}”")
            if q.status == "altered":
                print(f"    closest in {q.source}: “{q.closest}” (similarity {q.similarity:.2f})")
        for n in res.numbers:
            if not n.traced:
                print(f"line {n.line}: NUMBER NOT FOUND IN SOURCES: {n.raw}  (it may be a calculation or invented)")
        ok_q = sum(q.status == "verbatim" for q in res.quotes)
        print(f"{ok_q}/{len(res.quotes)} quotations verbatim; {sum(n.traced for n in res.numbers)}/{len(res.numbers)} numbers traced; {res.problems} problem(s).")
    return 0 if res.problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
