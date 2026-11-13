"""Reject incomplete tile/scatter receipts rather than accepting a PASS line."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from column_tile_probe import analyse


def fixture():
    # Literal hand-counted R2/N8/K3 case, with four diagnostic final shifts.
    manifest={'kind':'native-column-tile-scatter-probe-v2','sha256':{},
              'cases':[{'id':0,'rows':2,'columns':8,'k':3}],
              'groups':[],'scope':'synthetic receipt fixture only','excluded':[]}
    record={'id':0,'rows':2,'columns':8,'k':3,'cycles':100,
            'a_fires':210,'b_fires':390,'wide_reads':591,'store_acks':88,
            'e_store_acks':16,'e_commands':16,'dot_a_stage_words':18,'dot_b_stage_words':24}
    profiles=[]
    for boundary in ('p-command','native-m'):
        for r,op,count in ((2,4,9),(2,10,9),(2,3,8),(2,5,16),
                           (1,4,192),(1,10,192),(1,5,64)):
            p={'boundary':boundary,'rows':r,'op':op,'samples':count,'min':2,'max':2}
            if boundary=='p-command':p['store']=int(op in (3,5))
            profiles.append(p)
    for r,reuse,count in ((2,0,3),(2,1,6),(1,0,192)):
        profiles.append({'boundary':'feeder','rows':r,'reuse_b':reuse,
                         'samples':count,'min':3,'max':3})
    profiles.append({'boundary':'e-service','op':8,'shift':15,'samples':16,'min':14,'max':14})
    return manifest,record,profiles


class TestColumnTileEvidence(unittest.TestCase):
    def run_fixture(self,record,profiles,*,complete=True,extra='',materialized=False):
        manifest=fixture()[0]
        if materialized:manifest['execution_order']='packed-external-three-phase-v1'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'manifest.json').write_text(json.dumps(manifest))
            lines=['COLUMN_TILE '+json.dumps(record)]
            lines+=['COLUMN_PROFILE '+json.dumps(p) for p in profiles]
            if complete:lines.append('PASS native column tile and scalar scatter probe')
            (root/'simulate.log').write_text('\n'.join(lines)+'\n'+extra)
            return analyse(root,root/'simulate.log',emit=False)

    def test_complete_hand_counted_receipt(self):
        _,r,p=fixture();result=self.run_fixture(r,p)
        self.assertEqual(result['passed_cases'],1)
        self.assertEqual(result['passive_profiles'],p)

    def test_transport_or_ack_corruption_rejected(self):
        _,r,p=fixture()
        for field in ('dot_b_stage_words','a_fires','wide_reads','store_acks','e_store_acks'):
            bad=deepcopy(r);bad[field]-=1
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_fixture(bad,p)

    def test_missing_duplicate_or_corrupted_profile_rejected(self):
        _,r,p=fixture();bad=deepcopy(p);bad[-1]['samples']+=1
        for changed in (p[:-1],p+[p[0]],bad):
            with self.assertRaises(ValueError):self.run_fixture(r,changed)

    def test_truncation_or_fatal_even_with_pass_line_rejected(self):
        _,r,p=fixture()
        with self.assertRaises(ValueError):self.run_fixture(r,p,complete=False)
        with self.assertRaises(ValueError):self.run_fixture(r,p,extra='FATAL: numeric mismatch\n')

    def test_explicit_materialized_phase_receipt(self):
        _,r,p=fixture()
        result=self.run_fixture(r,p,extra='MATERIALIZED_PHASE id=0 packed=16 flags=16 refill=16\n')
        self.assertEqual(result['materialized_order']['cases'],1)
        for changed in ('packed=15 flags=16 refill=16','packed=16 flags=15 refill=16','packed=16 flags=16 refill=0'):
            with self.assertRaisesRegex(ValueError,'phase coverage'):
                self.run_fixture(r,p,extra='MATERIALIZED_PHASE id=0 '+changed+'\n')
        with self.assertRaisesRegex(ValueError,'missing materialized'):
            self.run_fixture(r,p,materialized=True)
