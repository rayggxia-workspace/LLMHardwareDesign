"""Run independent electrostatic references on immutable actual calibration scenes.

The pilot exercises every generated family/target layer and the largest context.
Selected master rows include every context conductor; they are not a complete
parasitic extraction of the calibration chip or a qualified RCX model.
"""
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_rows(case, rows):
    expected={n['name']for n in case['nets']}|{'ground'}
    assert {r['master']for r in rows}==set(case['masters'])
    assert len(rows)==len(case['masters'])
    parsed={}
    for row in rows:
        assert row['case']=='%06d'%case['id'] and row['dimension']=='3D'
        entries={e['net']:e for e in row['entries']}
        assert set(entries)==expected and len(entries)==len(row['entries'])
        assert row['walks']>0 and row['hops']>0
        for net,e in entries.items():
            assert math.isfinite(e['cap'])and math.isfinite(e['sigma'])and e['sigma']>=0
        total=entries[row['master']]['cap']
        assert total>0 and entries[row['master']]['sigma']/total<=.003
        for net,e in entries.items():
            if net==row['master']:continue
            # Signed Monte Carlo estimates of near-zero couplings can change
            # sign. Reject statistically significant/non-negligible positives;
            # preserve every raw estimate rather than clipping the evidence.
            assert e['cap']<=min(5*e['sigma'],1e-4*total),(row['case'],row['master'],e)
        assert abs(sum(e['cap']for net,e in entries.items()if net!=row['master'])+total)<1e-9*max(1,total)
        parsed[row['master']]=entries
    # Independently solved Maxwell rows must agree within their stochastic
    # uncertainty, plus a 1% of total bound for capture/systematic effects.
    for a,ea in parsed.items():
        for b,eb in parsed.items():
            if a>=b:continue
            delta=abs(ea[b]['cap']-eb[a]['cap'])
            tolerance=5*math.hypot(ea[b]['sigma'],eb[a]['sigma'])+.01*min(ea[a]['cap'],eb[b]['cap'])
            assert delta<=tolerance,(a,b,delta,tolerance)


