"""Real saved-data adversarial readback; no model rerun and no Phi tuning."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n',newline='\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 a.out.mkdir();source=a.root/'phase13';capture=a.root/'qwen25-gqa01';records=[]
 bad=a.out/'rehashed-integer';shutil.copytree(a.root/'qwen25-integer01',bad);p=bad/'encoded-linears.npz';z=np.load(p,allow_pickle=False);arrays={k:z[k]for k in z.files};key=next(k for k in arrays if k.endswith('.out'));old=int(arrays[key][0,0]);arrays[key][0,0]=old+1 if old<127 else old-1;np.savez_compressed(p,**arrays)
 m=json.loads((bad/'manifest.json').read_text());m['artifacts']['encoded-linears.npz']={'bytes':p.stat().st_size,'sha256':sha(p)};save(bad/'manifest.json',m)
 run=subprocess.run([sys.executable,'-B',str(source/'receive_probe.py'),'--result',str(bad),'--capture',str(capture),'--out',str(bad/'unexpected-pass.json')],capture_output=True,text=True)
 (a.out/'integer-rejected.log').write_text(run.stdout+run.stderr,newline='\n')
 if run.returncode==0 or 'Fraction RNE/output mutation'not in run.stderr:raise AssertionError('arithmetic mutation not rejected for expected reason')
 records.append({'kind':'actual Qwen2.5 saved INT8 output changed and producer NPZ SHA recomputed','status':'REJECTED_AS_EXPECTED','returncode':run.returncode,'key':key,'old':old,'new':int(arrays[key][0,0]),'mutated_npz_sha256':sha(p)})
 bad=a.out/'rehashed-export';shutil.copytree(a.root/'qwen25-strict02',bad);doc=json.loads((bad/'prefix128/capture.json').read_text());t=next(t for t in doc['tensors']if t['name'].endswith('_A_row0'));p=bad/'prefix128'/t['file']['path'];data=bytearray(p.read_bytes());data[0]^=1;p.write_bytes(data);t['file']['sha256']=sha(p);save(bad/'prefix128/capture.json',doc)
 idx=json.loads((bad/'index.json').read_text());next(r for r in idx['cases']if r['case']=='prefix128')['capture_json_sha256']=sha(bad/'prefix128/capture.json');save(bad/'index.json',idx)
 run=subprocess.run([sys.executable,'-B',str(source/'integer_precision/capture.py'),str(bad/'prefix128')],capture_output=True,text=True)
 if run.returncode:raise AssertionError('negative should pass internal schema/hash check first '+run.stderr)
 run=subprocess.run([sys.executable,'-B',str(source/'validate_export.py'),'--capture',str(capture),'--export',str(bad),'--out',str(bad/'unexpected-pass.json')],capture_output=True,text=True);(a.out/'export-rejected.log').write_text(run.stdout+run.stderr,newline='\n')
 if run.returncode==0 or 'export payload differs from bound native source'not in run.stderr:raise AssertionError('source binding mutation not rejected')
 records.append({'kind':'actual exported FP32 activation low mantissa bit changed, SHA and index recomputed; internal schema passed','status':'REJECTED_AS_EXPECTED','returncode':run.returncode,'tensor':t['name'],'mutated_payload_sha256':sha(p)})
 save(a.out/'negative-receipt.json',{'status':'PASS','source_scope':'Qwen2.5 actual saved artifacts only, no model rerun, Phi untouched','checks':records});print(json.dumps({'status':'PASS','actual_negative_checks':len(records)}))
if __name__=='__main__':main()
