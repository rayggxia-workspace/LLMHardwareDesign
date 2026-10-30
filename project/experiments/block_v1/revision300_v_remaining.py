"""Read-only geometry and route eligibility for the measured old-V remainder."""
from collections import Counter, defaultdict
from decimal import Decimal
import json,re


def inspect(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import records,parse
    from native_rect_completion import complement
    from revision300_v_via_batch import pairs,contains,name_of
    assert cpus==16
    base=out.parents[2]
    source=base/'block-v1-20261030-598/tasks/revision300-v-geometry-compose'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']
    for name in ('revision300-v-geometry-compose.json','composed-candidate.odb',
                 'composed-candidate.def','composed-native-drc.rpt'):
        assert file_sha(source/name)==receipt['outputs'][name]
    original=base/'block-v1-20261030-557/tasks/revision300-v-spacing-localize'
    prior=json.loads((original/'receipt.json').read_text());assert prior['passed']
    helper=original/'selected-geometry.tcl';assert file_sha(helper)==prior['outputs'][helper.name]
    odb=source/'composed-candidate.odb';definition=source/'composed-candidate.def'
    report=source/'composed-native-drc.rpt';text=report.read_text()
    pattern=(r'violation type: Metal Spacing\n\s*srcs: net:([^\n]+)\n'
             r'\s*bbox = \(([-\d.]+), ([-\d.]+)\) - '
             r'\(([-\d.]+), ([-\d.]+)\) on Layer (metal\d+)')
    markers=[]
    for m in re.finditer(pattern,text):
        name,*values,layer=m.groups();coords=[Decimal(x)*2000 for x in values]
        assert all(v==int(v)for v in coords)
        markers.append(dict(net=name,layer=layer,bbox_dbu=list(map(int,coords))))
    expected=json.loads((source/'revision300-v-geometry-compose.json').read_text())
    assert len(markers)==text.count('violation type:')==expected['composed_native_count']==172
    script=('set_thread_count 16\nread_db {'+str(odb)+'}\nsource {'+str(helper)+
            '}\nbvgeom::export selected-geometry.tsv\n')
    (out/'read-remaining.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'read-remaining.tcl'],'read-remaining.log')
    geometry=out/'selected-geometry.tsv'
    # The installed path iterator omits explicit RECTs. Include actual sealed
    # DEF rectangles before interpreting any local union or marker window.
    completion=complement(geometry,definition,'v',require_historic_m_patch=False)
    aliases={};by_net=defaultdict(list)
    for line in geometry.read_text().splitlines():
        if line.startswith('# NET '):
            _,_,alias,name=line.split();aliases[alias]=bytes.fromhex(name).decode().replace('\\','')
        elif line and not line.startswith('#'):
            alias,layer,shape,*box=line.split('\t')
            by_net[aliases[alias]].append(dict(layer=layer,shape=shape,bbox_dbu=list(map(int,box))))
    wanted={m['net'].replace('\\','')for m in markers};paths={};rect_counts={}
    for record in records(definition):
        name=name_of(record)
        if name in wanted:
            assert name not in paths
            start=re.search(r'\+ ROUTED\s+',record);assert start
            pieces=re.split(r'\s+NEW\s+',record[start.end():].strip().removesuffix(';').strip())
            rect_counts[name]=sum(len(re.findall(r'\bRECT\b',p))for p in pieces)
            nonrect=[p for p in pieces if not re.search(r'\bRECT\b',p)]
            assert nonrect
            # The path grammar excludes RECT. Its real shapes are already
            # included by the complete, independently parsed DEF complement.
            _,paths[name]=parse(record[:start.start()]+'+ ROUTED '+' NEW '.join(nonrect)+' ;')
    assert set(paths)==wanted
    counts=Counter();located=[]
    for index,marker in enumerate(markers):
        name=marker['net'].replace('\\','');layer=marker['layer'];x0,y0,x1,y1=marker['bbox_dbu']
        nearby=[r for r in by_net[name]if r['layer']==layer and r['bbox_dbu'][0]<x1+1000
                and r['bbox_dbu'][2]>x0-1000 and r['bbox_dbu'][1]<y1+1000 and r['bbox_dbu'][3]>y0-1000]
        row=dict(marker=marker,same_net_nearby_rectangles=nearby);options=[]
        for a,b in pairs(row):
            wire=[p for p in paths[name]if contains(p,layer,a,b)]
            via_layer='metal1'if layer=='metal1'else'metal2'
            av=[p for p in paths[name]if p['layer']==via_layer and p['via']and len(p['points'])==1 and tuple(p['points'][0][:2])==a]
            bv=[p for p in paths[name]if p['layer']==via_layer and p['via']and len(p['points'])==1 and tuple(p['points'][0][:2])==b]
            end=all(any(p['layer']=='metal2'and not p['via']and point in [tuple(t[:2])for t in p['points']]for p in paths[name])for point in(a,b))
            segment=all(any(contains(p,'metal2',point,point)for p in paths[name])for point in(a,b))
            options.append(dict(a=a,b=b,source_wire_count=len(wire),a_via_names=[p['via']for p in av],
                                b_via_names=[p['via']for p in bv],m2_endpoint_branches=end,m2_segment_branches=segment))
        reason='no_geometric_pair'if not options else'pair_needs_route_review'
        for o in options:
            if o['source_wire_count']==1 and len(o['a_via_names'])==len(o['b_via_names'])==1:
                reason='via_pair_without_m2_branches'
                if o['m2_segment_branches']:reason='general_via_pair_m2_segment_eligible';break
        counts[reason]+=1;located.append(dict(index=index,**row,route_options=options,classification=reason,
                                             nonrect_def_paths=paths[name],actual_def_rectangles=rect_counts[name]))
    unchanged=all(file_sha(source/name)==receipt['outputs'][name]for name in
                  ('composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt'))
    result=dict(passed=unchanged,diagnostic_only=True,physical_qualified=False,
                source_receipt_sha256=file_sha(source/'receipt.json'),input_odb_sha256=file_sha(odb),
                source_database_and_reports_unchanged=unchanged,native_marker_count=len(markers),
                layers=dict(Counter(m['layer']for m in markers)),eligibility_counts=dict(counts),
                geometry_helper_sha256=file_sha(helper),explicit_rect_completion=completion,markers=located,
                scope='Actual composed old523 geometry/DEF and route eligibility only. No repair, '
                      'terminal-connectivity proof, DRC waiver or current588/final qualification.')
    (out/'revision300-v-remaining.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
