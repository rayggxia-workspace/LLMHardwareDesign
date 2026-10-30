"""One bounded same-net corner-fill diagnostic; never final acceptance."""
from collections import Counter,defaultdict
import json,re
from pathlib import Path
from revision300_v_marker_probe import area


def candidates(markers):
    chosen=[];skipped=[]
    for index,row in enumerate(markers):
        m=row['marker'];box=m['bbox_dbu'];x0,y0,x1,y1=box
        rects=[r['bbox_dbu']for r in row['same_net_nearby_rectangles']
               if r['shape']in ('wire','wire-via')]
        covering=[r for r in rects if r[0]<=x0 and r[1]<=y0 and r[2]>=x1 and r[3]>=y1]
        proposals=[]
        for cover in covering:
            if cover[2]-cover[0]<cover[3]-cover[1]:
                lower=[r for r in rects if r[3]==y0 and r[0]<x1 and r[2]>x0]
                upper=[r for r in rects if r[1]==y1 and r[0]<x1 and r[2]>x0]
                proposals.extend([min(a[0],b[0],x0),y0,max(a[2],b[2],x1),y1]
                                 for a in lower for b in upper)
            elif cover[2]-cover[0]>cover[3]-cover[1]:
                left=[r for r in rects if r[2]==x0 and r[1]<y1 and r[3]>y0]
                right=[r for r in rects if r[0]==x1 and r[1]<y1 and r[3]>y0]
                proposals.extend([x0,min(a[1],b[1],y0),x1,max(a[3],b[3],y1)]
                                 for a in left for b in right)
        if not covering:
            # Five original gaps spanning multiple conductor rectangles were
            # removed by the explicit marker RECT in the separate560 control.
            proposals.append(box)
        options=[]
        for p in proposals:
            width=p[2]-p[0];height=p[3]-p[1]
            if width<=0 or height<=0 or max(width,height)>2000:continue
            extra=width*height-area(rects,p)
            if extra>0 or not covering:options.append((extra,width*height,tuple(p)))
        if not options:
            skipped.append(index);continue
        extra,_,p=min(options)
        chosen.append(dict(index=index,net=m['net'],layer=m['layer'],bbox_dbu=list(p),
                           estimated_added_area_dbu2=extra,original_marker_bbox_dbu=box))
    return chosen,skipped


def def_content(path):
    from native_escape import records
    from native_rect_completion import rectangles
    rects=Counter();routes=Counter();count=0
    for record in records(path):
        count+=1;rects.update(rectangles(record))
        route=re.search(r'\+\s+(?:ROUTED|FIXED|COVER)\s+',record)
        if route is None:
            routes[('unrouted',re.sub(r'\s+',' ',record).strip())]+=1;continue
        header=re.sub(r'\s+',' ',record[:route.start()]).strip()
        body=record[route.end():].strip().removesuffix(';').strip()
        kept=tuple(sorted(re.sub(r'\s+',' ',p).strip()for p in re.split(r'\s+NEW\s+',body)
                          if not re.search(r'\bRECT\b',p)))
        routes[(header,kept)]+=1
    normalized=Counter()
    for (name,layer,*box),n in rects.items():normalized[(name.replace('\\',''),layer,*box)]+=n
    return normalized,routes,count


def violations(text):
    result=Counter(re.sub(r'\s+',' ',v).strip()for v in re.split(r'(?m)(?=^violation type:)',text)if v.strip())
    assert sum(result.values())==len(re.findall(r'(?m)^violation type:',text))
    return result


