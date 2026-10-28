"""Whole 770-edge physical adapter audit, not a full-system/frozen-base proof."""
from pathlib import Path
from collections import defaultdict
import csv,gzip,re
from check_access import check


def audit(out,plan):
    out=Path(out);assert len(plan['physical_edges'])==770
    result={'all_edge_signal_clock_geometry':check(out/'whole_access.tsv.gz',True)}
    expected={h['helper_pin']:h for e in plan['physical_edges'] for h in e['endpoints']}
    assert len(expected)==1540
    with gzip.open(str(out/'whole_access.tsv.gz'),'rt') as f:records=list(csv.DictReader(f,delimiter='\t'))
    terms={};net_edges=defaultdict(set);vias=defaultdict(set);m10=0
    for q in records:
        if q['kind']!='BTERM':continue
        pin=q['link'][2:];assert pin not in terms and pin in expected and q['layer']=='metal10'
        assert [int(q[k]) for k in ['x0','y0','x1','y1']]==expected[pin]['base_pin_box_dbu']
        terms[pin]=q;net_edges[q['net']].add(int(re.search(r'\[(\d+)\]',pin)[1]))
    assert set(terms)==set(expected) and len(net_edges)==770 and all(len(v)==1 for v in net_edges.values())
    for q in records:
        index=next(iter(net_edges[q['net']]));assert plan['physical_edges'][index]['edge_id']==index
        boxes=[h['base_pin_box_dbu'] for h in plan['physical_edges'][index]['endpoints']]
        b=[int(q[k]) for k in ['x0','y0','x1','y1']]
        if q['layer']=='metal10':
            assert any(a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3] for a in boxes),('M10 material outside original actual hook',q)
            m10+=1
        else:assert q['layer'] in ['metal11','metal12','via10','via11'],('Forbidden lower-layer/cut material',q)
        if q['kind']=='VIA' and q['layer'] in ['via10','via11']:vias[q['layer']].add((q['net'],q['link']))
    result.update({'actual_770_native_edge_terminal_bijection':True,
      'all_actual_overlay_M10_material_contained_in_existing_base_hook_rectangles':True,
      'new_material_below_M10_or_original_cut1_cut9_count':0,'observed_M10_geometry_rows_with_duplicates':m10,
      'actual_via_definition_instances':{k:len(v) for k,v in vias.items()},
      'same_lower_material_proof_scope':'Same immutable partial base input plus exact overlay M10 containment; not qualified freeze, complete composed database/LVS or two functional systems.'})
    return result
