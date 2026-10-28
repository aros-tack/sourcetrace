"""Core checks.  Standard library only (PDF needs the `pdftotext` tool from poppler, if you have PDFs).

What it verifies is *textual traceability*: is each quotation present, word for word, in one of the sources, and does each number
the report states occur in a source?  It does not judge whether a statement is true or well reasoned.
"""
from __future__ import annotations

import difflib
import html.parser
import re
import shutil
import subprocess
import unicodedata
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

_QUOTE_PAIRS = (("“", "”"), ('"', '"'), ("«", "»"))
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_APOS = dict.fromkeys(map(ord, "‘’‛ʼ"), "'")
_DQ = dict.fromkeys(map(ord, "“”„«»"), '"')


def normalize(text: str) -> str:
    """Case, spacing, curly quotes, dashes and line-break hyphenation are ignored; the words themselves are not."""
    t = unicodedata.normalize("NFKC", text).replace("­", "")
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)           # exam-\nple -> example
    t = t.translate(_DASHES).translate(_APOS).translate(_DQ)
    return " ".join(t.lower().split())


class _Text(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def load_source(path: str | Path) -> str:
    p = Path(path)
    suf = p.suffix.lower()
    if suf in (".txt", ".md", ".csv", ".tsv", ".json", ".log", ".rst", ""):
        return p.read_text(encoding="utf-8", errors="replace")
    if suf in (".html", ".htm"):
        t = _Text()
        t.feed(p.read_text(encoding="utf-8", errors="replace"))
        return "".join(t.out)
    if suf == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:tab/>", " ", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    if suf == ".pdf":
        exe = shutil.which("pdftotext")
        if not exe:
            raise RuntimeError("reading PDFs needs the 'pdftotext' tool (poppler); install it or convert the PDF to text")
        r = subprocess.run([exe, "-layout", str(p), "-"], capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise RuntimeError(f"pdftotext failed on {p.name}: {r.stderr.strip()[:200]}")
        return r.stdout
    raise RuntimeError(f"unsupported source type: {suf}")


@dataclass
class Quote:
    text: str
    line: int


@dataclass
class QuoteResult:
    quote: Quote
    status: str                       # verbatim | altered | missing
    source: str = ""
    closest: str = ""
    similarity: float = 0.0


@dataclass
class NumberResult:
    raw: str
    line: int
    traced: bool


@dataclass
class Report:
    quotes: list[QuoteResult] = field(default_factory=list)
    numbers: list[NumberResult] = field(default_factory=list)

    @property
    def problems(self) -> int:
        return sum(q.status != "verbatim" for q in self.quotes) + sum(not n.traced for n in self.numbers)

    def as_dict(self) -> dict:
        return {"ok": self.problems == 0,
                "quotes": [{"line": q.quote.line, "text": q.quote.text, "status": q.status, "source": q.source,
                            "closest_source_text": q.closest, "similarity": round(q.similarity, 3)} for q in self.quotes],
                "numbers": [{"line": n.line, "text": n.raw, "traced": n.traced} for n in self.numbers]}


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"`[^`\n]*`", " ", text)


def find_quotes(report: str, min_chars: int = 20, min_words: int = 4) -> list[Quote]:
    found: list[Quote] = []
    for n, line in enumerate(_strip_code(report).splitlines(), 1):
        for op, cl in _QUOTE_PAIRS:
            pat = re.escape(op) + r"([^" + re.escape(op + cl) + r"\n]{%d,400})" % min_chars + re.escape(cl)
            for m in re.finditer(pat, line):
                t = m.group(1).strip()
                if len(t.split()) >= min_words and t not in {q.text for q in found if q.line == n}:
                    found.append(Quote(t, n))
    return found


_NUM = re.compile(r"(?<![\w.,])(?:[$€£R]\s?)?\d{1,3}(?:[, ]\d{3})+(?:\.\d+)?%?|(?<![\w.,])(?:[$€£R]\s?)?\d+(?:\.\d+)?%?(?![\w])")


def _value(raw: str) -> Decimal | None:
    s = re.sub(r"[^\d.]", "", raw.replace(",", "").replace(" ", ""))
    try:
        return Decimal(s).normalize() if s else None
    except InvalidOperation:
        return None


def numbers_in(text: str, ignore_years: bool = True) -> list[tuple[str, int, Decimal]]:
    out = []
    for n, line in enumerate(_strip_code(text).splitlines(), 1):
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line)          # list markers are not figures
        line = re.sub(r"https?://\S+|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/:]\d{1,2}(?:[/:]\d{2,4})?\b", " ", line)
        for m in _NUM.finditer(line):
            v = _value(m.group(0))
            if v is None:
                continue
            if ignore_years and re.fullmatch(r"(?:19|20)\d\d", m.group(0).strip()):
                continue
            out.append((m.group(0).strip(), n, v))
    return out


def _best_span(q_norm: str, seg: str, centre: int) -> tuple[str, float]:
    """The word-aligned stretch of ``seg`` near ``centre`` that best matches the quotation."""
    span = len(q_norm)
    starts = [m.start() for m in re.finditer(r"(?<!\S)\S", seg) if abs(m.start() - centre) <= 40]
    ends = [m.end() for m in re.finditer(r"\S+", seg)]
    best, ratio = "", 0.0
    for a in starts:
        for e in ends:
            if not (span - 12 <= e - a <= span + 12):
                continue
            r = difflib.SequenceMatcher(None, q_norm, seg[a:e], autojunk=False).ratio()
            if r > ratio:
                best, ratio = seg[a:e], r
    return best, ratio


def _closest(q_norm: str, src_norm: str) -> tuple[str, float]:
    words = sorted(set(re.findall(r"[a-z0-9']{5,}", q_norm)), key=len, reverse=True)[:3] or q_norm.split()[:1]
    best, ratio = "", 0.0
    span = len(q_norm)
    for w in words:
        start, hits = 0, 0
        while hits < 40:
            i = src_norm.find(w, start)
            if i < 0:
                break
            lo, hi = max(0, i - span - 40), min(len(src_norm), i + span + 40)
            seg = src_norm[lo:hi]
            centre = max(0, (i - lo) - q_norm.find(w))
            cand, r = _best_span(q_norm, seg, centre)
            if r > ratio:
                best, ratio = cand, r
            start, hits = i + len(w), hits + 1
    return best, ratio


def check_report(report_text: str, sources: dict[str, str], *, min_chars: int = 20, ignore_years: bool = True,
                 check_numbers: bool = True) -> Report:
    """``sources``: name -> text.  Quotations must appear verbatim (after normalisation); numbers must occur in some source."""
    norm = {name: normalize(t) for name, t in sources.items()}
    res = Report()
    for q in find_quotes(report_text, min_chars=min_chars):
        qn = normalize(q.text)
        hit = next((n for n, s in norm.items() if qn in s), "")
        if hit:
            res.quotes.append(QuoteResult(q, "verbatim", hit, "", 1.0))
            continue
        best, ratio, src = "", 0.0, ""
        for name, s in norm.items():
            b, r = _closest(qn, s)
            if r > ratio:
                best, ratio, src = b, r, name
        res.quotes.append(QuoteResult(q, "altered" if ratio >= 0.85 else "missing", src if ratio >= 0.85 else "", best if ratio >= 0.85 else "", ratio))
    if check_numbers:
        src_vals = {v for t in sources.values() for _r, _n, v in numbers_in(t, ignore_years=False)}
        for raw, line, v in numbers_in(report_text, ignore_years=ignore_years):
            res.numbers.append(NumberResult(raw, line, v in src_vals))
    return res
