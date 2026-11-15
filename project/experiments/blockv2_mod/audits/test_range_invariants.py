import struct,unittest
from native_range_frontier import expand
from native_range_residency import rewrite

def call(schema,group='C0',word=0,address=0x1000,**kw):
 raw=bytearray(128);struct.pack_into('<I',raw,0,schema)
 struct.pack_into('<H',raw,16,word);struct.pack_into('<Q',raw,24,address)
 if schema==3:struct.pack_into('<4H',raw,16,0,32,kw.get('dst',64),32)
 return dict(index=0,after=[],group=group,descriptor_hex=raw.hex())

def sequence(*calls):
 return {'calls':[dict(c,index=i,after=[] if i==0 else [i-1]) for i,c in enumerate(calls)]}

class Test(unittest.TestCase):
 def test_committed_reuse(self):
  c,s=rewrite(sequence(call(0x314c5244)),{})
  d,s=rewrite(sequence(call(0x314c5244)),s)
  self.assertEqual(len(d['calls']),0)
 def test_overwritten_source_not_reused(self):
  c,s=rewrite(sequence(call(0x314c5244),call(3,dst=0)),{})
  d,s=rewrite(sequence(call(0x314c5244)),s)
  self.assertEqual(len(d['calls']),1)
 def test_foreign_commit_invalidates_cached_version(self):
  c,s=rewrite(sequence(call(0x314c5244)),{})
  c,s=rewrite(sequence(call(0x31535744,group='J0')),s)
  d,s=rewrite(sequence(call(0x314c5244)),s)
  self.assertEqual(len(d['calls']),1)
 def test_unknown_service_invalidates(self):
  c,s=rewrite(sequence(call(0x314c5244),call(0xdead)),{})
  self.assertFalse(s['C0'])
 def test_independent_sram_never_aliases(self):
  c,s=rewrite(sequence(call(0x314c5244,group='J0')), {})
  d,s=rewrite(sequence(call(0x314c5244)),s)
  self.assertEqual(len(d['calls']),1)
 def test_output_range_publication(self):
  def tile(v,start,root=None):
   return {'write':{'value':v,'element_offset':start,'elements':128},
    'read':[] if root is None else [{'root':root,'segments':[{'source_element':start,'elements':128}]}]}
  tasks={'p':{'id':'p','kind':'MatMul','tiles':[tile('x',0),tile('x',128)]},
    'c':{'id':'c','kind':'Add','tiles':[tile('y',0,'x'),tile('y',128,'x')]}}
  t,d,o,p=expand(tasks,{'p':[],'c':['p']},['p','c'])
  self.assertEqual(d[p['c'][0]],[p['p'][0]])
  self.assertNotIn(p['p'][1],d[p['c'][0]])
 def test_unpublished_range_rejected(self):
  tasks={'p':{'id':'p','kind':'MatMul','tiles':[{'write':{'value':'x','element_offset':0,'elements':128}}]},
   'c':{'id':'c','kind':'Add','tiles':[{'write':{'value':'y','element_offset':0,'elements':128},'read':[{'root':'x','segments':[{'source_element':64,'elements':128}]}]}]}}
  with self.assertRaisesRegex(ValueError,'unpublished'):
   expand(tasks,{'p':[],'c':['p']},['p','c'])
if __name__=='__main__':unittest.main()