def probe(root,out,cpus,run,filter_added=False):
    from io_slots import file_sha
    assert cpus==16
    base=out.parents[2];previous=base/'block-v1-20261030-557/tasks/revision300-v-spacing-localize'
    receipt=json.loads((previous/'receipt.json').read_text());assert receipt['passed']
    report=previous/'revision300-v-physical-localization.json'
    assert file_sha(report)==receipt['outputs'][report.name]
    d=json.loads(report.read_text());original=Path(d['input_odb'])
    assert d['source_run']=='523'and file_sha(original)==d['input_odb_sha256']
    native=previous/'native-whole-drc.rpt'
    assert file_sha(native)==receipt['outputs'][native.name]==d['failed_report_sha256']
    prior=base/'block-v1-20261030-562/tasks/revision300-v-marker-readback'
    pr=json.loads((prior/'receipt.json').read_text());assert pr['passed']
    original_def=prior/'original.def';assert file_sha(original_def)==pr['outputs'][original_def.name]
    rd=prior/'revision300-v-marker-readback.json';assert file_sha(rd)==pr['outputs'][rd.name]
    assert json.loads(rd.read_text())['original_odb_sha256']==file_sha(original)
    chosen,skipped=candidates(d['markers']);assert chosen
    filtered=[];filter_provenance=None
    if filter_added:
        failed=base/'block-v1-20261030-566/tasks/revision300-v-corner-probe'
        fr=json.loads((failed/'receipt.json').read_text())
        assert not fr['passed'] and fr['mode']=='revision300-v-corner-probe'
        failure=failed/'revision300-v-corner-probe.json';actual=failed/'corner-native-drc.rpt'
        assert file_sha(failure)==fr['outputs'][failure.name]
        assert file_sha(actual)==fr['outputs'][actual.name]
        fd=json.loads(failure.read_text());assert not fd['passed']and fd['source_odb_sha256']==file_sha(original)
        added=violations(actual.read_text())-violations(native.read_text())
        assert sum(added.values())==fd['added_marker_count']==22
        affected={name.replace('\\','')for block in added for name in re.findall(r'net:(\S+)',block)}
        filtered=[r['index']for r in chosen if r['net'].replace('\\','')in affected]
        chosen=[r for r in chosen if r['net'].replace('\\','')not in affected]
        assert len(filtered)==20 and len(chosen)==232
        filter_provenance=dict(failed_receipt_sha256=file_sha(failed/'receipt.json'),
                               actual_failed_native_drc_sha256=file_sha(actual),
                               actual_new_marker_count=sum(added.values()),affected_net_names=sorted(affected))
    (out/'candidate-rectangles.json').write_text(json.dumps(dict(chosen=chosen,skipped=skipped,filtered=filtered,filter_provenance=filter_provenance),indent=2)+'\n')
    groups=defaultdict(list)
    for row in chosen:groups[row['net'].replace('\\','')].append(row)
    helper=previous/'selected-geometry.tcl';assert file_sha(helper)==receipt['outputs'][helper.name]
    script='set_thread_count 16\nread_db {'+str(original)+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
    script+='set exact [dict create]\nforeach net [$block getNets] {\nset plain [string map [list [format %c 92] {}] [$net getName]]\ndict lappend exact $plain $net\n}\n'
    for name,rows in sorted(groups.items()):
        script+='set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nif {[llength $matches] != 1} {error "Ambiguous target net"}\nset net [lindex $matches 0]\n'
        script+='set enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_append $enc [$net getWire]\n'
        for row in rows:
            x0,y0,x1,y1=row['bbox_dbu']
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+row['layer']+'] ROUTED\n'
            script+='odb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db corner-candidate.odb\nwrite_def corner-candidate.def\n'
    script+='drt::check_drc_cmd corner-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'corner-probe.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'corner-probe.tcl'],'corner-probe.log')
    assert file_sha(original)==d['input_odb_sha256']
    before,routes0,n0=def_content(original_def);after,routes1,n1=def_content(out/'corner-candidate.def')
    expected=Counter((r['net'].replace('\\',''),r['layer'],*r['bbox_dbu'])for r in chosen)
    exact=after==before+expected and routes0==routes1 and n0==n1
    old=violations(native.read_text());new=violations((out/'corner-native-drc.rpt').read_text())
    added=new-old;removed=old-new
    result=dict(passed=exact and not added and sum(new.values())<sum(old.values()),
                diagnostic_only=True,physical_qualified=False,original_unchanged=True,
                source_odb_sha256=file_sha(original),source_native_drc_sha256=file_sha(native),
                localization_receipt_sha256=file_sha(previous/'receipt.json'),
                original_def_receipt_sha256=file_sha(prior/'receipt.json'),
                selected_corners=len(chosen),skipped_marker_indices=skipped,
                filtered_marker_indices=filtered,filter_provenance=filter_provenance,
                normal_net_counts=[n0,n1],exact_expected_rectangles_and_nonrect_net_routes=exact,
                original_drc_count=sum(old.values()),candidate_drc_count=sum(new.values()),
                added_marker_count=sum(added.values()),removed_marker_count=sum(removed.values()),
                estimated_added_area_um2=sum(r['estimated_added_area_dbu2']for r in chosen)/4000000,
                scope='One bounded physical corner fill on a failed-source copy. Max rectangle extent1um. Candidate is rejected on any added native marker or changed nonRECT route/header. Partial diagnostic improvement is not zero-DRC/final acceptance. Complete final RCX/STA/electrical, connectivity, full unmodified GDS, final function/LEC, files and geometry remain required.')
    (out/'revision300-v-corner-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Corner diagnostic rejected; keep actual source/candidate evidence'
