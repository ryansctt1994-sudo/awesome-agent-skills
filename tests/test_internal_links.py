"""Regression fixtures for offline Markdown relative-link auditing."""
import tempfile
import unittest
from pathlib import Path

from scripts.check_internal_links import scan, anchors


class InternalLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, text):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def test_html_summary_heading_and_unicode(self):
        self.write("README.md", '<summary><h3>Skills by Vercel Engineering Team</h3></summary>\n'
                   '## 🤝 Contributing\n')
        self.write("index.md", '[one](README.md#skills-by-vercel-engineering-team)\n'
                   '[two](README.md#-contributing)\n')
        # GitHub strips emoji before slugging, leaving the separating space.
        self.assertEqual(scan(self.root), [])

    def test_missing_file_and_anchor_both_fail(self):
        self.write("index.md", '[missing](nowhere.md)\n[anchor](#absent)\n')
        errors = scan(self.root)
        self.assertEqual(len(errors), 2)

    def test_explicit_custom_anchor(self):
        self.write("README.md", '<a id="custom-key"></a>\n[go](#custom-key)\n')
        self.assertEqual(scan(self.root), [])

    def test_duplicate_heading_suffixes(self):
        self.assertIn("repeat", anchors("# Repeat\n# Repeat"))
        self.assertIn("repeat-1", anchors("# Repeat\n# Repeat"))
        self.write("README.md", "# Repeat\n# Repeat\n[go](#repeat-1)\n")
        self.assertEqual(scan(self.root), [])

    def test_code_fence_links_are_not_interpreted(self):
        self.write("README.md", '```markdown\n[example](missing.md)\n```\n')
        self.assertEqual(scan(self.root), [])

    def test_shorter_inner_fence_does_not_expose_code_links(self):
        self.write("README.md", "~~~~markdown\n[example](missing.md)\n~~~\n"
                   "[still-code](also-missing.md)\n~~~~\n# Real\n[ok](#real)\n")
        self.assertEqual(scan(self.root), [])

    def test_different_fence_marker_cannot_close_block(self):
        self.write("README.md", "~~~~markdown\n```\n[example](missing.md)\n"
                   "# Hidden Heading\n~~~~\n[bad](#hidden-heading)\n")
        errors = scan(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing anchor", errors[0])

    def test_shorter_backticks_do_not_close_longer_backtick_block(self):
        self.write("README.md", "````md\n```\n[bad](missing.md)\n````\n")
        self.assertEqual(scan(self.root), [])

    def test_absolute_traversal_is_rejected(self):
        self.write("README.md", '[escape](../outside.md)\n')
        self.assertTrue(any("escapes" in x for x in scan(self.root)))


if __name__ == '__main__':
    unittest.main()
