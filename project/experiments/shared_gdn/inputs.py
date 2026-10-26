"""Server-only byte-exact reuse and explicit pointer relocation."""
import argparse,hashlib,json,struct,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=Path('/public/home/yuzelu/RuizhiLiang')
OLD=BASE/'issue106-shared-services-20261025/input01'
G=BASE/'issue104-gdn-state-20261025'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8',newline='\n')
def check(p):
 m=json.loads((p/'manifest.json').read_text())
 for e in m['artifacts']:
  assert sha(p/e['path'])==e['sha256'] and (p/e['path']).stat().st_size==e['bytes']
 return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
 om=check(OLD);copies=[];relocations=[]
 for q in OLD.iterdir():
  if q.is_file()and q.name!='manifest.json':shutil.copyfile(q,a.out/q.name);copies.append({'source':str(q),'target':q.name,'sha256':sha(q)})
 vectors=(OLD/'vectors.tsv').read_text().replace(str(OLD),str(a.out))
 for label,path in [('native',G/'input-native3201'),('rescale',G/'gateprepare01/rescale')]:
  im=check(path);image=bytearray((path/'image.bin').read_bytes());assert len(image)==1048576
  off=0xa1000+((int.from_bytes(image[0xa1080:0xa1090],'little')>>32)&1)*64+48
  old=struct.unpack_from('<4I',image,off);assert old[0]==0x040b0000 and old[1]==32 and old[2]in(0x04000000,0x04020000)and old[3]in(0x040a0000,0x040a0800)
  new=(old[0]+0x02200000,old[1],old[2]+0x02200000,old[3]+0x02200000);struct.pack_into('<4I',image,off,*new)
  (a.out/(label+'.bin')).write_bytes(image);shutil.copyfile(path/'coefficients.npz',a.out/(label+'.npz'))
  relocations.append({'label':label,'source':str(path),'manifest_sha256':sha(path/'manifest.json'),'original_image_sha256':sha(path/'image.bin'),'offset':off,'before':list(old),'after':list(new),'image':label+'.bin','coefficients':label+'.npz','original':im})
  vectors+='G '+label+' '+str(a.out/(label+'.bin'))+'\n'
 (a.out/'vectors.tsv').write_text(vectors,encoding='utf8',newline='\n')
 put(a.out/'manifest.json',{'schema':'shared109-input/1','status':'VERIFIED_PAYLOAD_REUSE_NOT_RTL','source':json.loads((ROOT/'binding.json').read_text()),'old_input':str(OLD),'old_manifest_sha256':sha(OLD/'manifest.json'),'copies':copies,'relocations':relocations,'artifacts':[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(a.out.iterdir())]})
 print('VERIFIED_PAYLOAD_REUSE_NOT_RTL')
if __name__=='__main__':main()
