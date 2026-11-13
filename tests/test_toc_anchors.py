import unittest
from scripts.check_toc_anchors import anchors, unresolved_fragments


class TocAnchorsTests(unittest.TestCase):
    def test_md_headings_and_manual_named_anchors(self):
        md = '[One](#one) [Two](#two)\n\n## One\n<a name="two"></a>\n<details><summary>Two</summary></details>\n'
        self.assertEqual(unresolved_fragments(md), [])

    def test_missing_target_is_reported(self):
        self.assertEqual(unresolved_fragments('[Broken](#does-not-exist)\n## Other'), ['does-not-exist'])

    def test_duplicate_markdown_headings_get_numbered(self):
        self.assertTrue({'repeat', 'repeat-1'} <= anchors('## Repeat\n## Repeat'))
        self.assertEqual(unresolved_fragments('[Again](#repeat-1)\n## Repeat\n## Repeat'), [])

    def test_percent_encoded_fragments_are_decoded(self):
        self.assertEqual(unresolved_fragments('[Go](#hello%20world)\n<a id="hello world"></a>'), [])


if __name__ == '__main__':
    unittest.main()
