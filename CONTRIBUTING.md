# Contributing

Bug reports and small, tested improvements are welcome.

* Run the tests: `python -m unittest discover -s tests -t .` (no dependencies; PDFs need `pdftotext` for the one PDF test, which is skipped without it).
* Keep it dependency-free and keep the promise in the README: it checks textual traceability only.
* A change that alters what is flagged needs a test in `tests/test_sourcetrace.py` and, if it changes the shipped example, the matching text in `docs/guide.md`.
* Contributions are accepted under the MIT licence.

This project is maintained by an AI-assisted workflow (see the README). Please say if a report or patch came from an AI tool.
