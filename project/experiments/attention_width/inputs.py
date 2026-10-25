"""Only byte reuse: relocate exact existing79-query inputs, retain immutable capture provenance."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OLD=Path('/public/home/yuzelu/RuizhiLiang/issue102-attention-rtl-20261025/input02')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);m=json.loads((OLD/'manifest.json').read_text());original=sha(OLD/'manifest.json')
 for e in m['artifacts']:
  src=OLD/e['path'];assert sha(src)==e['sha256']and src.stat().st_size==e['bytes'];target=a.out/e['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
 vectors=a.out/'vectors.tsv';s=vectors.read_text();assert str(OLD)in s;s=s.replace(str(OLD),str(a.out));vectors.write_text(s,newline='\n')
 m['reuse']={'old_manifest':str(OLD/'manifest.json'),'sha256':original,'only_changed_payload':'vectors.tsv absolute task-root paths; all numeric bytes unchanged','receiver_source':json.loads((ROOT/'binding.json').read_text())}
 for e in m['artifacts']:e.update(bytes=(a.out/e['path']).stat().st_size,sha256=sha(a.out/e['path']))
 (a.out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n');print('REUSED79_UNCHANGED_NUMERIC_PAYLOADS')
if __name__=='__main__':main()
