# Checking a report against its sources

A short practical guide for anyone who writes — or receives — reports built from documents. It goes with the open-source tool [quotecheck](../README.md).
*The first draft was written by ARIA's local model and then edited and checked by an engineer; every command and output below was run for real (see `examples/`).*

## Why reports go wrong

Two errors account for most trouble in reports written from documents. A **quotation is almost right**: one word changed, "cleared" turned into "approved", and the meaning has moved. And a **figure appears that is in none of the sources**: it may be a calculation, a typo or an invention.
Readers rarely catch either, because both fit the flow of the argument. Checking them by eye means re-reading every source; a mechanical check does it in a second.

## What a mechanical check can and cannot tell you

A tool can check **textual traceability**: is the quoted text word for word in a source, and does a stated number occur in a source? It cannot tell you whether a statement is true, whether a quotation is used fairly in context, or whether a calculation is right.
A clean result means only that the quoted words and stated figures are in the sources you supplied. Treat it as the floor of checking, not the whole of it.

## A five-step routine

1. **Gather the exact sources** the report claims to use — the same files, not newer copies.
2. **Run the check:** `quotecheck REPORT -s SOURCE [-s SOURCE ...]`.
3. **Fix every altered or missing quotation.** Paste the source wording back in, or drop the quotation. A "missing" quotation (no close match anywhere) deserves the most suspicion.
4. **Decide for each untraced number.** If it is a calculation, show the working next to it; if you cannot say where it came from, remove it.
5. **Read for meaning.** Every word and figure is now traceable; whether they are used fairly and the conclusion follows is still your judgement.

## A worked example

The files in `examples/` are invented. `policy.txt` says: *"Northwind Logistics Ltd is cleared to handle personal data inside the EEA."* The draft `report.md` says "approved" and "EU" instead, and states a margin that is not in the policy.

```
$ quotecheck examples/report.md -s examples/policy.txt
line 3: QUOTE ALTERED: “Northwind Logistics Ltd is approved to handle personal data inside the EU.”
    closest in policy.txt: “northwind logistics ltd is cleared to handle personal data inside the eea.” (similarity 0.93)
line 5: NUMBER NOT FOUND IN SOURCES: R 3,049,500  (it may be a calculation or invented)
1/2 quotations verbatim; 2/3 numbers traced; 2 problem(s).
```

The second quotation was word for word and passed. The first is fixed by restoring the source wording. The margin R 3,049,500 is revenue minus costs (R 4,250,000 − R 1,200,500): a legitimate calculation, so the right fix is to say so in the report, not to delete it.

## Sources it can read

`.txt .md .csv .tsv .json .html .docx`, and PDFs through `pdftotext` (poppler). Matching ignores case, spacing, curly versus straight quotes, dash styles and line-break hyphenation.
A scanned PDF with no text layer cannot be read — run OCR first. Tables are read as the text they produce, so a figure split across lines may not match.

## One-page checklist

- Use the exact source files the report was written from.
- Run `quotecheck` and read every line it prints.
- Fix each ALTERED quotation by restoring the source's words.
- Treat each MISSING quotation as unsupported until you find where it came from.
- For each untraced number: a calculation (show the working) or unsupported (remove it).
- Remember a clean run means "traceable", not "true".
- Check that verbatim quotations are not misleading in context.
- Keep the command and its output with the report as a record of what was checked.
