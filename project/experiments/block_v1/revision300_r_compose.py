"""Compose actual checked R copies with failure attribution and fresh native DRC."""
from collections import Counter
import hashlib,json,re


def compose(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    from revision300_v_gds_repair import nonnet
    assert cpus==16
    base=out.parents[2];corner=base/'block-v1-20261101-866/tasks/revision300-r-corner-compose'
    cr=json.loads((corner/'receipt.json').read_text());assert cr['passed']and cr['mode']==corner.name
    for n in ('revision300-r-clearance-corners.json','selected-corners.json','corner-candidate.odb','corner-candidate.def','corner-native-drc.rpt'):
        assert file_sha(corner/n)==cr['outputs'][n]
    cd=json.loads((corner/'revision300-r-clearance-corners.json').read_text())
    assert cd['passed']and cd['combined']and cd['candidate_native_count']==265 and cd['added_markers']==0
    ancestral='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b'
    assert cd['source_receipt_sha256']==ancestral
    source=base/'block-v1-20261101-828/tasks/revision300-final-source-r';assert file_sha(source/'receipt.json')==ancestral
    frozen=source/'flow/results/nangate45/bv1_block_v1_r/base'
    for n,h in cd['source_inputs_sha256'].items():assert file_sha(frozen/n)==h
    neigh=base/'block-v1-20261101-851/tasks/revision300-r-current-neighborhood'
    nr=json.loads((neigh/'receipt.json').read_text());assert nr['passed']
    for n in ('native-whole-drc.rpt','via-footprints.tsv'):assert file_sha(neigh/n)==nr['outputs'][n]
    old584=violations((neigh/'native-whole-drc.rpt').read_text());assert sum(old584.values())==584
    foot={}
    for line in(neigh/'via-footprints.tsv').read_text().splitlines():
        name,l,*box=line.split('\t');foot.setdefault(name,[]).append((l,list(map(int,box))))
    selected=[];evidence=[];excluded=set()
    families=[('866','revision300-r-vias-',None,53),('870','revision300-r-alternate-vias-','r-alternate-plan-869.json',64),('875','revision300-r-stack-vias-','r-stack-plan-873.json',94)]
    for number,prefix,planfile,count in families:
        planpath=root/'project/experiments/block_v1'/planfile if planfile else base/'block-v1-20261101-857/tasks/revision300-r-topology/via-candidate-plan.json'
        plan=json.loads(planpath.read_text());assert len(plan['selected'])==count
        covered=[];family=[];bad=set()
        for s in range(6):
            folder=base/('block-v1-20261101-'+number)/'tasks'/(prefix+str(s))
            rr=json.loads((folder/'receipt.json').read_text());assert rr['mode']==folder.name
            for n in ('revision300-r-vias.json','selected-vias.json','via-native-drc.rpt'):assert file_sha(folder/n)==rr['outputs'][n]
            d=json.loads((folder/'revision300-r-vias.json').read_text())
            assert d['passed']==rr['passed']and d['shard']==s and d['source_receipt_sha256']==ancestral and d['plan_sha256']==file_sha(planpath)
            assert d['exact_normal_net_header_path_rect_and_nonnet_delta']and d['original_inputs_unchanged']and not d['combined']
            own=[p for p in plan['selected']if int(hashlib.sha256(p['net'].encode()).hexdigest(),16)%6==s]
            assert json.loads((folder/'selected-vias.json').read_text())==own
            new=violations((folder/'via-native-drc.rpt').read_text());added=new-old584
            assert sum(added.values())==d['added_markers']and bool(added)==(not rr['passed'])
            participants=set()
            for marker in added:
                implicated=set(re.findall(r'net:([^ ]+)',marker))&{p['net']for p in own}
                assert implicated,'Unattributable new marker; refuse blind filtering'
                participants.update(implicated)
            bad.update(participants);covered.extend(p['index']for p in own)
            family.append(dict(task=str(folder),receipt_sha256=file_sha(folder/'receipt.json'),passed=rr['passed'],added=list(added.elements()),excluded_nets=sorted(participants)))
        assert sorted(covered)==sorted(p['index']for p in plan['selected'])
        for p in plan['selected']:
            if p['net']in bad:continue
            if planfile:p=dict(p,family=number)
            else:p=dict(p,family=number,added_bridge=p['added_m2_wire'],moved_via=None,retain_pad_layer='metal2')
            selected.append(p)
        excluded.update(bad);evidence.extend(family)
    assert len({p['net']for p in selected})==len(selected)>100
    cornernets={p['net'].replace('\\','')for p in json.loads((corner/'selected-corners.json').read_text())}
    assert not cornernets&{p['net']for p in selected},'Changed corner net needs fresh topology before via reconstruction'
    wanted={p['net']:p for p in selected};original={};others=Counter();n0=0
    for record in records(corner/'corner-candidate.def'):
        n0+=1;name=name_of(record)
        if name not in wanted:others[token_hash(record)]+=1;continue
        assert name not in original;header,paths,rects=decode(record)
        assert all(v is None for p in paths for x,y,v in p['points'])
        original[name]=(header,paths,rects)
    assert set(original)==set(wanted)and n0==1013372
    script='set_thread_count 16\nread_db {'+str(corner/'corner-candidate.odb')+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\nif {[$tech getManufacturingGrid]!=10} {error {Frozen grid mismatch}}\nset selected [dict create]\n'
    script+='foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];dict lappend selected $name $net}\n'
    expected={}
    for name,p in wanted.items():
        header,paths,rects=original[name];before=Counter(map(path_key,paths));remove=path_key(p['removed_via']);assert before[remove]==1
        if p['retained_via']:assert before[path_key(p['retained_via'])]==1
        adds=[p['added_bridge']]+([p['moved_via']]if p['moved_via']else[])
        assert all(before[path_key(v)]==0 for v in adds)
        after=list(paths);after.pop(next(i for i,v in enumerate(after)if path_key(v)==remove));after.extend(adds)
        required=before.copy();required.subtract([remove]);required+=Counter(map(path_key,adds))
        assert Counter(map(path_key,after))==required and all(required[path_key(v)]==before[path_key(v)]for v in p['preserved_source_wires'])
        # Preserve the removed via's old adjacent metal for every family,
        # including base866, so off-center lower-layer contacts are not lost.
        rects=rects.copy();x,y=p['a'];pads=[]
        for l,(x0,y0,x1,y1)in foot[p['removed_via']['via']]:
            if l==p['retain_pad_layer']:
                rects[(l,x+x0,y+y0,x+x1,y+y1)]+=1;pads.append((l,x+x0,y+y0,x+x1,y+y1))
        assert len(pads)==1
        expected[name]=(header,required,rects)
        script+='set matches [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nif {[llength $matches]!=1} {error {Ambiguous target}}\nset net [lindex $matches 0]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for v in after:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+v['layer']+'] ROUTED\n'
            for x,y,_ in v['points']:
                assert x%10==y%10==0;script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if v['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+v['via']+']\n'
        for (l,x0,y0,x1,y1),count in rects.items():
            assert all(v%10==0 for v in (x0,y0,x1,y1))
            for _ in range(count):script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+l+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db composed-candidate.odb\nwrite_def composed-candidate.def\ndrt::check_drc_cmd composed-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'compose.tcl').write_text(script);(out/'selected-vias.json').write_text(json.dumps(selected,indent=2)+'\n');(out/'independent-failures.json').write_text(json.dumps(evidence,indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'compose.tcl'],'compose.log')
    actual=Counter();found=set();exact=True;n1=0
    for record in records(out/'composed-candidate.def'):
        n1+=1;name=name_of(record)
        if name not in expected:actual[token_hash(record)]+=1;continue
        assert name not in found;found.add(name);header,paths,rects=decode(record);h,required,rr=expected[name]
        exact=exact and re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',h)and Counter(map(path_key,paths))==required and rects==rr
    exact=exact and actual==others and found==set(expected)and n0==n1 and nonnet(corner/'corner-candidate.def')==nonnet(out/'composed-candidate.def')
    old=violations((corner/'corner-native-drc.rpt').read_text());new=violations((out/'composed-native-drc.rpt').read_text());assert sum(old.values())==265
    unchanged=all(file_sha(corner/n)==cr['outputs'][n]for n in ('corner-candidate.odb','corner-candidate.def','corner-native-drc.rpt'))and all(file_sha(frozen/n)==h for n,h in cd['source_inputs_sha256'].items())
    result=dict(passed=exact and unchanged and not(new-old)and bool(old-new),combined=True,physical_qualified=False,ancestral_source_receipt_sha256=ancestral,
                corner_source_receipt_sha256=file_sha(corner/'receipt.json'),corner_source_files_sha256={n:cr['outputs'][n]for n in ('corner-candidate.odb','corner-candidate.def','corner-native-drc.rpt')},
                independent_receipts=evidence,excluded_nets=sorted(excluded),selected_nets=len(selected),exact_normal_net_header_path_rect_and_nonnet_delta=exact,original_inputs_unchanged=unchanged,normal_net_counts=[n0,n1],
                original_native_count=265,candidate_native_count=sum(new.values()),added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='Real composition on actual866314-corner source, not independent count sum. Source-bound866/870/875 actual shards and failed-net exclusions; all original wires and adjacent via pads retained including base866. Whole native check and complete DEF delta mandatory; NS variants not included. Remaining DRC and fresh fullsignal/RCX/STA/fullGDS/function/LEC/delivery/interfaces still mandatory.')
    (out/'revision300-r-composed-vias.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed combined result for new geometry attribution'
