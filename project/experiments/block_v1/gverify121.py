# Derived independent G receiver SHA256 c698ba20d0d037a1d4396dfc82e69f432bc1b942a38b9eb5aa3ad42d03e8907f
"""Independent GDN payload/state/stage and shared-export reception."""
import hashlib,json,struct,importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('gdn_independent',ROOT/'project/experiments/gdn_state/reference.py');REF=importlib.util.module_from_spec(spec);spec.loader.exec_module(REF)
SNAP=133200
GNUMBERS=set('g_op g_slot g_position g_version g_epoch g_units_raw g_value_units_raw g_bank g_retries g_wide_calls g_root_writes g_owner_saved g_context_saved candidate_holds'.split())
GSTRINGS={'g_context_label'};GARRAYS={'g_out'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snapshot(data):
 assert len(data)==SNAP
 rt=int.from_bytes(data[:16],'little');meta=[int.from_bytes(data[16+16*i:32+16*i],'little')for i in range(4)]
 assert rt&0xffffffff==0x47445231 and(rt>>33)&1 and(rt>>34)&((1<<30)-1)==0,'root'
 bank=(rt>>32)&1;ver=rt>>64
 m0,m1,m2,m3=meta
 assert m0&0xffffffff==0x47444e31 and(m0>>32)&65535==1 and(m0>>48)&0xffffffff==182389313,'metadata identity'
 assert(m0>>80)&31==0 and(m0>>85)&31==1 and(m0>>90)&63==0,'group'
 assert(m2>>32)&((1<<64)-1)==104 and(m2>>96)&1==bank and m2>>97==0,'metadata context'
 assert [m3>>(32*i)&0xffffffff for i in range(4)]==[0x062b0000,32,0x06200000+bank*131072,0x062a0000+bank*2048],'metadata address'
 assert m1>>64==ver,'root/meta version'
 units=np.frombuffer(((m0>>96)&65535).to_bytes(2,'little'),dtype=np.int8).astype(int).tolist();vu=np.frombuffer((m0>>112).to_bytes(2,'little'),dtype=np.int8).astype(int).tolist()
 return {'state':np.frombuffer(data[80:131152],dtype='<i4').reshape(2,128,128),'y':np.frombuffer(data[131152:],dtype='<i8').reshape(2,128),'units':units,'value_units':vu,'epoch':m2&0xffffffff,'position':m1&((1<<64)-1),'version':ver,'bank':bank}

class GOracle:
 def __init__(self,inp,manifest):
  self.inp=inp;self.cases={};self.commits=0;self.waves=0;self.stage_count=0;self.exports=0;self.restored=False
  for e in manifest['relocations']:
   old=Path(e['source']);m=json.loads((old/'manifest.json').read_text());assert sha(old/'manifest.json')==e['manifest_sha256']
   for a in m['artifacts']:assert sha(old/a['path'])==a['sha256'] and (old/a['path']).stat().st_size==a['bytes']
   original=(old/'image.bin').read_bytes();data=(inp/e['image']).read_bytes();assert sha(old/'image.bin')==e['original_image_sha256']
   changed=bytearray(original);struct.pack_into('<4I',changed,e['offset'],*e['after']);assert bytes(changed)==data and struct.unpack_from('<4I',original,e['offset'])==tuple(e['before'])
   assert e['after']==[e['before'][0]+0x02200000,32,e['before'][2]+0x02200000,e['before'][3]+0x02200000]
   assert sha(inp/e['coefficients'])==sha(old/'coefficients.npz')
   with np.load(inp/e['coefficients'],allow_pickle=False)as n:z={k:n[k].copy()for k in n.files}
   bank=(int.from_bytes(data[0xa1080:0xa1090],'little')>>32)&1
   init=snapshot(data[0xa1080:0xa1090]+data[0xa1000+bank*64:0xa1040+bank*64]+data[bank*131072:(bank+1)*131072]+data[0xa0000+bank*2048:0xa0800+bank*2048])
   assert np.array_equal(init['state'],z['state_initial'])and np.array_equal(init['y'],z.get('initial_output',np.zeros((2,128),np.int64)))
   assert init['units']==list(map(int,z['state_units']))and init['value_units']==list(map(int,z['value_units']))
   for slot in range(len(z['q'])):
    raw=data[0xb0000+slot*1568:0xb0000+(slot+1)*1568];assert struct.unpack_from('<II',raw)==(0x47444331,slot)
    assert list(struct.unpack_from('<IIHHI',raw,16))==[*map(int,z['decay'][slot]),*map(int,z['beta'][slot]),0]
    for j,k in enumerate(('q','k','v')):assert np.array_equal(np.frombuffer(raw[32+j*512:544+j*512],dtype='<i2').reshape(2,128),z[k][slot])
   self.cases[e['label']]=(init,z)
  self.switch('native')
 def switch(self,label):
  self.label=label;self.expected={k:v.copy()if isinstance(v,np.ndarray)else list(v)if isinstance(v,list)else v for k,v in self.cases[label][0].items()};self.z=self.cases[label][1];self.restored=False
 def prepare(self,run,rows):
  self.raw=(run/'actual.jsonl.g-snapshots.bin').read_bytes();assert len(self.raw)==len(rows)*SNAP
  data=(run/'actual.jsonl.g-stages.bin').read_bytes();assert len(data)%40==0;self.stages={}
  for i in range(0,len(data),40):
   record,*other=struct.unpack_from('<6I2q',data,i);assert record<len(rows);self.stages.setdefault(record,[]).append(tuple(other))
  self.total_stages=len(data)//40
 def check(self,index,row):
  if row['role']=='G-restore-rescale':self.switch('rescale')
  if row['role']=='second-reset-Rrestore':self.restored=False
  assert row['g_context_label']==self.label
  e=self.expected;stages=self.stages.get(index,[])
  if row['kind']==3:
   if row['status']==4:
    assert not stages and not row['g_out']and row['g_root_writes']==row['transactions']==row['mul0']==row['sreads']==row['swrites']==0
   elif row['g_op']==0:
    assert row['transactions']==5 and row['g_root_writes']==0 and row['result_lines']==0 and not row['g_out']and not stages
    self.restored=True
   else:
    slot=row['g_slot'];ns,ny,nu,ne,attempts=REF.step(e['state'],self.z['q'][slot],self.z['k'][slot],self.z['v'][slot],self.z['decay'][slot],self.z['beta'][slot],e['units'],e['value_units'],e['epoch'])
    wanted=list(REF.observations(attempts));assert stages==wanted[:len(stages)],(index,'G stage prefix')
    if row['status']in(0,3):assert len(stages)==len(wanted),(index,'G complete stages')
    assert row['g_out']==ny.ravel().tolist()[:len(row['g_out'])],(index,'real candidate prefix')
    if row['status']in(0,3):assert row['result_lines']==128 and len(row['g_out'])==(256 if row['status']==0 else 0) and row['candidate_holds']>=9 and row['g_retries']==len(attempts)-1,(index,'full candidate before decision')
    assert row['g_root_writes']==int(row['status']==0)
    if row['role']=='G-actual-rescale':assert len(attempts)>1,'true selected rescale'
    if row['status']==0:e.update(state=ns,y=ny,units=nu,epoch=ne,bank=1-e['bank'],position=e['position']+1,version=e['version']+1);self.commits+=1;self.waves+=len(attempts)-1
    self.exports+=len(row['g_out'])*8
  else:assert not stages and not row['g_out'] and row['g_root_writes']==0
  actual=snapshot(self.raw[index*SNAP:(index+1)*SNAP])
  for k in e:
   assert np.array_equal(actual[k],e[k]),(index,'G published preserved',k)
  if self.restored:
   for name,key in [('g_position','position'),('g_version','version'),('g_epoch','epoch'),('g_bank','bank')]:assert row[name]==e[key],(index,name)
   assert row['g_units_raw']==(e['units'][0]&255)|((e['units'][1]&255)<<8)
   assert row['g_owner_saved']==182389313 and row['g_context_saved']==104
  self.stage_count+=len(stages)
 def report(self):
  assert self.stage_count==self.total_stages
  return {'complete_twohead_commits':self.commits,'range_waves':self.waves,'stage_pairs':self.stage_count,'exported_payload_bytes':self.exports,'snapshot_count':len(self.raw)//SNAP,'state_codes':len(self.raw)//SNAP*32768,'output_codes':len(self.raw)//SNAP*256}
