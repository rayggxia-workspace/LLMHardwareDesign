"""Actual rehashed-file negatives through the frozen complete gamma receiver."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path('/public/home/yuzelu/RuizhiLiang/issue93-gamma-stream-20261025')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
 if not v:raise ValueError(s)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();need(a.out.resolve().parent==ROOT and not a.out.exists(),'new explicit task supplemental directory');a.out.mkdir()
 source=ROOT/'rtl-s003';receiver=ROOT/'phase7/project/experiments/gamma_stream/verify.py';im=ROOT/'input02';binding=json.loads((ROOT/'phase7/binding.json').read_text());need(sha(receiver)==binding['sources']['project/experiments/gamma_stream/verify.py'],'frozen final receiver');original=json.loads((source/'manifest.json').read_text());results=[]
 for name,field,error in [('changed_output','out','independent full row integer output'),('changed_global_den','den_words','one entireH sum/den')]:
  target=a.out/name;target.mkdir();mf=json.loads(json.dumps(original))
  for e in mf['artifacts']:
   need(Path(e['path']).name==e['path'] and sha(source/e['path'])==e['sha256']and(source/e['path']).stat().st_size==e['bytes'],'original actual artifact');shutil.copyfile(source/e['path'],target/e['path'])
  f=target/'actual.jsonl';lines=f.read_text().splitlines();row=json.loads(lines[0]);old=row[field][0];row[field][0]^=1;lines[0]=json.dumps(row,separators=(',',':'));f.write_text('\n'.join(lines)+'\n');entry=next(e for e in mf['artifacts']if e['path']=='actual.jsonl');entry.update(bytes=f.stat().st_size,sha256=sha(f));mf['derived_semantic_negative']={'field':field,'old':old,'new':row[field][0],'original_manifest_sha256':sha(source/'manifest.json')};(target/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n')
  # Every mutated file SHA/size is valid, before invoking the actual receiver.
  for e in mf['artifacts']:need(sha(target/e['path'])==e['sha256']and(target/e['path']).stat().st_size==e['bytes'],'rehashed mutated bundle')
  cmd=[sys.executable,'-B',str(receiver),'--input',str(im),'--run',str(target),'--out',str(target/'unexpected-pass.json')];r=subprocess.run(cmd,text=True,capture_output=True,timeout=120);(target/'receiver.stdout.log').write_text(r.stdout);(target/'receiver.stderr.log').write_text(r.stderr);need(r.returncode!=0 and ('ValueError: '+error)in r.stderr and not(target/'unexpected-pass.json').exists(),'must reject independent math, not artifact hash')
  results.append({'case':name,'status':'REJECTED_INDEPENDENT_MATH_AFTER_VALID_REHASH','argv':cmd,'returncode':r.returncode,'expected_error':error,'old_value':old,'new_value':row[field][0],'mutated_manifest_sha256':sha(target/'manifest.json'),'actual_jsonl_sha256':sha(f)})
 result={'schema':'gamma93-rehashed-semantic-negatives-v1','status':'PASS_BOTH_COMPLETE_RECEIVER_REJECTIONS','receiver_binding':binding,'receiver_sha256':sha(receiver),'helper_sha256':sha(__file__),'original_run_manifest_sha256':sha(source/'manifest.json'),'input_manifest_sha256':sha(im/'manifest.json'),'tests':results,'artifacts':[{'path':f.relative_to(a.out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)}for f in sorted(a.out.rglob('*'))if f.is_file()]};(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':main()
