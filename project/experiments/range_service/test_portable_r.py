"""Portable bundle integrity and small independent retry semantics, no model replay."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np

def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

p=module('portable_test','portable_r.py');producer=module('range_fixture','range.py')
ORACLE=Path(os.environ.get('ISSUE68_ORACLE',str(Path(__file__).with_name('receive_range.py'))))


class PortableR(unittest.TestCase):
    def test_zip_all_members_rehashed_and_unsafe_paths_rejected(self):
        temp=Path('D:/Projects/Codex/range-service-20261024-1238/range');temp.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp,prefix='portable-boundary-') as td:
            root=Path(td);path=root/'small.zip';p.write_bundle({'a.json':b'{}\n'},path)
            self.assertEqual(p.load_bundle(path),{'a.json':b'{}\n'})
            with zipfile.ZipFile(root/'unsafe.zip','w') as z:z.writestr('../x',b'bad')
            with self.assertRaises(AssertionError):p.load_bundle(root/'unsafe.zip')
            members={'a.json':b'bad'}
            with zipfile.ZipFile(root/'wronghash.zip','w') as z:
                z.writestr('a.json',b'bad');z.writestr('index.json',p.jbytes({'schema':'issue68-portable-r/1','artifacts':{'a.json':p.descriptor(b'original')}}))
            with self.assertRaises(AssertionError):p.load_bundle(root/'wronghash.zip')
            with self.assertRaises(FileExistsError):p.write_bundle(members,path)

    @unittest.skipUnless(ORACLE.is_file(),'frozen independent oracle not present in this isolated worktree')
    def test_small_two_causal_rescales_and_wrong_outputs_epochs(self):
        o=p.oracle_module(ORACLE.read_bytes())
        for bits in (16,32):
            encoded={'q':np.full((14,2,2),10000,dtype=np.int16),'k':np.zeros((14,2,2),dtype=np.int16),
                     'v':np.zeros((14,2,2),dtype=np.int16),'beta':np.zeros((14,2),dtype=np.uint16),
                     'decay':np.full((14,2),1<<31,dtype=np.uint32)}
            encoded['k'][:,:,0]=16384
            for t in (3,12):encoded['v'][t,1,0]=32767;encoded['beta'][t,1]=32768
            initial=np.zeros((2,2,2),dtype=np.int64);units=np.array([0,0])-(16 if bits==32 else 0);vu=np.array([2,2])
            full,stats=producer.run(encoded,initial,units,vu,bits,31,'guard_rescale',7936,'synthetic')
            self.assertEqual([e['token'] for e in stats['rescale_events']],[3,12])
            arrays={k:v[2:14] for k,v in encoded.items()};arrays['value_units']=vu
            arrays.update({k:full[k][2:15] for k in ('state_trace','state_units_trace','epoch_trace')})
            arrays.update({k:full[k][2:14] for k in ('output_codes','output_units')})
            case={'id':'synthetic.S'+str(bits),'format':{'state_bits':bits,'decay_fraction':31},'begin':2,'end':14,
                  'initial_snapshot':stats['tokens'][2]['before'],'final_snapshot':stats['tokens'][13]['commit']['new']}
            trace={'tokens':stats['tokens'][2:14],'rescale_events':stats['rescale_events']}
            self.assertEqual(p.verify_segment(case,arrays,trace,o)['real_rescale_waves'],2)
            for field in ('output_codes','epoch_trace'):
                bad={k:v.copy() for k,v in arrays.items()};bad[field].flat[-1]+=1
                with self.assertRaises(AssertionError):p.verify_segment(case,bad,trace,o)
            wrong=copy.deepcopy(case);wrong['initial_snapshot']['epoch']=1
            with self.assertRaises(AssertionError):p.verify_segment(wrong,arrays,trace,o)
            wrongarrays={k:v.copy() for k,v in arrays.items()};wrongarrays['epoch_trace'][0]+=1
            with self.assertRaises(AssertionError):p.verify_segment(case,wrongarrays,trace,o)
            wrongtrace=copy.deepcopy(trace);wrongtrace['tokens'][1]['attempts'][0]['proposed_state_sha256']='wrong'
            with self.assertRaises(AssertionError):p.verify_segment(case,arrays,wrongtrace,o)

    @unittest.skipUnless(ORACLE.is_file(),'frozen independent oracle not present in this isolated worktree')
    def test_oracle_pin_rejects_changed_source(self):
        with self.assertRaises(AssertionError):p.oracle_module(ORACLE.read_bytes()+b'\n')


if __name__=='__main__':unittest.main()
