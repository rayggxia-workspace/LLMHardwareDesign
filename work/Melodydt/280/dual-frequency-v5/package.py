from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone,timedelta
import json,shutil,zipfile,csv
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
def load(p):return json.loads(p.read_bytes())
def sha(p):return sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    d=load(H/'results.json');v=load(H/'verification.json');pdf=load(H/'pdf-checks.json');assert v['passed']
    for p in pdf:assert p['visual_review'].startswith('PASS') and sha(ROOT/p['file'])==p['sha256']
    index=ROOT/'output/pdf/seven-model-reports-latest.json'
    backup=H/'previous-report-index.json'
    if backup.exists():assert load(index)['data_version']=='SYNC-08'
    else:shutil.copyfile(index,backup)
    formal=[]
    for r in pdf:
        p=ROOT/'docs/experiments'/Path(r['file']).name;shutil.copyfile(ROOT/r['file'],p);formal.append(p)
    with (H/'summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        out=csv.writer(f);out.writerow(['model','MHz','window','seconds','tokens/s','scope','W_low','W_high','mJ/token_low','mJ/token_high'])
        for m in d['models']:
            for phase,w in m['windows'].items():
                for freq,x in w['frequencies'].items():
                    for scope,met in x['scopes'].items():out.writerow([m['name'],freq,phase,x['duration_s'],x['tokens_per_second'],scope]+met['average_power_w']+met['energy_mj_per_token'])
    handoff=ROOT/'docs/handoffs/2026-11-19-issue-280-dual-frequency-v5.md';shutil.copyfile(H/'README.md',handoff)
    new=dict(data_version='SYNC-08',published_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),source_snapshot=str(H),stable_filenames=False,
        files=[dict(file=Path(r['file']).name,frequency_mhz=r['frequency_mhz'],sha256=r['sha256'],pages=r['pages']) for r in pdf],
        source_update_changes=['200MHz基于最新300MHz v5逐项推算，替换旧基线历史表','两频率使用各自R标定收窄Qwen3.5/Falcon','七模型P512/Decode、片上/片上+DDR、W/mJ/token和分项/缺项齐全','频率响应迁移及方法敏感性单列；无新200MHz E32-18回放'],
        numeric_checks=v['numeric_checks'],input_sha256_verified=v['frozen_inputs'],legacy_fixed_names_are_not_latest=True)
    dump(index,new)
    paths=[p for p in H.rglob('*') if p.is_file() and p.name not in ('bundle-receipt.json','previous-report-index.json') and '__pycache__' not in p.parts]+formal+[handoff]
    manifest={p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths}
    zip_path=ROOT/'output/pdf/seven-model-dual-frequency-v5-evidence.zip'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(zip_path) as z:
        assert z.testzip() is None
        for rel,m in manifest.items():assert sha256(z.read(rel)).hexdigest()==m['sha256']
    dump(H/'bundle-receipt.json',dict(file=zip_path.relative_to(ROOT).as_posix(),sha256=sha(zip_path),bytes=zip_path.stat().st_size,members=len(manifest)+1,crc_and_sha256='PASS'))
    print(json.dumps({'pdfs':len(pdf),'pages':sum(p['pages'] for p in pdf),'bundle_bytes':zip_path.stat().st_size,'members':len(manifest)+1}))
if __name__=='__main__':main()
