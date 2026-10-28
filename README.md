# quotecheck

Check that a report's **quotations and numbers really come from its sources**.

When a person or an AI writes a report from documents, the usual failure is a quotation that is *almost* right, or a figure that appears nowhere in the sources.
`quotecheck` takes the report and the source files and tells you, line by line:

* every quotation that is **not word for word** in any source (and, for near-misses, the closest wording that *is* in the source);
* every number in the report that **cannot be found** in the sources (it may be a legitimate calculation, or it may be invented).

Example (illustrative output, invented data):

```
$ quotecheck report.md -s policy.pdf -s vendors.csv
line 11: QUOTE ALTERED: “Northwind Logistics Ltd is approved to handle personal data inside the EEA.”
    closest in policy.pdf: “northwind logistics ltd is cleared to handle personal data inside the eea.” (similarity 0.89)
line 24: NUMBER NOT FOUND IN SOURCES: 3,049,500  (it may be a calculation or invented)
6/7 quotations verbatim; 5/6 numbers traced; 2 problem(s).
```

Exit status is `0` when everything traces, `1` when there is a problem, `2` for a usage or file error, so it drops into a script or CI job.

## Install

```
pip install git+https://github.com/aros-tack/quotecheck
```

Python 3.11+ (tested on 3.11 and 3.13), standard library only. PDFs are read with `pdftotext` (poppler) if you have it; `.txt .md .csv .tsv .json .html .docx` need nothing extra.

## Use

```
quotecheck REPORT -s SOURCE [-s SOURCE ...] [--min-chars 20] [--no-numbers] [--years] [--json]
```

* A quotation is text in “curly”, "straight" or «guillemet» quotes of at least 20 characters and 4 words (code blocks and inline code are ignored).
* Matching ignores case, spacing, curly vs straight quotes, dash styles and line-break hyphenation — never the words themselves.
* Years, ISO dates, URLs and list markers are not treated as figures unless you pass `--years`.

## What it does *not* do

It checks **textual traceability only**. It cannot tell you whether a statement is true, whether a quotation is used fairly in context, or whether a calculation is right —
a number it cannot find is reported, not judged. A quotation that is verbatim can still be misleading. Treat a clean result as "the quoted words and stated figures are in the
sources", nothing more.

## Why it exists

It applies the same idea as the verification step of [ARIA](https://github.com/aros-tack), an autonomous personal assistant that checks its own reports for unsupported quotations and invented figures,
as a small standalone tool anyone can run.

## AI assistance

This project was written with AI assistance (Claude Code) on behalf of the `aros-tack` account, and is tested; the tests are in `tests/`. Contributions and bug reports are welcome.

## Support

Free and MIT-licensed. If it saves you time you can support the work at <https://ko-fi.com/P7A426ZPCE>. There is no paid tier and no tracking.
