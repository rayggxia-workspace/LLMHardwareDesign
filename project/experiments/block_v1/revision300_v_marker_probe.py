"""Explicitly encode already-covered same-net rectangles in a derived copy.

Preserve failed originals. This probe is not a final-source implementation.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path


def area(rectangles, target):
    x0,y0,x1,y1=target
    cuts=sorted({x0,x1}|{max(x0,min(x1,b[i]))for b in rectangles for i in(0,2)})
    result=0
    for left,right in zip(cuts,cuts[1:]):
        intervals=sorted((max(y0,b[1]),min(y1,b[3]))for b in rectangles
                         if b[0]<right and b[2]>left and b[1]<y1 and b[3]>y0)
        previous=y0;length=0
        for low,high in intervals:
            length+=max(0,high-max(previous,low));previous=max(previous,high)
        result+=(right-left)*length
    return result


def shapes(path):
    names={};rows=Counter()
    for line in path.read_text().splitlines():
        if line.startswith('# NET '):
            _,_,alias,name=line.split();names[alias]=bytes.fromhex(name).decode()
        elif line and not line.startswith('#'):
            alias,layer,kind,*coords=line.split('\t')
            rows[(names[alias],layer,kind,*map(int,coords))]+=1
    return rows


def probe(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    # Positive/negative guard controls exercise union coverage, not the DRC
    # checker. No rectangle outside the original same-net metal is admitted.
    assert area([[0,0,4,10],[6,0,10,10]],[0,0,10,10])==80
    assert area([[0,0,7,10],[3,0,10,10]],[0,0,10,10])==100
    base=out.parents[2]
    previous=base/'block-v1-20261030-557/tasks/revision300-v-spacing-localize'
    pr=json.loads((previous/'receipt.json').read_text());assert pr['passed']
    path=previous/'revision300-v-physical-localization.json'
    assert file_sha(path)==pr['outputs'][path.name]
    d=json.loads(path.read_text());assert d['passed']and d['source_run']=='523'and len(d['markers'])==445
    odb=Path(d['input_odb']);expected=d['input_odb_sha256'];assert file_sha(odb)==expected
    geometry=previous/'selected-geometry.tsv';helper=previous/'selected-geometry.tcl'
    assert file_sha(geometry)==pr['outputs'][geometry.name]and file_sha(helper)==pr['outputs'][helper.name]
    before=shapes(geometry);assert before
    grouped=defaultdict(list);additions=Counter()
    for row in d['markers']:
        m=row['marker'];box=m['bbox_dbu'];x0,y0,x1,y1=box
        assert x0<x1 and y0<y1 and len(box)==4
        nearby=row['same_net_nearby_rectangles']
        assert all(r['layer']==m['layer']and r['net'].replace('\\','')==m['net'].replace('\\','')for r in nearby)
        assert area([r['bbox_dbu']for r in nearby if r['shape']in('wire','wire-via')],box)==(x1-x0)*(y1-y0)
        names={name for name,layer,kind,*coords in before if name.replace('\\','')==m['net'].replace('\\','')}
        assert len(names)==1
        name=next(iter(names));grouped[name].append((m['layer'],box))
        additions[(name,m['layer'],'wire',*box)]+=1
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
    for name,records in sorted(grouped.items()):
        script+='set net [$block findNet [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\n'
        script+='if {$net eq "NULL"} {error "Missing exact net"}\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_append $enc [$net getWire]\n'
        for layer,(x0,y0,x1,y1)in records:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+layer+'] ROUTED\n'
            script+='odb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db explicit-rectangles.odb\nsource {'+str(helper)+'}\nbvgeom::export selected-after.tsv\n'
    script+='drt::check_drc_cmd explicit-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'probe.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'probe.tcl'],'probe.log')
    assert file_sha(odb)==expected
    actual=shapes(out/'selected-after.tsv')
    counts=dict(expected_added_rectangles=sum(additions.values()),actual_added_rectangles=sum((actual-before).values()),
                missing_original_rectangles=sum((before-actual).values()),exact_counter_matches=actual==before+additions)
    remaining=(out/'explicit-native-drc.rpt').read_text()
    result=dict(passed=counts['exact_counter_matches']and not remaining.strip(),diagnostic_only=True,
                input_odb=str(odb),input_odb_sha256=expected,original_unchanged=True,
                actual_localization_receipt_sha256=file_sha(previous/'receipt.json'),
                original_report_sha256=d['failed_report_sha256'],
                original_marker_count=445,derived_marker_count=remaining.count('violation type:'),
                geometry_counter_checks=counts,all_added_rectangles_inside_same_net_union=True,
                selected_net_union_unchanged=counts['exact_counter_matches'],
                full_library_qualified=False,
                remaining='Derived copy only. Full all-net geometry/XOR, connectivity, fresh final/RCX/STA/electrical, full unmodified GDS deck, final-netlist function and strict LEC remain mandatory; old setup23/cap1 failure is retained.')
    (out/'revision300-v-marker-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Explicit-rectangle derived control failed; raw original and candidate evidence retained'


def readback(root,out,cpus,run):
    """Diagnose failed probe using native DEF, including iterator-missing RECTs."""
    import re
    from io_slots import file_sha
    from native_escape import records
    from native_rect_completion import rectangles
    assert cpus==16
    base=out.parents[2]
    previous=base/'block-v1-20261030-560/tasks/revision300-v-marker-probe'
    receipt=json.loads((previous/'receipt.json').read_text())
    report=previous/'revision300-v-marker-probe.json'
    assert not receipt['passed'] and file_sha(report)==receipt['outputs'][report.name]
    d=json.loads(report.read_text());assert not d['passed']and d['derived_marker_count']==440
    original=Path(d['input_odb']);candidate=previous/'explicit-rectangles.odb'
    assert file_sha(original)==d['input_odb_sha256']
    assert file_sha(candidate)==receipt['outputs'][candidate.name]
    for name,odb in [('original',original),('candidate',candidate)]:
        script='set_thread_count 16\nread_db {'+str(odb)+'}\nwrite_def '+name+'.def\n'
        (out/(name+'.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',out/(name+'.tcl')],name+'.log')
    assert file_sha(original)==d['input_odb_sha256']
    assert file_sha(candidate)==receipt['outputs'][candidate.name]
    before=Counter();after=Counter();nonrect=[];nets=[]
    for name,total in [('original',before),('candidate',after)]:
        paths=Counter();count=0
        for record in records(out/(name+'.def')):
            count+=1;total.update(rectangles(record))
            # Every non-RECT route path and NETS header must remain exact.
            # Independent DEF writer emits one record per logical normal net.
            route=re.search(r'\+\s+(?:ROUTED|FIXED|COVER)\s+',record)
            if route is None:
                paths[('unrouted',re.sub(r'\s+',' ',record).strip())]+=1
                continue
            header=re.sub(r'\s+',' ',record[:route.start()]).strip()
            body=record[route.end():].strip().removesuffix(';').strip()
            kept=tuple(sorted(re.sub(r'\s+',' ',p).strip()for p in re.split(r'\s+NEW\s+',body)
                              if not re.search(r'\bRECT\b',p)))
            paths[(header,kept)]+=1
        nonrect.append(paths);nets.append(count)
    localization=base/'block-v1-20261030-557/tasks/revision300-v-spacing-localize/revision300-v-physical-localization.json'
    lr=localization.parent/'receipt.json'
    assert file_sha(lr)==d['actual_localization_receipt_sha256']
    assert file_sha(localization)==json.loads(lr.read_text())['outputs'][localization.name]
    markers=json.loads(localization.read_text())['markers'];expected=Counter()
    # DEF names use backslash escaping; compare normalized exact net identities.
    def normalize(rows):
        result=Counter()
        for (name,layer,*box),count in rows.items():
            result[(name.replace('\\',''),layer,*box)]+=count
        return result
    for row in markers:
        m=row['marker'];expected[(m['net'].replace('\\',''),m['layer'],*m['bbox_dbu'])]+=1
    added=normalize(after)-normalize(before)
    missing=normalize(before)-normalize(after)
    exact=added==expected and not missing
    result=dict(passed=exact and nonrect[0]==nonrect[1],diagnostic_only=True,
                original_odb_sha256=file_sha(original),candidate_odb_sha256=file_sha(candidate),
                original_def_sha256=file_sha(out/'original.def'),candidate_def_sha256=file_sha(out/'candidate.def'),
                probe_receipt_sha256=file_sha(previous/'receipt.json'),localization_sha256=file_sha(localization),
                original_unchanged=True,candidate_unchanged=True,normal_net_counts=nets,
                original_rectangles=sum(before.values()),candidate_rectangles=sum(after.values()),
                added_rectangles=sum(added.values()),missing_rectangles=sum(missing.values()),
                exact_expected_445_rectangles=exact,all_nonrect_routes_and_normal_net_headers_identical=nonrect[0]==nonrect[1],
                native_drc_remaining=440,physical_qualified=False,
                scope='Read-only failed-probe diagnosis. Path iterator omits RECT; native DEF separately verifies them. Does not repair remaining440 native spacing violations or grant final physical qualification.')
    (out/'revision300-v-marker-readback.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Native DEF rectangle diagnosis failed; retain actual evidence'
