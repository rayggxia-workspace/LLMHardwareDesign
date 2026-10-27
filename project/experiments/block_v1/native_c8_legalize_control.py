"""Bounded routing preflight on sealed real C8 geometry and oracle controls."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import random
from native_c8_geometry import UPPER,Obstacles,replace
from native_c8_legalize import legalize
from native_escape_audit import geometry
from native_upper_index import audit


def verify(results,folder,out):
    assert not out.exists();actual=[]
    budget=Path(__file__).with_name('physical-budget.json');size=json.loads(budget.read_text())['leaves']['shared109']['die_um']
    die=(0,0,*[round(v*2000)for v in size])
    for policy in 'ac':
        index=results/('run163'+policy+'-terminal/index.json');data=json.loads(index.read_text())
        proof=data['tasks']['native-c8-locate-'+policy]['artifacts']['native-c8-location.json']['content']
        path=folder/('c8-upper163-'+policy+'.tsv');digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert proof['passed']is True and digest==proof['source_geometry_sha256']
        source=geometry(path);report,texts,plans,scene=legalize(proof,source,die)
        again,texts2,plans2,scene2=legalize(proof,source,die)
        assert report['passed']is True and report==again and texts==texts2 and plans==plans2
        assert set(source)==set(scene)
        for name in source:
            if name not in report['changed_nets']:assert collections.Counter(source[name])==collections.Counter(scene[name])
        complete=audit(scene);assert complete['passed']is True
        sample=report['changed_nets'][0];original=proof['source_routes'][sample]
        one=next(r for r in source[sample]if r[0]=='metal10'and r[1]=='wire')
        damaged=[r for r in source[sample]if r!=one]
        try:replace(damaged,original,texts[sample])
        except AssertionError:pass
        else:raise AssertionError('Missing native source rectangle accepted')
        obstacle=Obstacles(scene);one=next(r for r in scene[sample]if r[0]=='metal10')
        obstacle.add('__declared_unreported_net__',[one]);assert obstacle.violations(sample,scene[sample])
        actual.append(dict(policy=policy,index_sha256=hashlib.sha256(index.read_bytes()).hexdigest(),geometry_sha256=digest,
            geometry_bytes=path.stat().st_size,report=report,complete_upper_audit=complete,deterministic_repeat=True,
            missing_source_rectangle_rejected=True,unreported_foreign_obstacle_rejected=True))
    rng=random.Random(165);controls=[]
    for case in range(12):
        scene=collections.defaultdict(list)
        for i in range(60):
            x,y=[rng.randrange(-100,101)*160 for _ in range(2)];w,h=[rng.choice([1,160,1600,6400,12800])for _ in range(2)]
            scene['net'+str(rng.randrange(5))].append((rng.choice(UPPER),'declared',(x,y,x+w,y+h)))
        indexed=Obstacles(scene,pitch=rng.choice([513,1600,6400]))
        for name,rows in scene.items():
            expected=[]
            for layer,kind,a in rows:
                spacing=1760 if layer=='via9'else 1600
                for other,rs in scene.items():
                    if other==name:continue
                    for other_layer,other_kind,b in rs:
                        if layer!=other_layer:continue
                        dx=max(0,a[0]-b[2],b[0]-a[2]);dy=max(0,a[1]-b[3],b[1]-a[3])
                        if dx*dx+dy*dy<spacing*spacing:expected.append(dict(net=name,other=other,layer=layer,box=a,other_box=b,distance_squared=dx*dx+dy*dy,required_spacing_dbu=spacing))
            counter=lambda values:collections.Counter(json.dumps(v,sort_keys=True)for v in values)
            assert counter(expected)==counter(indexed.violations(name,rows))
        controls.append(dict(case=case,exact_pair_counter_equal=True,pitch_dbu=indexed.pitch))
    sources=[Path(__file__),*[Path(__file__).with_name(name)for name in ['native_c8_geometry.py','native_c8_legalize.py','native_c8_escape.py','native_upper_index.py']]]
    result=dict(passed=True,actual=actual,declared_oracle_controls=controls,budget_sha256=hashlib.sha256(budget.read_bytes()).hexdigest(),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},qualified_hard_macro=False,
        scope='Actual sealed source-geometry preflight, deterministic repeat and independent exhaustive spacing-pair oracle only; no real database edit or native DRC/RC/STA/function qualification')
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,actual_candidates=len(actual),declared_oracle_cases=len(controls),changes=[len(v['report']['changed_nets'])for v in actual])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    for name in ['results','folder','out']:parser.add_argument(name,type=Path)
    args=parser.parse_args();verify(args.results,args.folder,args.out)
