import unittest

from qwen_sram_spans import pm_cycles, span_beats


class QwenSramWidthTest(unittest.TestCase):
    def test_aligned_data_span_packs_words_into_one_port_beat(self):
        for width_words, expected in ((1, 8), (2, 4), (4, 2)):
            with self.subTest(width_words=width_words):
                self.assertEqual(span_beats(8, 8, width_words), expected)

    def test_unaligned_data_span_preserves_partial_beats_at_both_ends(self):
        for width_words, expected in ((1, 6), (2, 4), (4, 3)):
            with self.subTest(width_words=width_words):
                self.assertEqual(span_beats(3, 6, width_words), expected)
                self.assertEqual(span_beats(3, 1, width_words), 1)

    def test_pm_waits_for_the_last_partial_write(self):
        for width_words, one_burst_cycles in ((1, 8), (2, 4), (4, 2)):
            with self.subTest(width_words=width_words):
                self.assertEqual(pm_cycles(64, width_words), one_burst_cycles)
                self.assertEqual(pm_cycles(80, width_words), one_burst_cycles + 2)


if __name__ == "__main__":
    unittest.main()
