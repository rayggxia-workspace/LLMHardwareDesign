"""SHA-bound lossless export of actual PR36 continuous state windows; no new inference."""
import argparse,gzip,hashlib,io,json,os,platform,zipfile
from pathlib import Path
import numpy as np
import torch

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',newline='\n')
def npz(path,arrays):
 with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for k,a in sorted(arrays.items()):
   buf=io.BytesIO();np.save(buf,a,allow_pickle=False)
   info=zipfile.ZipInfo(k+'.npy',(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,buf.getvalue())
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 b=json.loads(a.binding.read_text())
 if sha(__file__)!=b['source_sha256']or sha(a.input)!='049c1cf4e81044fdc740dd1e65701a86293f31293d4b0ee2c554daecfef4e91a':raise ValueError('source/input SHA')
 if not os.environ.get('SLURM_JOB_ID'):raise ValueError('Slurm required')
 torch.set_num_threads(1);torch.set_num_interop_threads(1)
 raw=gzip.decompress(a.input.read_bytes());payload=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
 arrays={};windows={}
 wanted={f'layer{l}-end{t}'for l in (0,14,30)for t in (2048,2049,8192,8193)}
 if set(payload)!=wanted:raise ValueError('unexpected window inventory')
 for name,fields in sorted(payload.items()):
  windows[name]={}
  for k,v in fields.items():
   x=v.detach().cpu().numpy().copy()
   if x.dtype!=np.float32 or not np.isfinite(x).all():raise ValueError('dtype/finite')
   arrays[name+'.'+k]=x;windows[name][k]={'shape':list(x.shape),'dtype':str(x.dtype)}
 a.out.mkdir();npz(a.out/'windows.npz',arrays)
 save(a.out/'manifest.json',{'status':'PASS','source_commit':b['commit'],'source_sha256':sha(__file__),'input':{'path':str(a.input),'sha256':sha(a.input),'uncompressed_sha256':hashlib.sha256(raw).hexdigest()},'origin_commit':'2ada6cf6a61f5acff4b6052e81e15d20070dc0f3','scope':__doc__,'windows':windows,'artifacts':{'windows.npz':{'bytes':(a.out/'windows.npz').stat().st_size,'sha256':sha(a.out/'windows.npz')}},'environment':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__},'job_id':os.environ['SLURM_JOB_ID']})
 print(json.dumps({'status':'PASS','windows':len(windows),'arrays':len(arrays)}))
if __name__=='__main__':main()
