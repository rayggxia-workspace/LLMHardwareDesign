"""Generate current dual-P images and independent zlib CRC32 loader references."""
from pathlib import Path
import sys,json,zlib,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'control_p16_native_v1'))
from images import build
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
images=[];args=[]
for i,(name,data) in enumerate(build()):
 p=out/(name+'.mem')
 p.write_text(''.join(f'{int.from_bytes(data[n:n+16],"little"):032x}\n' for n in range(0,len(data),16)))
 crc=zlib.crc32(data)
 images.append({'target':i,'name':name,'image_bytes':len(data),'crc32_ieee':f'{crc:08x}','image_sha256':hashlib.sha256(data).hexdigest(),'mem_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 args.extend([f'+{("MOTHER","LOCAL0","LOCAL1")[i]}={p.resolve()}',f'+{("MWORDS","WORDS0","WORDS1")[i]}={len(data)//16}',f'+CRC{i}={crc:08x}'])
(out/'loader-manifest.json').write_text(json.dumps({'instruction_bits':64,'image_version':2,'images':images},indent=2)+'\n')
print('\n'.join(args))
