"""Measure bounded 3D window behavior against a complete finite layout scene.

This qualifies client plumbing/local-tail diagnostics only. It does not solve
the separate distributed-C partition or native/new-layer stitching problem.
"""
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import subprocess


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root,out,cpus):
    assert cpus>=16
    solver=out.parents[2]/'block-v1-20261027-063/tasks/fsv-build'
    receipt=json.loads((solver/'receipt.json').read_text());assert receipt['passed']is True
    qualified=solver/'fsv-qualified.json';assert sha(qualified)==receipt['outputs'][qualified.name]
    record=json.loads(qualified.read_text());binary=Path(record['binary']);assert sha(binary)==record['binary_sha256']
    boxes=[]
    for i in range(-64,65):
        # Fifty-micron horizontal/vertical finite wires, extending to +/-205um.
        boxes.append(('target'if i==0 else'h_%d'%(i+64),[-24.4,i*3.2-.4,12.89,24.4,i*3.2+.4,14.89]))
        boxes.append(('v_%d'%(i+64),[i*3.2-.4,-24.4,15.69,i*3.2+.4,24.4,17.69]))
    for x in [-4.8,4.8]:boxes.append(('PG',[x-.4,-240,10.09,x+.4,240,12.09]))
    variants=[('full',None),('window16',16),('window64',64),('window128',128)]
    specs=[]
    for name,margin in variants:
        bounds=None if margin is None else[-24.4-margin,-.4-margin,24.4+margin,.4+margin]
        selected=[]
        for net,original in boxes:
            box=original[:]
            if bounds:
                box[0]=max(box[0],bounds[0]);box[1]=max(box[1],bounds[1])
                box[3]=min(box[3],bounds[2]);box[4]=min(box[4],bounds[3])
            if box[0]<box[3]and box[1]<box[4]:selected.append((net,box))
        text='background 3.9\nmaster target\nground PG\n'
        if bounds:text+='window '+' '.join(map(str,bounds))+'\n'
        text+=''.join('box '+net+' '+' '.join('%.12g'%v for v in box)+'\n'for net,box in selected)
        scene=out/(name+'.txt');scene.write_text(text)
        specs.append(dict(name=name,margin_um=margin,window_xy_um=bounds,scene_sha256=sha(scene),boxes=selected))
    def solve(spec):
        log=out/(spec['name']+'.jsonl')
        with log.open('w')as stream:
            code=subprocess.run([str(binary),'scene3d',str(cpus//4),str(out/(spec['name']+'.txt'))],stdout=stream,stderr=subprocess.STDOUT).returncode
        assert code==0,log
        rows=[json.loads(line)for line in log.read_text().splitlines()]
        assert len(rows)==2 and rows[-1]=={'status':'PASS','mode':'scene3d'}
        row=rows[0];assert row['master']=='target'
        assert row['window_recorded']==(spec['margin_um']is not None)
        assert math.isfinite(row['window_leakage'])and row['window_leakage']>=0
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
        rows=dict(zip([s['name']for s in specs],pool.map(solve,specs)))
    reference={e['net']:e for e in rows['full']['entries']}
    total=reference['target']['cap'];assert total>0
    results={}
    for spec in specs[1:]:
        row=rows[spec['name']];entries={e['net']:e for e in row['entries']}
        sigma=math.hypot(reference['target']['sigma'],entries['target']['sigma'])
        total_error=abs(entries['target']['cap']-total)
        retained=[]
        for net,entry in entries.items():
            if net in ('ground','target','PG'):continue
            expected=reference[net]
            difference=abs(entry['cap']-expected['cap'])
            allowed=.02*abs(expected['cap'])+.005*total+5*math.hypot(entry['sigma'],expected['sigma'])
            retained.append(difference<=allowed)
        omitted=[e for net,e in reference.items()if net not in entries and net not in ('ground','PG')]
        tail=sum(max(0,-e['cap'])for e in omitted)
        tail_sigma=math.sqrt(sum(e['sigma']**2 for e in omitted))
        checks=dict(total=total_error<=.01*total+5*sigma,
            retained_couplings=all(retained),omitted_tail=tail<=.005*total+5*tail_sigma,
            reported_window_leakage=row['window_leakage']<=.01*total)
        results[spec['name']]=dict(passed=all(checks.values()),checks=checks,total_error_ff=total_error,
            total_reference_ff=total,omitted_coupling_ff=tail,omitted_count=len(omitted),
            window_leakage_ff=row['window_leakage'],window_leakage_over_total=row['window_leakage']/total)
    result=dict(schema='block-v1-field-window/1',passed=results['window128']['passed'],solver_sha256=sha(binary),
        full_conductor_boxes=len(boxes),scenes=specs,results=results,
        gates=dict(total_fraction=.01,retained_pair_fraction=.02,retained_total_fraction=.005,
                   omitted_tail_fraction=.005,window_leakage_fraction=.01,sigma_factor=5),
        scope='Finite complete-scene vs local 3D window/PG controls; no full-block distributed-C or boundary-stitch qualification')
    (out/'field-window.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Largest predeclared window failed its locked bounds'
