"""Read-only critical-path NLDM table diagnosis, never an STA lower-bound proof.

Uses the exact extracted path and library SHA. Grid minima allow different slew,
load, transition and conditional arcs at every cell, so cannot certify feasibility.
"""
from pathlib import Path
from functools import lru_cache
from collections import Counter
import argparse,csv,gzip,hashlib,json,re
from cell_semantics import groups,contract


def run(paths,liberty,out):
    paths,liberty,out=Path(paths),Path(liberty),Path(out);out.mkdir(parents=True,exist_ok=False)
    raw=paths.read_bytes();raw=gzip.decompress(raw) if paths.suffix=='.gz' else raw
    path=min(json.loads(raw)['checks'],key=lambda q:q['slack']);nodes=path['source_path']
    text=liberty.read_text();cells=dict(groups(text,'cell'));assert len(cells)>100
    unit=re.search(r'\btime_unit\s*:\s*"([\d.]+)(ns|ps|s)"',text);assert unit
    scale=float(unit[1])*{'ns':1,'ps':.001,'s':1e9}[unit[2]]
    semantics={name:contract('cell ("'+name+'") {'+body+'}',name) for name,body in cells.items() if list(groups(body,'pin'))}
    @lru_cache(maxsize=None)
    def arc_min(name,input_pin,output_pin):
        pin=dict(groups(cells[name],'pin'))[output_pin];values=[]
        for _,arc in groups(pin,'timing'):
            related=re.search(r'\brelated_pin\s*:\s*"([^"]+)"',arc)
            if not related or input_pin not in related[1].split():continue
            for kind in ['cell_rise','cell_fall']:
                for _,table in groups(arc,kind):
                    value=re.search(r'\bvalues\s*\((.*?)\)\s*;',table,re.S);assert value
                    values.extend(float(q)*scale for q in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',value[1]))
        assert values,('No matching actual combinational timing arc',name,input_pin,output_pin)
        return min(values)
    rows=[]
    for a,b in zip(nodes,nodes[1:]):
        if not a.get('instance') or a['instance']!=b.get('instance'):continue
        name=b['cell'];ip=a['pin'].rsplit('/',1)[1];op=b['pin'].rsplit('/',1)[1]
        family=re.sub(r'_X\d+$','',name)
        peers=[n for n in semantics if re.sub(r'_X\d+$','',n)==family and semantics[n]==semantics[name]]
        minima={n:arc_min(n,ip,op) for n in peers}
        best=min(minima,key=minima.get)
        rows.append({'arc_index':len(rows),'instance':b['instance'],'actual_master':name,'input_pin':ip,'output_pin':op,
          'actual_extracted_arrival_increment_ns':(b['arrival']-a['arrival'])*1e9,
          'current_master_table_grid_minimum_ns':minima[name],'same_function_family_best_table_grid_minimum_ns':minima[best],
          'best_grid_master':best,'available_exact_logic_state_family_masters':'/'.join(sorted(peers))})
    assert len(rows)==141
    with (out/'arcs.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'scope':'EXACT_LIBRARY_TABLE_GRID_DIAGNOSIS_NOT_ZERO_WIRE_STA_OR_PHYSICAL_FEASIBILITY_BOUND',
      'actual_extracted_path_SHA256':hashlib.sha256(raw).hexdigest(),'actual_Liberty_SHA256':hashlib.sha256(liberty.read_bytes()).hexdigest(),
      'startpoint':path['startpoint'],'endpoint':path['endpoint'],'actual_path_slack_ns':path['slack']*1e9,
      'actual_cell_arc_count':len(rows),'actual_cell_master_counts':dict(Counter(r['actual_master'] for r in rows)),
      'actual_extracted_cell_arrival_increment_sum_ns':sum(r['actual_extracted_arrival_increment_ns'] for r in rows),
      'current_master_independent_table_grid_minimum_sum_ns':sum(r['current_master_table_grid_minimum_ns'] for r in rows),
      'best_exact_function_family_independent_table_grid_minimum_sum_ns':sum(r['same_function_family_best_table_grid_minimum_ns'] for r in rows),
      'masters_on_path_with_no_exact_function_family_size_alternative':sorted({r['actual_master'] for r in rows if '/' not in r['available_exact_logic_state_family_masters']}),
      'all_original_constraints_and_physical_inputs_unchanged':True,'full_qualification':False,
      'is_zero_wire_lower_bound':False,'is_timing_repair_or_proof_infeasible':False,
      'limits':['Independent table-grid minima mix rise/fall, conditions, input slew and output load; not simultaneously realizable.',
        'Extrapolation outside characterized grids is not bounded; clock/launch/setup/hold and net RC omitted from grid sums.',
        'No cell size, placement, net, buffer, RTL, protocol, pipeline or constraint changed.']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k.endswith('_ns') or k=='masters_on_path_with_no_exact_function_family_size_alternative'}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--paths',required=True);p.add_argument('--liberty',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.paths,a.liberty,a.out)
