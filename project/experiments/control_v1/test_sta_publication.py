"""A positive dependency signal must never precede its complete bound receipt."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from system_sta import publish_completion

class PublicationTest(unittest.TestCase):
    def test_reader_at_dependency_visibility(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);(root/'result.tsv').write_text('all endpoints checked\n')
            original=Path.replace;observed=[]
            def replace(path,target):
                if path.name=='native-system-audit.pending':
                    self.assertFalse(Path(target).exists())
                    receipt=json.loads((root/'receipt.json').read_text())
                    self.assertEqual(receipt['outputs']['native-system-audit.json'],hashlib.sha256(path.read_bytes()).hexdigest())
                    self.assertEqual(receipt['outputs']['result.tsv'],hashlib.sha256((root/'result.tsv').read_bytes()).hexdigest())
                    self.assertTrue(receipt['execution_passed']);observed.append(True)
                return original(path,target)
            with patch.object(Path,'replace',replace):publish_completion(root,dict(passed=False,execution_passed=True),dict(passed=True))
            self.assertEqual(observed,[True]);self.assertTrue(json.loads((root/'native-system-audit.json').read_text())['passed'])
    def test_failed_receipt_write_never_publishes_positive_audit(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);original=Path.write_bytes
            def write(path,data):
                if path.name=='receipt.pending':raise OSError('injected receipt storage failure')
                return original(path,data)
            with patch.object(Path,'write_bytes',write),self.assertRaises(OSError):
                publish_completion(root,dict(execution_passed=True),dict(passed=True))
            self.assertFalse((root/'native-system-audit.json').exists());self.assertFalse((root/'receipt.json').exists())
            self.assertTrue((root/'native-system-audit.pending').exists())

if __name__=='__main__':unittest.main()
