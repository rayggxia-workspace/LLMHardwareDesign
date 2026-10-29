"""Pair screen of all planned default via10 cuts at actual M10 hook boxes.

These are planned one-cut accesses, NOT actual routed vias or full DRC. The
cut-spacing input is explicit; route topology, OBS/PG and other rules remain
independent gates. Read only immutable snapshot material, never live ODBs.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,math


def run(snapshot,out,spacing):
    snapshot,out=Path(snapshot),Path(out);out.mkdir(parents=True,exist_ok=False)
    assert spacing>0;results=[];rows=[];base_shas=set()
    for mode in ['opentpu','llaccel']:
        path=snapshot/'upper_adaptation_trial/r02'/(mode+'_actual_hook_plan.json.gz')
        raw=gzip.decompress(path.read_bytes());plan=json.loads(raw)
        assert plan['edge_count']==770 and plan['used_actual_hook_boxes']==1540
        assert not plan['base_frozen'] and not plan['base_qualified']
        base_shas.add(plan['source_lower_checkpoint_SHA256'])
        cuts=[v['box_dbu'] for v in plan['native_via10_template_boxes'] if v['layer']=='via10']
        assert cuts==[[-800,-800,800,800]],'This screen only supports the actual fixed one-cut template'
        points=[]
        for edge in plan['physical_edges']:
            for t in edge['endpoints']:
                b=t['base_pin_box_dbu'];assert b[2]-b[0]==b[3]-b[1]==1600
                points.append({'edge_id':edge['edge_id'],'component':t['component'],
                  'x_um':(b[0]+b[2])/4000.,'y_um':(b[1]+b[3])/4000.})
        assert len(points)==1540 and len({(p['x_um'],p['y_um']) for p in points})==1540
        nearest=[(float('inf'),None) for p in points];conflicts=[];tested=0
        for i,a in enumerate(points):
            for j in range(i):
                b=points[j];tested+=1
                dx=max(0,abs(a['x_um']-b['x_um'])-.8)
                dy=max(0,abs(a['y_um']-b['y_um'])-.8)
                distance=math.hypot(dx,dy)
                if distance<nearest[i][0]:nearest[i]=(distance,j)
                if distance<nearest[j][0]:nearest[j]=(distance,i)
                if distance<spacing-1e-9:conflicts.append({'a':i,'b':j,'cut_rectangle_gap_um':distance})
        for i,p in enumerate(points):
            gap,j=nearest[i]
            rows.append(dict(p,mode=mode,nearest_component=points[j]['component'],nearest_edge_id=points[j]['edge_id'],
              nearest_cut_rectangle_gap_um=gap,assumed_cut_spacing_um=spacing,screen_margin_um=gap-spacing))
        results.append({'mode':mode,'planned_hook_count':1540,'all_pairs_tested':tested,
          'minimum_cut_rectangle_gap_um':min(v[0] for v in nearest),'conflicts':conflicts,
          'source_plan_raw_sha256':hashlib.sha256(raw).hexdigest(),'source_plan_stored_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'source_research_tech_SHA256':plan['research_technology_SHA256'],'source_lower_checkpoint_SHA256':plan['source_lower_checkpoint_SHA256']})
    assert len(base_shas)==1
    table=out/'planned_via10_nearest.csv'
    with table.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    result={'scope':'ALL_PLANNED_DEFAULT_VIA10_PAIR_GEOMETRIC_SCREEN_NOT_ACTUAL_VIA_PLACEMENT_OR_DRC',
      'full_qualification':False,'cut_spacing_um_explicit_assumption':spacing,
      'assumption_source':'extend_upper_tech.py clones original via9 cut spacing 0.88um; native via10 template in each exact hook plan is 0.8um square. This screen does not certify the technology model.',
      'geometry_source':'Actual native lower M10 hook boxes exported into immutable plans; no hypothetical blank-space interpretation.',
      'checked':['All 1540 planned hook centers per mode','All unordered cut-rectangle pairs per mode','Exact native default via10 template footprint inside existing M10 hook box'],
      'not_checked':['Actual routed via placement','PRL/EOL/enclosure/OBS/PG/antenna or full rule deck','Route access or congestion','Normalized lower freeze','RC or system STA/function'],
      'modes':results,'table_sha256':hashlib.sha256(table.read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('ALL_PLANNED_VIA10_PAIR_SCREEN',[(r['mode'],r['all_pairs_tested'],r['minimum_cut_rectangle_gap_um'],len(r['conflicts'])) for r in results])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--out',required=True);p.add_argument('--cut-spacing-um',type=float,required=True);a=p.parse_args();run(a.snapshot,a.out,a.cut_spacing_um)
