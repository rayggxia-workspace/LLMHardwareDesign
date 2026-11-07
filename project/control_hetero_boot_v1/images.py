"""Directed RAW128 programs; current v2 assembler and independent numeric references."""
from pathlib import Path
import sys,argparse,json,zlib,hashlib
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P/'control_five_boot_v1'))
import importlib.util
spec=importlib.util.spec_from_file_location('five_images',P/'control_five_boot_v1/images.py');five=importlib.util.module_from_spec(spec);spec.loader.exec_module(five)
operations,vectors,pack16,ABI=five.operations,five.vectors,five.pack16,five.ABI
sys.path.insert(0,str(P/'control_p_compute_v0_1'))
from run_a2 import assemble,mem
def build(kind,epoch):
 topology=0x01930500+kind;source=operations(kind,epoch);count=4 if kind==4 else 1
 address={0:25,1:15,2:44,4:0}[kind];prefix=len(source)
 source += [dict(native_op=0x101,native0=(i if kind==4 else address)|(60+i)<<10) for i in range(count)]
 sink=[]
 for i in range(count):sink += [dict(native_op=0x103,native0=60+i,native1=prefix+i),dict(native_op=0x102)]
 sink += [dict(native_op=0x112,native0=60|13<<10|14<<20)]
 mother=[dict(op='G_CALL',a=0,b=2,c=0),dict(op='G_CALL',a=1,b=3,c=0),dict(op='G_WAIT',x=12),dict(op='G_END')]
 yield 'mother',assemble('mother',mother,{},195000+kind*10,0,ABI,topology,instruction_version=2)
 for block,rows in enumerate((source,sink)):
  image=195001+kind*10+block;program=[];records=[]
  for i,row in enumerate(rows):
   program += [dict(op='L_EXEC',a=0,b=0,c=i),dict(op='L_WAIT',x=1)];records.append(dict(row,resource=0,service=0,native_abi_id=ABI))
  program += [dict(op='L_END')]
  task=dict(block_type=kind if block==0 else 3,entry_pc=0,max_steps=len(program),required_resources=1,program_image_id=image,topology_id=topology,native_abi_id=ABI)
  yield f'local{block}',assemble('local',program,dict(task=[task],execution=records),image,1,ABI,topology,instruction_version=2)
def main():
 p=argparse.ArgumentParser();p.add_argument('--kind',type=int,choices=(0,1,2,4),required=True);p.add_argument('output',type=Path);a=p.parse_args()
 for epoch,variant in ((1,0),(1,1),(2,0)):
  out=a.output/f'e{epoch}-v{variant}';out.mkdir(parents=True,exist_ok=True);counts=[];crc=[];images=[]
  for name,data in build(a.kind,epoch):
   mem(out/(name+'.mem'),data);counts.append(len(data)//16);crc.append(zlib.crc32(data));images.append(dict(name=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
  seeds,checks=vectors(a.kind,epoch,variant);seeds=[s for s in seeds if s[1]==1];checks=[c for c in checks if c[1]==1]
  if a.kind==4:
   checks=[];payloads=[pack16([60+4*i+2*lane+14*variant for lane in range(8)]) for i in range(4)]
  else:
   source_address={0:25,1:15,2:44}[a.kind]*16
   payloads=[next(c[3] for c in checks if c[2]==source_address)]
  # Destination poison makes a missing/early commit observable at every word.
  seeds += [(12,2,(60+i)*16,(1<<128)-1) for i in range(len(payloads))]+[(12,2,13*16,0)]
  checks += [(11,2,(60+i)*16,v,(1<<128)-1) for i,v in enumerate(payloads)]
  checks += [(11,2,14*16,0,(1<<128)-1)]
  counts += [len(seeds),len(checks)]
  for name,vals in [('counts',counts),('crc',crc)]: (out/(name+'.mem')).write_text(''.join(f'{v:08x}\n' for v in vals))
  (out/'seeds.mem').write_text(''.join(f'{op<<272|target<<270|addr<<256|value:069x}\n' for op,target,addr,value in seeds))
  (out/'checks.mem').write_text(''.join(f'{op<<1040|target<<1038|addr<<1024|mask<<512|value:0261x}\n' for op,target,addr,value,mask in checks))
  (out/'reference.json').write_text(json.dumps(dict(kind=a.kind,epoch=epoch,variant=variant,images=images,payloads=payloads,expected_commits=len(payloads),expected_write_bytes={0:80,1:64,2:80,4:144}[a.kind]),indent=2)+'\n')
if __name__=='__main__':main()
