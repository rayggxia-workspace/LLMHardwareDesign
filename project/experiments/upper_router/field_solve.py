"""Run fresh hash-bound field rows and retain failed numerical attempts."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


def run(scene,build,controls,out,*,threads,walks,masters_path=None):
    meta=json.loads((scene/'scene.json').read_text());binary=build/'native_field'
    built=json.loads((build/'build.json').read_text());control=json.loads((controls/'controls.json').read_text())
    assert control['passed'] and control['binary_sha256']==built['binary_sha256']==sha(binary)
    assert meta['scene_sha256']==sha(scene/'scene.bin') and meta['complete_native_context']
    all_masters=list(map(int,(scene/'masters.txt').read_text().split()))
    masters_path=masters_path or scene/'masters.txt'
    masters=list(map(int,masters_path.read_text().split()))
    assert masters and len(set(masters))==len(masters) and set(masters)<=set(all_masters)
    out.mkdir()
    with (out/'rows.jsonl').open('xb') as stdout,(out/'field.log').open('xb') as stderr:
        subprocess.run([str(binary),str(scene/'scene.bin'),str(masters_path),str(threads),str(walks),'.25','104729'],
                       stdout=stdout,stderr=stderr,check=True)
    rows=[json.loads(s) for s in (out/'rows.jsonl').read_text().splitlines()]
    assert [r['master'] for r in rows]==masters
    details=[]
    for row in rows:
        # Client values already include the ground column as their last item.
        assert len(row['values'])==len(meta['names'])+1
        assert row['values'][-1]==row['ground']
        assert row['total_ff']>0 and abs(sum(v[0] for v in row['values']))<1e-8*row['total_ff']
        upper=sum(v[0] for v in row['node_self']);error=sum(v[1] for v in row['node_self'])
        assert upper>0
        details.append({'master':row['master'],'upper_ff':upper,'upper_sigma_bound_ff':error,
                        'relative_sigma_bound':error/upper,'field_total_relative_sigma':row['sigma_ff']/row['total_ff']})
    result={'passed':all(d['relative_sigma_bound']<=.02 and d['field_total_relative_sigma']<=.003 for d in details),
            'binary_sha256':sha(binary),'scene_sha256':sha(scene/'scene.bin'),'rows_sha256':sha(out/'rows.jsonl'),
            'masters':masters,'complete_master_coverage':masters==all_masters,
            'controls_sha256':sha(controls/'controls.json'),
            'minimum_walks':walks,'maximum_upper_relative_sigma_bound':max(d['relative_sigma_bound'] for d in details),
            'complete_native_context':True,'node_error_bound':'sum of standard errors, no independence assumption',
            'scope':'fresh full-native-context field C; distributed SPEF/STA remain separate gates'}
    (out/'solve.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'statistics.json').write_text(json.dumps(details,indent=2)+'\n');print(json.dumps(result))
    if not result['passed']:raise RuntimeError('field numerical error gate failed; retain run and increase walk budget')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('scene','build','controls','output'):p.add_argument(n,type=Path)
    p.add_argument('--threads',type=int,required=True);p.add_argument('--walks',type=int,default=262144)
    p.add_argument('--masters',type=Path)
    a=p.parse_args();run(a.scene,a.build,a.controls,a.output,threads=a.threads,walks=a.walks,masters_path=a.masters)
