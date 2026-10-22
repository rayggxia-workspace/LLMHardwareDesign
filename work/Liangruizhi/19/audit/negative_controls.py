"""Run rejection controls on one isolated, restored D-drive evidence copy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

def encoded(obj): return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
def digest(data): return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('run',type=Path);p.add_argument('--verify',type=Path,required=True)
    p.add_argument('--copy',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    root=Path('D:/Projects/Codex/interface-contract-20261022/independent-audit').resolve()
    target=a.copy.resolve()
    if target.exists() or not target.is_relative_to(root):
        raise ValueError('Use a new isolated directory under the audit task root')
    before={p.relative_to(a.run).as_posix():digest(p.read_bytes()) for p in a.run.rglob('*') if p.is_file()}
    shutil.copytree(a.run,target)
    original={n:(a.run/n).read_bytes() for n in ['manifest.json','inputs/capture.json','views.json','summary.json','inputs/ACT20.lef']}
    records=[]
    def restore():
        for name,data in original.items():(target/name).write_bytes(data)
    def reindex():
        manifest=json.loads((target/'manifest.json').read_bytes())
        for name,info in manifest['files'].items():
            data=(target/name).read_bytes()
            info.update(bytes=len(data),sha256=digest(data))
        manifest['input_manifest_sha256']=digest((target/'inputs/capture.json').read_bytes())
        (target/'manifest.json').write_bytes(encoded(manifest))
    def change_json(name,fn):
        obj=json.loads((target/name).read_bytes());fn(obj)
        (target/name).write_bytes(encoded(obj))
    cases=[
       ('collector_sha',lambda:change_json('inputs/capture.json',lambda d:d.update(collector_sha256='0'*64)),'Capture collector/archive provenance changed'),
       ('archive_sha',lambda:change_json('inputs/capture.json',lambda d:d.update(reused_lef16_archive_sha256='0'*64)),'Capture collector/archive provenance changed'),
       ('missing_output_bit',lambda:change_json('views.json',lambda d:d['ACT20']['bits'].pop('r_data[0]')),'Replay differs: views.json'),
       ('wrong_liberty_line',lambda:change_json('views.json',lambda d:d['ACT20']['bits']['r_data[0]']['liberty'].update(line=1)),'Replay differs: views.json'),
       ('wrong_lef_geometry',lambda:change_json('views.json',lambda d:d['ACT20']['bits']['r_data[0]']['lef']['ports'][0]['rects'][0]['rect_dbu'].__setitem__(0,d['ACT20']['bits']['r_data[0]']['lef']['ports'][0]['rects'][0]['rect_dbu'][0]+1)),'Replay differs: views.json'),
       ('false_scope_claim',lambda:change_json('summary.json',lambda d:d['limitations'].update(legal_signal_access_verified=True)),'Replay differs: summary.json'),
    ]
    for name,mutate,message in cases:
        restore();mutate();reindex()
        r=subprocess.run([sys.executable,'-B',str(a.verify),str(target)],capture_output=True,text=True,timeout=60)
        accepted=r.returncode!=0 and message in r.stderr
        records.append({'case':name,'self_consistent_outer_manifest':True,'expected_failure':message,
                        'exit_code':r.returncode,'rejected_as_expected':accepted})
        if not accepted:
            raise AssertionError(json.dumps(records[-1])+'\n'+r.stdout+'\n'+r.stderr)
    restore()
    after={p.relative_to(a.run).as_posix():digest(p.read_bytes()) for p in a.run.rglob('*') if p.is_file()}
    restored={p.relative_to(target).as_posix():digest(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
    if before!=after or before!=restored: raise AssertionError('Original evidence changed or negative copy not restored')
    result={'status':'PASS','negative_cases':records,'copy_restored_to_original':True,
            'production_directory_unmodified':True,'script_sha256':digest(Path(__file__).read_bytes()),
            'run_manifest_sha256':digest(original['manifest.json'])}
    a.out.write_bytes(encoded(result));print(json.dumps(result))
if __name__=='__main__':main()
