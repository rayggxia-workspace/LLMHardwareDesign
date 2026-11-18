"""Create a replayable public copy; omit legacy commercial simulator transcripts."""
from pathlib import Path
from hashlib import sha256
import json,shutil,subprocess,sys,zipfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
TARGET=ROOT/'tmp/recurrent-300mhz/public-export'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    assert not TARGET.exists(), 'Use a fresh export directory; do not overwrite evidence.'
    dest=TARGET/HERE.relative_to(ROOT)
    shutil.copytree(HERE,dest,ignore=shutil.ignore_patterns('__pycache__','report-before-r300.pdf'))
    for rel in ['docs/experiments/recurrent-state-latest-300mhz.pdf','docs/handoffs/2026-11-18-issue-280-recurrent-300mhz.md','work/Melodydt/280/report-sync/render_sync06.py','work/Melodydt/280/report-sync/build_sync04_reports.py']:
        p=TARGET/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
    receipt={'omitted_fields':[],'original_inputs_unchanged':True,'reason':'Legacy commercial simulator transcripts excluded; public files retain numeric verdicts and provenance.'}
    rel='work/Melodydt/280/recurrent-step1/calibration-tb-check.json';p=dest/'inputs'/rel
    original=digest(p);obj=json.loads(p.read_bytes())
    def sanitize(v,path=''):
        if isinstance(v,dict):
            for key in list(v):
                if key in ('log','rtl_log'):
                    raw=json.dumps(v.pop(key),ensure_ascii=False).encode()
                    receipt['omitted_fields'].append({'path':path+'/'+key,'sha256_of_json_value':sha256(raw).hexdigest(),'bytes':len(raw)})
                else:sanitize(v[key],path+'/'+key)
        elif isinstance(v,list):
            for i,item in enumerate(v):sanitize(item,path+'/'+str(i))
    sanitize(obj);assert receipt['omitted_fields'];dump(p,obj)
    receipt.update(file=rel,original_sha256=original,public_sha256=digest(p))
    manifest=json.loads((dest/'input-manifest.json').read_bytes())
    manifest['files'][rel].update(sha256=digest(p),bytes=p.stat().st_size)
    manifest['public_export']='Legacy transcript fields omitted; see public-export.json for original SHA.'
    dump(dest/'input-manifest.json',manifest)
    original_roll=json.loads((dest/'candidate-rollup.json').read_bytes())
    for script in ('integrate.py','verify_integration.py'):
        subprocess.run([sys.executable,'-B',str(dest/script)],cwd=TARGET,check=True,capture_output=True)
    new_roll=json.loads((dest/'candidate-rollup.json').read_bytes())
    assert new_roll['models']==original_roll['models']
    receipt['numeric_model_results_identical']=True
    dump(dest/'public-export.json',receipt)
    for p in dest.rglob('*'):
        if p.is_file() and p.suffix in ('.json','.log','.txt'):
            txt=p.read_text(encoding='utf-8')
            assert 'ModelSim SE-' not in txt and 'License checkout failed' not in txt,p
    files=[p for p in TARGET.rglob('*') if p.is_file()]
    manifest={p.relative_to(TARGET).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}
    package=ROOT/'output/pdf/recurrent-300mhz-v5-results-public.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,p.relative_to(TARGET).as_posix())
        z.writestr('MANIFEST.json',json.dumps({'files':manifest,'public_export':receipt},indent=2))
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        for rel,r in manifest.items():assert sha256(z.read(rel)).hexdigest()==r['sha256']
    dump(HERE/'public-bundle-receipt.json',{'file':package.relative_to(ROOT).as_posix(),'sha256':digest(package),'bytes':package.stat().st_size,'members':len(manifest)+1,'numeric_replay':'PASS','crc_and_sha256':'PASS','public_export':receipt})
    print(json.dumps({'package':str(package),'bytes':package.stat().st_size,'members':len(manifest)+1,'omitted_fields':len(receipt['omitted_fields'])}))
if __name__=='__main__':main()
