import struct,zlib,unittest
from native_dirty_memory import transform,LOAD,STORE,MPR
def call(schema,owner='P0',words=(0,32,64),address=0):
 raw=bytearray(128);struct.pack_into('<I',raw,0,schema)
 if schema in (LOAD,STORE):struct.pack_into('<H',raw,16,words[0]);struct.pack_into('<Q',raw,24,address)
 else:struct.pack_into('<4H',raw,16,*words,32)
 struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
 return {'group':owner,'descriptor_hex':raw.hex(),'index':0,'after':[]}
def add(a,b,out,owner='P0',capacity=1024):
 return {'groups':[owner],'_input_pages':{a,b},'_capacity_words':{owner:capacity},'calls':[
  call(LOAD,owner,(0,),a),call(LOAD,owner,(32,),b),call(3,owner),
  call(STORE,owner,(64,),out)]}
def schemas(c):return [int.from_bytes(bytes.fromhex(x['descriptor_hex'])[:4],'little') for x in c['calls']]
class DirtyTests(unittest.TestCase):
 def setUp(self):
  self.kw={'produced':{12288:0,16384:1},'users':{12288:2},'exports':{16384}}
  self.empty={'memory':{},'backed':0}
 def produce(self,capacity=1024):
  return transform(add(4096,8192,12288,capacity=capacity),self.empty,keep=True,done=1,**self.kw)
 def test_local_handoff_release(self):
  c,s,e=self.produce(96);self.assertNotIn(STORE,schemas(c));self.assertEqual(s['backed'],0)
  c,s,e=transform(add(12288,8192,16384,capacity=96),s,keep=True,done=3,**self.kw)
  self.assertEqual(schemas(c),[3,STORE]);self.assertTrue(s['backed']&2)
  self.assertTrue(any(x['op']=='release' and x['dirty'] for x in e))
 def test_cross_owner_requires_commit(self):
  _,s,_=self.produce()
  c,s,e=transform(add(12288,8192,16384,'P1'),s,keep=True,done=3,**self.kw)
  self.assertEqual(c['calls'][0]['group'],'P0');self.assertEqual(schemas(c)[0],STORE)
  self.assertTrue(any(x['op']=='spill' for x in e))
 def test_missing_backing_rejected(self):
  with self.assertRaisesRegex(ValueError,'no backing'):
   transform(add(12288,8192,16384),self.empty,keep=True,done=3,**self.kw)
 def test_live_output_commits(self):
  kw={**self.kw,'exports':{12288,16384}}
  c,s,e=transform(add(4096,8192,12288),self.empty,keep=True,done=1,**kw)
  self.assertIn(STORE,schemas(c));self.assertTrue(s['backed']&1)
 def test_insufficient_sram_rejected(self):
  with self.assertRaisesRegex(ValueError,'exhausted'):self.produce(64)
 def test_opaque_requires_dirty_commit(self):
  _,s,_=self.produce()
  opaque={'groups':['P0'],'_input_pages':{12288},'calls':[call(0xdead)]}
  c,s,e=transform(opaque,s,keep=True,done=3,**self.kw)
  self.assertEqual(schemas(c),[STORE,0xdead]);self.assertFalse(s['memory']['P0'])
 def test_capacity_eviction_spills_live_dirty(self):
  kw={**self.kw,'users':{12288:4}}
  _,state,_=transform(add(4096,8192,12288,capacity=96),self.empty,keep=True,done=1,**kw)
  c,state,events=transform(add(4096,8192,16384,capacity=96),state,keep=True,done=3,**kw)
  self.assertEqual(schemas(c),[STORE,3,STORE])
  self.assertTrue(state['backed']&1)
 def test_copy_workspace_preserves_source_identity(self):
  _,state,_=self.produce()
  c=add(12288,8192,16384)
  c['calls'].insert(1,call(STORE,words=(0,),address=20480))
  kw={**self.kw,'users':{12288:4}}
  c,state,events=transform(c,state,keep=True,done=3,**kw)
  self.assertFalse(state['backed']&1)
  self.assertTrue(any(v['address']==12288 and v['dirty'] for v in state['memory']['P0'].values()))
  for c in c['calls']:
   raw=bytes.fromhex(c['descriptor_hex'])
   self.assertEqual(zlib.crc32(raw[:124]),int.from_bytes(raw[124:],'little'))
 def projection(self,source):
  m=call(MPR);raw=bytearray.fromhex(m['descriptor_hex'])
  struct.pack_into('<H',raw,76,128);struct.pack_into('<HH',raw,84,880,64)
  struct.pack_into('<Q',raw,112,20480);struct.pack_into('<H',raw,120,832)
  m['descriptor_hex']=raw.hex()
  return {'groups':['P0'],'_input_pages':{source},'_workspace':{'base':20480,'bytes':512},
   'calls':[call(LOAD,words=(0,),address=source),call(STORE,words=(0,),address=20480),
    m,call(STORE,words=(64,),address=16384)]}
 def test_packed_workspace_reuse(self):
  c,state,_=transform(self.projection(4096),self.empty,keep=True,done=1,**self.kw)
  self.assertEqual(schemas(c),[LOAD,STORE,MPR,STORE])
  c,state,events=transform(self.projection(4096),state,keep=True,done=3,**self.kw)
  self.assertEqual(schemas(c),[MPR,STORE])
  self.assertEqual(state['copies'][20480],4096)
  self.assertTrue(any(e['op']=='reuse_packed_DDR' for e in events))
 def test_changed_packing_source_requires_copy(self):
  _,state,_=transform(self.projection(4096),self.empty,keep=True,done=1,**self.kw)
  c,state,events=transform(self.projection(8192),state,keep=True,done=3,**self.kw)
  self.assertEqual(schemas(c),[LOAD,STORE,MPR,STORE])
  self.assertEqual(state['copies'][20480],8192)
if __name__=='__main__':unittest.main()
