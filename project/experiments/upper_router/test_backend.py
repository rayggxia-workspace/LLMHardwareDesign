from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from backend import emit, merged_segments
from search import route
from test_router import sample


class BackendTests(unittest.TestCase):
    def test_merge_union_and_direction(self):
        parts=[{'layer':'M11','a':[8,8],'b':[16,8]},
               {'layer':'M11','a':[24,8],'b':[16,8]},
               {'layer':'M11','a':[8,8],'b':[16,8]}]
        self.assertEqual(merged_segments(parts),[{'layer':'M11','a':[8,8],'b':[24,8]}])

    def test_identity_map_and_exact_def(self):
        s=sample();s['pins']['source weird[/]']=s['pins'].pop('source')
        s['nets'][0]['driver']='source weird[/]'
        r=route(s)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'out';m=emit(s,r,path,2000,via_resistance_ohm=0.08)
            self.assertEqual(m['nets']['n000000']['driver'],'source weird[/]')
            text=(path/'upper.def').read_text()
            self.assertNotIn('source weird',text)
            self.assertIn('metal11 ( 8 8 ) ( 72 8 )',text)
            self.assertIn('metal12 ( 72 8 ) ( 72 72 )',text)
            self.assertFalse(json.loads((path/'bindings.json').read_text())['native_stitched'])

    def test_partial_and_stale_rejected(self):
        s=sample();r=route(s,max_expansions=1)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'partial'):
                emit(s,r,Path(directory)/'out',2000,via_resistance_ohm=0.08)
        r=route(s);r['context']={'wrong':'native'}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'context'):
                emit(s,r,Path(directory)/'out',2000,via_resistance_ohm=0.08)

    def test_multisink_has_one_net_and_all_ports(self):
        s=sample();s['pins']['other']=[[70,6,74,10]];s['nets'][0]['sinks'].append('other')
        r=route(s)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'out';m=emit(s,r,path,2000,via_resistance_ohm=0.08)
            self.assertEqual(len(m['nets']),1)
            self.assertEqual(len(m['nets']['n000000']['ports']),3)
            self.assertIn('PINS 3 ;',(path/'upper.def').read_text())

    def test_bound_grid_and_rc_cannot_change_silently(self):
        s=sample();s['context']['dbu_per_micron']=2000;r=route(s)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'DBU scale'):
                emit(s,r,Path(directory)/'out',1000,via_resistance_ohm=0.08)
            with self.assertRaisesRegex(ValueError,'via resistance'):
                emit(s,r,Path(directory)/'out',2000,via_resistance_ohm=float('nan'))


if __name__=='__main__':unittest.main()
