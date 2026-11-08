"""Collect disjoint, hash-bound field shards without changing any C result."""
import argparse
import json
from pathlib import Path
from field_solve import sha


def collect(scene,shards,out):
    meta=json.loads((scene/'scene.json').read_text())
    assert meta['complete_native_context'] and sha(scene/'scene.bin')==meta['scene_sha256']
    expected=list(map(int,(scene/'masters.txt').read_text().split()))
    selected={};provenance={};identity=None;maximum=0
    for shard in shards:
        receipt=shard/'solve.json';report=json.loads(receipt.read_text());rows_path=shard/'rows.jsonl'
        assert report['passed'] and report['complete_native_context']
        assert report['scene_sha256']==meta['scene_sha256'] and report['rows_sha256']==sha(rows_path)
        current=(report['binary_sha256'],report['controls_sha256'])
        if identity is None:identity=current
        assert identity==current,'shards used different solvers or controls'
        rows=[json.loads(s) for s in rows_path.read_text().splitlines()]
        assert [r['master'] for r in rows]==report['masters']
        for row in rows:
            master=row['master'];assert master in expected and master not in selected,'missing/overlapping master'
            assert row['net']==meta['names'][master]
            assert len(row['values'])==len(meta['names'])+1 and row['values'][-1]==row['ground']
            assert row['total_ff']>0 and abs(sum(x[0] for x in row['values']))<1e-8*row['total_ff']
            upper=sum(x[0] for x in row['node_self']);sigma=sum(x[1] for x in row['node_self'])
            assert upper>0 and 0<=sigma/upper<=.02 and 0<=row['sigma_ff']/row['total_ff']<=.003
            maximum=max(maximum,sigma/upper);selected[master]=row
            provenance[master]={'receipt':str(receipt),'receipt_sha256':sha(receipt),
                                'rows_sha256':report['rows_sha256']}
    assert set(selected)==set(expected),'incomplete field coverage'
    out.mkdir();merged=out/'rows.jsonl'
    merged.write_text(''.join(json.dumps(selected[m],separators=(',',':'))+'\n' for m in expected))
    result={'passed':True,'complete_native_context':True,'complete_master_coverage':True,
            'scene_sha256':meta['scene_sha256'],'binary_sha256':identity[0],'controls_sha256':identity[1],
            'rows_sha256':sha(merged),'masters':expected,'maximum_upper_relative_sigma_bound':maximum,
            'per_row_provenance':provenance,'scope':'fresh joint-scene field results; electrical/STA gates separate'}
    (out/'solve.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('output',type=Path)
    p.add_argument('shards',nargs='+',type=Path);a=p.parse_args();collect(a.scene,a.shards,a.output)
