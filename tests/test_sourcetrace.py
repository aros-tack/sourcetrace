import json, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

from sourcetrace.core import check_report, find_quotes, load_source, normalize, numbers_in
from sourcetrace.cli import main

SRC = {"policy.txt": ("Vendor review 2026.\nNorthwind Logistics Ltd is cleared to handle personal data inside the EEA.\n"
                      "Revenue for the year was R 4,250,000 and operating costs were R 1,200,500.\nHalvorsen Freight was removed from the approved list in March.\n")}


class Core(unittest.TestCase):
    def test_verbatim_quote_passes_even_with_curly_quotes_case_and_spacing(self):
        rep = "The policy says “Northwind Logistics Ltd is   cleared to handle personal data inside the EEA.”"
        r = check_report(rep, SRC)
        self.assertEqual([q.status for q in r.quotes], ["verbatim"])

    def test_altered_quote_is_flagged_with_the_closest_source_text(self):
        rep = 'It says "Northwind Logistics Ltd is approved to handle personal data inside the EU."'
        r = check_report(rep, SRC)
        self.assertEqual(r.quotes[0].status, "altered")
        self.assertIn("cleared to handle personal data", r.quotes[0].closest)

    def test_fabricated_quote_is_missing(self):
        r = check_report('The vendor "guarantees full compliance with every regulation worldwide" in writing.', SRC)
        self.assertEqual(r.quotes[0].status, "missing")
        self.assertEqual(r.problems >= 1, True)

    def test_short_phrases_and_code_are_not_treated_as_quotations(self):
        rep = 'Use the "approved list" label and `"some inline code that is long enough here"` as shown.\n```\n"a fenced block quote that is long enough to count"\n```\n'
        self.assertEqual(find_quotes(rep), [])

    def test_numbers_are_traced_to_the_sources_and_computed_ones_are_flagged(self):
        rep = "Revenue was R 4 250 000 (see policy), costs 1,200,500, so the margin is 3,049,500 and 42% grew."
        r = check_report(rep, SRC)
        traced = {n.raw: n.traced for n in r.numbers}
        self.assertTrue(traced["R 4 250 000"] and traced["1,200,500"])
        self.assertFalse(traced["3,049,500"])
        self.assertFalse(traced["42%"])

    def test_years_dates_urls_and_list_markers_are_not_numbers(self):
        rep = "1. In 2026 the check ran (2026-10-28) see https://example.org/a/12345\n2) Done."
        self.assertEqual(numbers_in(rep), [])

    def test_line_break_hyphenation_in_a_source_does_not_hide_a_quote(self):
        src = {"s.txt": "The supplier must keep full docu-\nmentation for seven years after the contract ends."}
        r = check_report('Quote: "must keep full documentation for seven years after the contract ends"', src)
        self.assertEqual(r.quotes[0].status, "verbatim")

    def test_normalize_keeps_the_words(self):
        self.assertNotEqual(normalize("approved"), normalize("not approved"))


class Readers(unittest.TestCase):
    def test_docx_and_html_are_read(self):
        d = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(d / "a.docx", "w") as z:
            z.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>Payments are made weekly via PayPal.</w:t></w:r></w:p></w:body></w:document>")
        (d / "b.html").write_text("<html><script>x=1</script><body><p>Workers in South Africa may apply.</p></body></html>")
        self.assertIn("Payments are made weekly via PayPal.", load_source(d / "a.docx"))
        self.assertIn("Workers in South Africa may apply.", load_source(d / "b.html"))
        self.assertNotIn("x=1", load_source(d / "b.html"))

    @unittest.skipUnless(shutil.which("pdftotext") and shutil.which("cupsfilter"), "needs poppler and cupsfilter")
    def test_pdf_is_read(self):
        d = Path(tempfile.mkdtemp())
        (d / "t.txt").write_text("Annual summary\nRevenue for the year was R 4,250,000.\n")
        (d / "t.pdf").write_bytes(subprocess.run(["cupsfilter", str(d / "t.txt")], capture_output=True).stdout)
        self.assertIn("Revenue for the year was R 4,250,000", " ".join(load_source(d / "t.pdf").split()))

    def test_unsupported_type_is_an_error_not_a_pass(self):
        d = Path(tempfile.mkdtemp())
        (d / "x.bin").write_bytes(b"\x00")
        with self.assertRaises(RuntimeError):
            load_source(d / "x.bin")


class Cli(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "src.txt").write_text(SRC["policy.txt"])

    def test_exit_codes_and_json(self):
        (self.d / "ok.md").write_text('"Halvorsen Freight was removed from the approved list in March."')
        (self.d / "bad.md").write_text('"Halvorsen Freight was added to the approved list in March."')
        self.assertEqual(main([str(self.d / "ok.md"), "-s", str(self.d / "src.txt")]), 0)
        self.assertEqual(main([str(self.d / "bad.md"), "-s", str(self.d / "src.txt"), "--json"]), 1)
        self.assertEqual(main([str(self.d / "missing.md"), "-s", str(self.d / "src.txt")]), 2)


class Examples(unittest.TestCase):
    """The shipped example is what docs/guide.md shows; if the tool's behaviour drifts this fails."""

    def test_example_matches_the_guide(self):
        root = Path(__file__).resolve().parents[1]
        rep = (root / "examples" / "report.md").read_text()
        src = {"policy.txt": (root / "examples" / "policy.txt").read_text()}
        r = check_report(rep, src)
        self.assertEqual([q.status for q in r.quotes], ["altered", "verbatim"])
        self.assertEqual([(n.raw, n.traced) for n in r.numbers], [("R 4,250,000", True), ("R 1,200,500", True), ("R 3,049,500", False)])
        self.assertEqual(r.problems, 2)
        self.assertGreaterEqual(r.quotes[0].similarity, 0.9)
        guide = (root / "docs" / "guide.md").read_text()
        self.assertIn("1/2 quotations verbatim; 2/3 numbers traced; 2 problem(s).", guide)


if __name__ == "__main__":
    unittest.main()