def pilot(root,out,cpus,shard=None,receive=False):
    base=out.parents[2]
    source=base/'block-v1-20261027-013/tasks/pattern-prepare'
    source_receipt=json.loads((source/'receipt.json').read_text())
    assert source_receipt['passed'] is True
    manifest_path=source/'reference-patterns/manifest.json'
    assert sha(manifest_path)==source_receipt['outputs']['reference-patterns/manifest.json']
    manifest=json.loads(manifest_path.read_text())
    assert manifest['schema']=='block-v1-reference-patterns/2'
    build=base/'block-v1-20261027-013/tasks/fsv-build'
    build_receipt=json.loads((build/'receipt.json').read_text())
    assert build_receipt['passed'] is True
    qualified=build/'fsv-qualified.json'
    assert sha(qualified)==build_receipt['outputs']['fsv-qualified.json']
    tool=json.loads(qualified.read_text());binary=Path(tool['binary'])
    assert sha(binary)==tool['binary_sha256']
    buckets={}
    for case in manifest['cases']:
        signal=[n for n in case['nets']if not n['context']and n['index']==3]
        assert len(signal)==1
        target=int(signal[0]['layer'][5:])
        key=(case['name'].split('_',1)[0],target)
        buckets.setdefault(key,[]).append(case)
    if shard is None:
        selected={}
        for key,cases in buckets.items():
            # Include largest context to catch shielding/grouping failures,
            # plus the first deterministic width/spacing case.
            for case in [cases[0],max(cases,key=lambda c:len(c['nets']))]:
                selected[case['id']]=case
        cases=sorted(selected.values(),key=lambda c:c['id'])
    else:
        assert 0<=shard<6 and (receive or cpus==96)
        passed=base/'block-v1-20261027-014/tasks/reference-pilot'
        prior=json.loads((passed/'receipt.json').read_text());assert prior['passed'] is True
        assert sha(passed/'reference-pilot.json')==prior['outputs']['reference-pilot.json']
        qualification=json.loads((passed/'reference-pilot.json').read_text())
        assert qualification['manifest_sha256']==sha(manifest_path)
        assert qualification['binary_sha256']==sha(binary)
        # R6 contributes only R to the official model. Its DC R is the actual
        # DEF length/width times the declared sheet resistance; computing C
        # would add no fitted data. Keep the complete R6 geometry in manifest.
        cases=[c for c in manifest['cases']if not c['name'].startswith('R6_')and c['id']%6==shard]
    workers=8 if receive else min(8,cpus//4);assert workers>0
    threads=12 if receive else cpus//workers
    shards=[cases[i::workers]for i in range(workers)]
    records=[]
    old=None
    if receive:
        old=base/('block-v1-20261027-015/tasks/reference-shard-%d'%shard)
        old_receipt=json.loads((old/'receipt.json').read_text())
        assert old_receipt['passed'] is False and old_receipt['error']=='AssertionError()'
        assert old_receipt['source_commit']=='a00bba4b31873eae05ad26a414906a6e7421a6c2'
    def solve(index,shard):
        listing=out/('scenes-%02d.txt'%index)
        for case in shard:
            scene=Path(case['scene']);assert sha(scene)==case['scene_sha256']
            assert scene.is_relative_to(source/'reference-patterns')
        listing.write_text(''.join(c['scene']+'\n'for c in shard))
        if receive:
            command=old/('command-%02d.json'%index)
            assert sha(command)==old_receipt['outputs'][command.name]
            record=json.loads(command.read_text())
            assert record['argv'][:3]==[str(binary),'scenelist3d',str(threads)]
            assert record['case_ids']==[c['id']for c in shard]and record['returncode']==0
            original_list=Path(record['argv'][3])
            assert sha(original_list)==old_receipt['outputs'][original_list.name]
            assert original_list.read_bytes()==listing.read_bytes()
            rows_path=old/('rows-%02d.jsonl'%index)
            assert sha(rows_path)==old_receipt['outputs'][rows_path.name]
            record['original_receipt']=str(old/'receipt.json')
            record['original_receipt_sha256']=sha(old/'receipt.json')
        else:
            argv=[str(binary),'scenelist3d',str(threads),str(listing)]
            started=time.time();rows_path=out/('rows-%02d.jsonl'%index)
            with rows_path.open('w')as stdout,(out/('solver-%02d.log'%index)).open('w')as stderr:
                result=subprocess.run(argv,stdout=stdout,stderr=stderr)
            record=dict(argv=argv,seconds=time.time()-started,returncode=result.returncode,
                        case_ids=[c['id']for c in shard])
        record['rows_file']=str(rows_path);record['rows_sha256']=sha(rows_path)
        (out/('command-%02d.json'%index)).write_text(json.dumps(record,indent=2)+'\n')
        assert record['returncode']==0,record
        rows=[json.loads(line)for line in rows_path.read_text().splitlines()]
        assert rows[-1]=={'status':'PASS','mode':'scenelist3d'}
        rows=rows[:-1];by_case={}
        for row in rows:by_case.setdefault(int(row['case']),[]).append(row)
        assert set(by_case)=={c['id']for c in shard}
        for case in shard:check_rows(case,by_case[case['id']])
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(cpus,workers))as pool:
        futures=[pool.submit(solve,i,shard)for i,shard in enumerate(shards)if shard]
        for future in futures:records.append(future.result())
    record=dict(schema='block-v1-reference-pilot/1'if shard is None else'block-v1-reference-shard/1',
                manifest=str(manifest_path),manifest_sha256=sha(manifest_path),shard=shard,
                qualified_solver=str(qualified),qualified_solver_sha256=sha(qualified),binary_sha256=sha(binary),
                cases=[dict(id=c['id'],name=c['name'],conductors=len(c['nets']),masters=c['masters'])for c in cases],
                family_target_layers=[list(key)for key in sorted(buckets)],workers=workers,threads_each=threads,commands=records,
                receive_only=receive,
                checks=['all scene conductors retained','finite Maxwell rows; positive off-diagonals <=5 sigma AND 0.01% total','row charge conservation',
                        'total statistical uncertainty <=0.3%','independent-row reciprocity within 5 sigma +1% total'],
                qualification='Selected physical Maxwell rows; model fit and held-out validation pending')
    (out/('reference-pilot.json'if shard is None else'reference-shard.json')).write_text(json.dumps(record,indent=2)+'\n')
