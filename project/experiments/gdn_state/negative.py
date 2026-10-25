"""Actual artifact mutation plus recomputed manifest hash must fail full receiver."""
import argparse,json,shutil,struct,subprocess,sys
from pathlib import Path
from inputs import sha,put
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);cases=[]
for name in ['output_code','state_code','stage_code','row_metadata','unexpected_schema','wrong_contract']:
 root=a.out/name;shutil.copytree(a.run,root);m=json.loads((root/'manifest.json').read_text())
 if name in('output_code','state_code'):
  path=root/'actual.bin';x=bytearray(path.read_bytes());offset=133200+(131152 if name=='output_code'else 80);x[offset]^=1;path.write_bytes(x)
 elif name=='stage_code':
  path=root/'stages.bin';x=bytearray(path.read_bytes());x[24]^=1;path.write_bytes(x)
 elif name in('row_metadata','unexpected_schema'):
  path=root/'actual.jsonl';rows=[json.loads(x)for x in path.read_text().splitlines()]
  if name=='row_metadata':rows[1]['position']+=1
  else:rows[1]['extra_unknown']=0
  path.write_text(''.join(json.dumps(x)+'\n'for x in rows),encoding='utf8',newline='\n')
 else:m['contract']['state_max']+=1
 for e in m['artifacts']:e.update(bytes=(root/e['path']).stat().st_size,sha256=sha(root/e['path']))
 put(root/'manifest.json',m);argv=[sys.executable,str(P/'verify.py'),'--run',str(root),'--input',str(a.input),'--out',str(a.out/(name+'-rejected'))];r=subprocess.run(argv,capture_output=True,text=True);(a.out/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf8',newline='\n');assert r.returncode!=0 and 'artifact bytes/hash'not in r.stderr,(name,r.stdout,r.stderr)
 cases.append({'name':name,'exit':r.returncode,'manifest_sha256':sha(root/'manifest.json'),'log_sha256':sha(a.out/(name+'.log')),'error_tail':r.stderr[-600:],'all_artifacts_rehashed':True})
put(a.out/'receipt.json',{'schema':'gdn104-artifact-negatives-v1','status':'PASS_FULL_RECEIVER_REJECTS_REHASHED_SEMANTIC_MUTATIONS','source_run_manifest_sha256':sha(a.run/'manifest.json'),'receiver_sha256':sha(P/'verify.py'),'cases':cases});print('PASS_NEGATIVE',len(cases))
