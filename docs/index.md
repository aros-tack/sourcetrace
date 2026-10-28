---
title: sourcetrace — check that a report's quotes and numbers come from its sources
description: A small open-source command-line tool that flags altered quotations and untraceable numbers in a report, by checking them against the source documents (txt, md, csv, html, docx, pdf).
---

# sourcetrace

**Does every quotation in this report appear, word for word, in its sources — and does every figure?**

`sourcetrace` answers that for a report you wrote, or one an AI wrote for you. It prints each altered quotation (with the closest wording that *is* in the source) and each number it cannot find.

```
$ sourcetrace report.md -s policy.pdf -s vendors.csv
line 3: QUOTE ALTERED: “Northwind Logistics Ltd is approved to handle personal data inside the EU.”
    closest in policy.txt: “northwind logistics ltd is cleared to handle personal data inside the eea.” (similarity 0.93)
line 5: NUMBER NOT FOUND IN SOURCES: R 3,049,500  (it may be a calculation or invented)
1/2 quotations verbatim; 2/3 numbers traced; 2 problem(s).
```

* Free and MIT-licensed, Python 3.11+, no dependencies. Exit code 0 / 1 / 2 for scripts and CI.
* It checks **traceability only** — not whether a statement is true or fairly used.
* Install: `pip install https://github.com/aros-tack/sourcetrace/releases/download/v0.2.0/sourcetrace-0.2.0-py3-none-any.whl`

## Read next

* [How to check a report against its sources — a short practical guide](guide)
* [Source code, issues and releases on GitHub](https://github.com/aros-tack/sourcetrace)

*Related tool for quotations only: [quotecheck](https://github.com/sandovabarbora/quotecheck) by another author. sourcetrace was written with AI assistance and is tested.*
