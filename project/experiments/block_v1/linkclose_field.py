"""Independent 3-D coupons for the declared 2um research stack, not a foundry PDK."""
import json
from pathlib import Path
from interconnect_spef import sha


def measure(root,out,cpus,run,kind):
    assert cpus==16 and kind in ('short','long','via','dense','upper')
    base=out.parents[2];qualified=base/'block-v1-20261027-013/tasks/fsv-build'
    receipt=json.loads((qualified/'receipt.json').read_text());assert receipt['passed']
    path=qualified/'fsv-qualified.json';assert sha(path)==receipt['outputs'][path.name]
    tool=json.loads(path.read_text());binary=Path(tool['binary']);assert sha(binary)==tool['binary_sha256']
    length=32 if kind=='short' else 64
    boxes=[]
    def box(name,x0,y0,z0,x1,y1,z1):boxes.append((name,[x0,y0,z0,x1,y1,z1]))
    box('target',-length/2,-1,12.89,length/2,1,14.89)
    # Eight-micron-center signal tracks; patterned native M10 and crossed M12.
    # The finite length difference measures end-effect sensitivity independently
    # of the old analytic capacitance. Every electrode retains its identity.
    pitch=4 if kind in ('dense','upper') else 8
    for y in (-pitch,pitch):box('neighbor'+str(y),-length/2,y-1,12.89,length/2,y+1,14.89)
    for x in range(-length//2,length//2+1,8):
        box('lower'+str(x),x-.4,-16,10.09,x+.4,16,12.09)
        box('upper'+str(x),x-1,-16,15.69,x+1,16,17.69)
    if kind=='upper':
        # Rotate the target/coplanar lines to M12 and retain crossed M11
        # conductors below; there is no invented upper ground plane.
        boxes=[b for b in boxes if not b[0].startswith('upper')]
        boxes=[(name,([b[1],b[0],15.69,b[4],b[3],17.69] if name=='target' or name.startswith('neighbor') else b))for name,b in boxes]
        for y in range(-length//2,length//2+1,4):box('middle'+str(y),-16,y-1,12.89,16,y+1,14.89)
    if kind=='via':
        box('target',-1,-1,10.09,1,1,12.89)
        box('target',-1,-1,14.89,1,1,17.69)
        # Remove coincident foreign crossing electrodes at the target junction.
        boxes=[b for b in boxes if b[0] not in ('lower0','upper0')]
        box('target',-1,-12,15.69,1,12,17.69)
    scene='background 3.9\nmaster target\n'+''.join('box '+name+' '+' '.join(map(str,b))+'\n' for name,b in boxes)
    (out/'scene.txt').write_text(scene)
    run([str(binary),'scene3d','16',str(out/'scene.txt')],'field.jsonl')
    rows=[json.loads(line)for line in (out/'field.jsonl').read_text().splitlines()]
    assert rows.pop()==dict(status='PASS',mode='scene3d') and len(rows)==1
    row=rows[0];entries={e['net']:e for e in row['entries']}
    total=entries['target']['cap'];ground=-entries['ground']['cap'];sigma=entries['target']['sigma']
    coupling=sum(-r['cap'] for n,r in entries.items() if n not in ('target','ground'))
    assert total>0 and ground>=0 and coupling>=0 and abs(total-ground-coupling)<1e-8*total
    checks=dict(signs=all(r['cap']<=5*r['sigma'] for n,r in entries.items() if n!='target'),
                relative_uncertainty_5sigma=5*sigma/total<.05)
    record=dict(passed=all(checks.values()),kind=kind,length_um=length,boxes=boxes,
        scene_sha256=sha(out/'scene.txt'),solver_sha256=sha(binary),qualified_solver_receipt_sha256=sha(qualified/'receipt.json'),
        total_ff=total,ground_ff=ground,coupling_ff=coupling,opposite_switching_miller_ff=ground+2*coupling,signal_pitch_um=pitch,
        sigma_ff=sigma,checks=checks,row=row,manufacturing_calibrated=False,
        scope='Independent finite3D homogeneous-epsilon research-stack coupon with same-layer8um pitch, native patterned M10 and crossed M12. Miller2 scenario is a conservative load scenario for this coupon, not dynamic SI signoff or a bound on arbitrary layouts.')
    (out/'linkclose-field.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'Preserve scientific gate failure; do not treat it as calibrated RC'
