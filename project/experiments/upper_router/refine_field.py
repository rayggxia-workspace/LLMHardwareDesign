"""Refine only field rows that fail the unchanged numerical error gates."""
import argparse
import json
from pathlib import Path
import subprocess
from field_solve import sha


def run(scene,build,controls,previous,out,*,threads,masters_path=None):
    out.mkdir();meta=json.loads((scene/'scene.json').read_text())
    binary=build/'native_field';built=json.loads((build/'build.json').read_text())
    control=json.loads((controls/'controls.json').read_text())
    assert control['passed'] and control['binary_sha256']==built['binary_sha256']==sha(binary)
    assert meta['scene_sha256']==sha(scene/'scene.bin') and meta['complete_native_context']
    all_masters=list(map(int,(scene/'masters.txt').read_text().split()))
    expected=list(map(int,(masters_path or scene/'masters.txt').read_text().split()))
    assert expected and len(set(expected))==len(expected) and set(expected)<=set(all_masters)
    selected={};provenance={};attempts=[]
    def error(row):
        assert row['net']==meta['names'][row['master']]
        assert row['total_ff']>0 and len(row['values'])==len(meta['names'])+1
        assert row['values'][-1]==row['ground'] and abs(sum(v[0] for v in row['values']))<1e-8*row['total_ff']
        c=sum(v[0] for v in row['node_self']);s=sum(v[1] for v in row['node_self'])
        assert c>0 and s>=0
        return max(s/c/.02,row['sigma_ff']/row['total_ff']/.003)
    def ingest(path):
        fingerprint=sha(path)
        for line in path.read_text().splitlines():
            row=json.loads(line);master=row['master'];assert master in expected
            score=error(row)
            if master not in selected or score<error(selected[master]):
                selected[master]=row;provenance[master]={'path':str(path),'sha256':fingerprint}
    for receipt in sorted(previous.glob('walks-*/solve.json')):
        report=json.loads(receipt.read_text());path=receipt.with_name('rows.jsonl')
        assert report['scene_sha256']==meta['scene_sha256'] and report['binary_sha256']==sha(binary)
        assert report['rows_sha256']==sha(path);ingest(path)
    assert set(selected)==set(expected),'prior full coverage missing'
    for budget in (16777216,67108864,268435456):
        failed=[m for m in expected if error(selected[m])>1]
        if not failed:break
        directory=out/('walks-'+str(budget));directory.mkdir()
        masters=directory/'masters.txt';masters.write_text('\n'.join(map(str,failed))+'\n')
        with (directory/'rows.jsonl').open('xb') as stdout,(directory/'field.log').open('xb') as stderr:
            subprocess.run([str(binary),str(scene/'scene.bin'),str(masters),str(threads),str(budget),'.25','104729'],
                           stdout=stdout,stderr=stderr,check=True)
        (directory/'inputs.json').write_text(json.dumps({'scene_sha256':meta['scene_sha256'],
            'binary_sha256':sha(binary),'minimum_walks':budget,'masters':failed},indent=2)+'\n')
        ingest(directory/'rows.jsonl');attempts.append({'minimum_walks':budget,'refined_masters':failed,
              'remaining_failed':[m for m in expected if error(selected[m])>1]})
    merged=out/'rows.jsonl';merged.write_text(''.join(json.dumps(selected[m],separators=(',',':'))+'\n' for m in expected))
    report={'passed':all(error(selected[m])<=1 for m in expected),'scene_sha256':meta['scene_sha256'],
            'binary_sha256':sha(binary),'rows_sha256':sha(merged),'masters':expected,
            'controls_sha256':sha(controls/'controls.json'),'complete_master_coverage':expected==all_masters,
            'complete_native_context':True,'maximum_upper_relative_sigma_bound':max(sum(v[1] for v in r['node_self'])/sum(v[0] for v in r['node_self']) for r in selected.values()),
            'attempts':attempts,'per_row_provenance':provenance,
            'scope':'all field rows meet original 2% upper-C and .3% total-C standard-error gates; failed numerical attempts retained'}
    (out/'solve.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='per_row_provenance'}))
    assert report['passed'],'field numerical refinement exhausted its declared budgets'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('scene','build','controls','previous','output'):p.add_argument(n,type=Path)
    p.add_argument('--threads',type=int,required=True);p.add_argument('--masters',type=Path);a=p.parse_args()
    run(a.scene,a.build,a.controls,a.previous,a.output,threads=a.threads,masters_path=a.masters)
