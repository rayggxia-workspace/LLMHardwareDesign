import unittest

from sequence_policy import validate_resume, sequence_passed


class SequenceQualification(unittest.TestCase):
    def previous(self):
        return {'identity': {'checkpoint': 'frozen', 'decode_template_sha256': 'template'},
                'batch_numeric_passed': False, 'HF_model_source_unchanged': True,
                'source_artifact_size_mtime_unchanged': True}

    def test_diagnostic_can_resume_quality_failure_but_cannot_erase_ancestry(self):
        previous = self.previous()
        with self.assertRaisesRegex(ValueError, 'previous batch failed'):
            validate_resume(previous, {'checkpoint': 'frozen'}, False)
        validate_resume(previous, {'checkpoint': 'frozen'}, True)
        self.assertFalse(sequence_passed(True, [{'numeric_passed': False}]))
        self.assertFalse(sequence_passed(False, [{'numeric_passed': True}]))
        self.assertTrue(sequence_passed(True, [{'numeric_passed': True}]))

    def test_diagnostic_does_not_allow_changed_checkpoint_or_source(self):
        previous = self.previous()
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            validate_resume(previous, {'checkpoint': 'different'}, True)
        previous['HF_model_source_unchanged'] = False
        with self.assertRaisesRegex(ValueError, 'source drift'):
            validate_resume(previous, {'checkpoint': 'frozen'}, True)
