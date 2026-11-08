"""Five current 64-bit native programs and independent numeric/CRC references."""
from pathlib import Path
import argparse,sys,json,zlib,hashlib
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P/'control_p_compute_v0_1'))
from run_a2 import assemble,mem
NAMES=('U','F','C','P','J');ABI=0x01930001
def pack16(values):return sum((x&0xffff)<<(16*i) for i,x in enumerate(values))
def command(lane,meta,src=(),dst=None):
 fields=lane | len(src)<<2
 if dst is not None:fields|=16 | dst<<5
 return dict(native_op=0x100,native0=fields,native1=sum(a<<(10*i) for i,a in enumerate(src)),native2=meta)
def operations(kind,epoch):
 if kind==0:return [command(1,0x100,(21,)),command(1,0x81,(40,)),command(1,2),command(1,0x85,(40,20),41),command(1,7,(),42),command(0,3,(23,24),25)]
 if kind in (1,2):
  rows=[command(1,9,(12,13),14),command(0,0,(14,13),15)]
  return rows+([command(2,0,(43,)),command(2,2,(),44)] if kind==2 else [])
 if kind==3:return [dict(native_op=0x110,native0=34|4<<21),dict(native_op=0x111,native0=10,native1=0x9214),dict(native_op=0x111,native0=10,native1=0x9210),dict(native_op=0x111,native0=5|1<<10|8<<12,native1=0x101),dict(native_op=0x112,native0=12|13<<10|14<<20)]
 return [dict(native_op=0x120,native0=32|4<<10,native1=epoch<<24|7),dict(native_op=0x121)]
def build(kind,epoch,fault=False):
 topology=0x01930011+kind;rows=[dict(native_op=0x101)] if fault else operations(kind,epoch)
 mother=[dict(op='G_CALL',a=0,b=2,c=0),dict(op='G_CALL',a=1,b=3,c=0),dict(op='G_WAIT',x=12),dict(op='G_END')]
 yield 'mother',assemble('mother',mother,{},194000+kind*10,0,ABI,topology,instruction_version=2)
 for block in (0,1):
  program=[];records=[]
  for n,row in enumerate(rows):
   program.extend([dict(op='L_EXEC',a=0,b=0,c=n),dict(op='L_WAIT',x=1)])
   records.append(dict(row,resource=0,service=0,native_abi_id=ABI))
  program.append(dict(op='L_END'));image_id=194001+kind*10+block
  task=dict(block_type=kind,entry_pc=0,max_steps=len(program),required_resources=1,program_image_id=image_id,topology_id=topology,native_abi_id=ABI)
  yield f'local{block}',assemble('local',program,dict(task=[task],execution=records),image_id,1,ABI,topology,instruction_version=2)
def vectors(kind,epoch,variant):
 seeds=[];checks=[]
 def seed(block,address,value,op=12):seeds.append((op,block+1,address*16,value))
 def check(block,address,value,op=11,mask=(1<<128)-1):checks.append((op,block+1,address,value,mask))
 for block in (0,1):
  v=variant+block
  if kind==0:
   inputs=[1024,-1024]*4
   # RMS mode requires nonzero epsilon. Integer sqrt((1024**2+1)<<16)
   # is 262144, giving the exact original +/-1024 normalization here.
   for address,value in ((0,5),(20,pack16([1024]*8)),(21,1),(40,pack16(inputs)),(23,pack16([2+v]*8)),(24,pack16([3+v]*8))):seed(block,address,value)
   stats=(sum(x*x for x in inputs)<<80)|((sum(inputs)&0xffffffff)<<48)|((min(inputs)&0xffff)<<32)|((max(inputs)&0xffff)<<16)|len(inputs)
   check(block,41*16,pack16(inputs));check(block,42*16,stats);check(block,25*16,pack16([(2+v)*(3+v)]*8))
  elif kind in (1,2):
   gamma=1024*(v+1);pair=gamma|(gamma<<16)
   seed(block,12,0);seed(block,13,pair)
   check(block,14*16,(gamma//2)|((gamma//2)<<16));check(block,15*16,(3*gamma//2)|((3*gamma//2)<<16))
   if kind==2:
    state=sum((i+1+v)<<(32*i) for i in range(4));seed(block,43,state);check(block,44*16,state)
  elif kind==3:
   for address,value in ((0,2+v),(1,0),(2,0),(3,0),(4,0xfb0000000000000003),(5,0),(6,0),(7,0),(12,0xd8f02710),(13,0x04000200)):seed(block,address,value)
   check(block,8*16,(((-5*(2+v))&0xffffffff)<<32)|(3*(2+v)));check(block,14*16,5000)
  else:
   tag=epoch<<24|7
   for slot,base in ((0,0),(1,8)):
    for index in range(4):
     values=[(100+3*index+7*lane if slot==0 else -40+index-5*lane)+7*v for lane in range(8)]
     metadata=tag<<128|slot<<160|int(index==3)<<162
     seed(block,base+index,pack16(values)|metadata,14)
   for index in range(4):
    result=pack16([max(-32768,min(32767,60+4*index+2*lane+14*v)) for lane in range(8)])
    packet=result|tag<<128|index<<160|int(index==3)<<170
    check(block,0,packet,13,(1<<171)-1)
 return seeds,checks
def main():
 p=argparse.ArgumentParser();p.add_argument('--kind',type=int,choices=range(5),required=True);p.add_argument('output',type=Path);a=p.parse_args()
 for epoch,variant,fault in ((1,0,False),(1,1,False),(2,0,False),(1,0,True)):
  out=a.output/(f'e{epoch}-fault' if fault else f'e{epoch}-v{variant}');out.mkdir(parents=True,exist_ok=True);counts=[];crcs=[];images=[]
  for name,data in build(a.kind,epoch,fault):
   mem(out/(name+'.mem'),data);counts.append(len(data)//16);crcs.append(zlib.crc32(data))
   images.append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'crc32':f'{crcs[-1]:08x}'})
  seeds,checks=vectors(a.kind,epoch,variant);counts.extend([len(seeds),len(checks)])
  (out/'counts.mem').write_text(''.join(f'{x:08x}\n' for x in counts));(out/'crc.mem').write_text(''.join(f'{x:08x}\n' for x in crcs))
  (out/'seeds.mem').write_text(''.join(f'{op<<272|target<<270|addr<<256|value:069x}\n' for op,target,addr,value in seeds))
  (out/'checks.mem').write_text(''.join(f'{op<<1040|target<<1038|addr<<1024|mask<<512|value:0261x}\n' for op,target,addr,value,mask in checks))
  (out/'reference.json').write_text(json.dumps({'kind':NAMES[a.kind],'epoch':epoch,'variant':variant,'images':images,'expected_write_bytes':{0:96,1:64,2:96,3:64,4:128}[a.kind],'seed_commands':seeds,'checks':checks},indent=2)+'\n')
 print('PASS generated five-type current images and independent references',NAMES[a.kind])
if __name__=='__main__':main()
