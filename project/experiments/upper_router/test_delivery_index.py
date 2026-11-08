import json
from pathlib import Path
import tempfile
import unittest
from check import digest
from delivery_index import collect
from native_inventory import sha


class DeliveryIndexTest(unittest.TestCase):
    def fixture(self,root):
        delivery=root/'delivery';delivery.mkdir()
        design=delivery/'design.gds';design.write_bytes(b'physical artifact')
        stage=root/'stage';stage.mkdir();(stage/'run.log').write_text('retained log')
        receipt=root/'receipt.json';receipt.write_text('{"passed":true}')
        manifest={'paths':{'stage':str(stage),'receipt':str(receipt)}}
        (delivery/'input-manifest.json').write_text(json.dumps(manifest))
        qualified={'passed':True,'physical_qualified':True,'manifest_sha256':digest(manifest),
            'artifacts':{'design.gds':{'path':str(design),'sha256':sha(design)}},
            'gates':{'gate':{'path':str(receipt),'sha256':sha(receipt)}},
            'coverage':{'test_fixture':True},'qualification':'collector test only','not_claimed':[]}
        (delivery/'qualification.json').write_text(json.dumps(qualified))
        return delivery

    def test_records_evidence_sources_and_tools_without_copying_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);delivery=self.fixture(root)
            source=root/'source.tar';source.write_bytes(b'source')
            tool=root/'tool';tool.write_bytes(b'tool')
            result=collect(delivery,root/'index.json',[source],[tool])
            self.assertIn(str((root/'stage/run.log').resolve()),{r['path'] for r in result['files']})
            self.assertEqual(result['source_archives'][0]['sha256'],sha(source))
            self.assertEqual(result['tool_artifacts'][0]['sha256'],sha(tool))
            self.assertFalse((root/'design.gds').exists())

    def test_refuses_modified_delivery_without_writing_index(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);delivery=self.fixture(root)
            (delivery/'design.gds').write_bytes(b'changed after qualification')
            with self.assertRaises(AssertionError):collect(delivery,root/'index.json')
            self.assertFalse((root/'index.json').exists())

    def test_refuses_changed_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);delivery=self.fixture(root)
            (delivery/'input-manifest.json').write_text('{"paths":{}}')
            with self.assertRaises(AssertionError):collect(delivery,root/'index.json')
            self.assertFalse((root/'index.json').exists())


if __name__=='__main__':unittest.main()
