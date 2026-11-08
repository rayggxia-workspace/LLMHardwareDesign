import json
from pathlib import Path
import tempfile
import unittest
from collect_field import collect
from field_solve import sha


class CollectionTest(unittest.TestCase):
    def fixture(self,root):
        scene=root/'scene';scene.mkdir();(scene/'scene.bin').write_bytes(b'test-only geometry')
        meta={'complete_native_context':True,'scene_sha256':sha(scene/'scene.bin'),'names':['first','second','PG']}
        (scene/'scene.json').write_text(json.dumps(meta));(scene/'masters.txt').write_text('0\n1\n')
        shards=[]
        for i,name in enumerate(meta['names'][:2]):
            shard=root/str(i);shard.mkdir();row={'master':i,'net':name,'node_self':[[10,.1]],
                'total_ff':100,'sigma_ff':.1,'ground':[-10,.01],
                'values':[[100 if j==i else 0,.01] for j in range(2)]+[[-90,.01],[-10,.01]]}
            (shard/'rows.jsonl').write_text(json.dumps(row)+'\n')
            report={'passed':True,'complete_native_context':True,'scene_sha256':meta['scene_sha256'],
                'rows_sha256':sha(shard/'rows.jsonl'),'binary_sha256':'b'*64,'controls_sha256':'c'*64,'masters':[i]}
            (shard/'solve.json').write_text(json.dumps(report));shards.append(shard)
        return scene,shards

    def test_disjoint_coverage_and_reject_missing_duplicate_stale_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);scene,shards=self.fixture(root)
            result=collect(scene,shards,root/'complete');self.assertTrue(result['passed'])
            self.assertTrue(result['complete_master_coverage']);self.assertEqual(result['masters'],[0,1])
            for label,selected in [('missing',shards[:1]),('duplicate',shards+shards[:1])]:
                with self.assertRaises(AssertionError):collect(scene,selected,root/label)
            (shards[0]/'rows.jsonl').write_text('{}\n')
            with self.assertRaises(AssertionError):collect(scene,shards,root/'tampered')


if __name__=='__main__':unittest.main()
