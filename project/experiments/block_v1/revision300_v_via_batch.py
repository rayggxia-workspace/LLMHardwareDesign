"""Bounded same-net via-pair replacements on the failed523 copy only."""
from collections import Counter,defaultdict
import hashlib,json,re
from pathlib import Path


def name_of(record):
    return record.lstrip().split()[1].replace('\\','')


def token_hash(record):
    return hashlib.sha256(re.sub(r'\s+',' ',record).strip().encode()).hexdigest()


def contains(path,layer,a,b):
    if path['layer']!=layer or path['via']or len(path['points'])!=2:return False
    u,v=[tuple(p[:2])for p in path['points']]
    return ((u[1]==v[1]==a[1]==b[1]and min(u[0],v[0])<=min(a[0],b[0])and max(u[0],v[0])>=max(a[0],b[0]))or
            (u[0]==v[0]==a[0]==b[0]and min(u[1],v[1])<=min(a[1],b[1])and max(u[1],v[1])>=max(a[1],b[1])))


def pairs(row):
    x0,y0,x1,y1=row['marker']['bbox_dbu'];rects=[r['bbox_dbu']for r in row['same_net_nearby_rectangles']if r['shape']=='wire-via']
    options=[]
    for left in rects:
        for right in rects:
            if left==right:continue
            horizontal=left[2]==x0 and right[0]==x1 and left[1]<=y0 and left[3]>=y1 and right[1]<=y0 and right[3]>=y1
            vertical=left[3]==y0 and right[1]==y1 and left[0]<=x0 and left[2]>=x1 and right[0]<=x0 and right[2]>=x1
            if not(horizontal or vertical):continue
            if any((r[0]+r[2])%2 or(r[1]+r[3])%2 for r in (left,right)):continue
            a=((left[0]+left[2])//2,(left[1]+left[3])//2);b=((right[0]+right[2])//2,(right[1]+right[3])//2)
            if (a[0]==b[0]or a[1]==b[1])and 0<abs(a[0]-b[0])+abs(a[1]-b[1])<=2000:
                options.append((a,b))
    return sorted(set(options))


def probe(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import records,parse
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    assert cpus==16
    base=out.parents[2];prior=base/'block-v1-20261030-557/tasks/revision300-v-spacing-localize'
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']
    report=prior/'revision300-v-physical-localization.json';assert file_sha(report)==receipt['outputs'][report.name]
    d=json.loads(report.read_text());odb=Path(d['input_odb']);assert file_sha(odb)==d['input_odb_sha256']
    controls=[]
    for number,mode in [('571','revision300-v-via-bridge'),('573','revision300-v-via-bridge-m3')]:
        p=base/('block-v1-20261030-'+number)/'tasks'/mode;r=json.loads((p/'receipt.json').read_text());assert r['passed']
        f=p/'revision300-v-via-bridge.json';assert file_sha(f)==r['outputs'][f.name]
        check=json.loads(f.read_text());assert check['passed']and check['added_markers']==0 and check['native_candidate_count']==444
        assert check['input_odb_sha256']==d['input_odb_sha256']
        controls.append(dict(path=str(p/'receipt.json'),sha256=file_sha(p/'receipt.json')))
    previous=base/'block-v1-20261030-562/tasks/revision300-v-marker-readback';pr=json.loads((previous/'receipt.json').read_text());assert pr['passed']
    source=previous/'original.def';source_sha=file_sha(source);assert source_sha==pr['outputs'][source.name]
    wanted=defaultdict(list)
    for index,row in enumerate(d['markers']):
        if row['marker']['layer']in('metal1','metal3'):
            wanted[row['marker']['net'].replace('\\','')].append((index,row))
    targets={};others=Counter();normal0=0
    for record in records(source):
        normal0+=1;name=name_of(record)
        if name in wanted:
            assert name not in targets;targets[name]=record
        else:others[token_hash(record)]+=1
    assert set(targets)==set(wanted)
    edits={};skipped=[];patches=[];expected={}
    for name,record in targets.items():
        header,paths=parse(record);original=list(paths)
        # No extension or explicit RECT can be silently discarded by encoding.
        assert ' RECT 'not in record and all(p[2]is None for path in paths for p in path['points'])
        for index,row in wanted[name]:
            layer=row['marker']['layer'];via_layer,via=('metal1','via1_7')if layer=='metal1'else('metal2','via2_5')
            selected=None
            for a,b in pairs(row):
                source_wires=[p for p in paths if contains(p,layer,a,b)]
                av=[p for p in paths if p['layer']==via_layer and p['via']==via and len(p['points'])==1 and tuple(p['points'][0][:2])==a]
                bv=[p for p in paths if p['layer']==via_layer and p['via']==via and len(p['points'])==1 and tuple(p['points'][0][:2])==b]
                branches=all(any(p['layer']=='metal2'and not p['via']and point in[tuple(t[:2])for t in p['points']]for p in paths)for point in(a,b))
                if len(source_wires)==1 and len(av)==1 and len(bv)==1 and branches:
                    selected=(a,b,av[0],bv[0],source_wires[0]);break
            if selected is None:skipped.append(index);continue
            a,b,remove,keep,wire=selected;addition=dict(layer='metal2',points=[(*a,None),(*b,None)],via=None)
            before=Counter(map(path_key,paths));paths=[p for p in paths if p is not remove]+[addition]
            after=Counter(map(path_key,paths));assert before-after==Counter([path_key(remove)])and after-before==Counter([path_key(addition)])
            assert keep in paths and wire in paths
            patches.append(dict(index=index,net=name,source_layer=layer,removed_via=remove,retained_via=keep,preserved_source_wire=wire,added_m2_wire=addition))
        if Counter(map(path_key,paths))!=Counter(map(path_key,original)):
            edits[name]=paths;expected[name]=(header,Counter(map(path_key,paths)))
    assert len(patches)>1 and any(p['index']==249 for p in patches)
    # Nets whose markers were ineligible are also required to remain exact.
    for name in set(targets)-set(edits):others[token_hash(targets[name])]+=1
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\nset wanted_names [dict create]\n'
    for name in edits:script+='dict set wanted_names [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]] 1\n'
    script+='set selected [dict create]\nforeach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]]; if {[dict exists $wanted_names $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}\n'
    script+='if {[dict size $selected] != %d} {error "Missing target"}\n'%len(edits)
    for name,paths in edits.items():
        script+='set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for p in paths:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+p['layer']+'] ROUTED\n'
            for x,y,_ in p['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if p['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+p['via']+']\n'
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db batch-candidate.odb\nwrite_def batch-candidate.def\ndrt::check_drc_cmd batch-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'batch-probe.tcl').write_text(script);(out/'expected-route-edits.json').write_text(json.dumps(dict(patches=patches,skipped_marker_indices=skipped),indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'batch-probe.tcl'],'batch-probe.log')
    actual_others=Counter();found=set();normal1=0;exact=True
    for record in records(out/'batch-candidate.def'):
        normal1+=1;name=name_of(record)
        if name in edits:
            assert name not in found;found.add(name);header,paths=parse(record);old_header,required=expected[name]
            exact=exact and Counter(map(path_key,paths))==required and re.sub(r'\s+',' ',header).strip()==re.sub(r'\s+',' ',old_header).strip()
        else:actual_others[token_hash(record)]+=1
    exact=exact and normal0==normal1 and actual_others==others and found==set(edits)
    native=prior/'native-whole-drc.rpt';assert file_sha(native)==receipt['outputs'][native.name]
    old=violations(native.read_text());new=violations((out/'batch-native-drc.rpt').read_text())
    original_unchanged=file_sha(odb)==d['input_odb_sha256']and file_sha(source)==source_sha
    result=dict(passed=exact and original_unchanged and not(new-old)and sum(new.values())<sum(old.values()),diagnostic_only=True,physical_qualified=False,
        input_odb_sha256=d['input_odb_sha256'],original_def_sha256=source_sha,localization_receipt_sha256=file_sha(prior/'receipt.json'),original_def_receipt_sha256=file_sha(previous/'receipt.json'),single_case_controls=controls,
        original_unchanged=original_unchanged,selected_marker_count=sum(map(len,wanted.values())),patch_count=len(patches),changed_nets=len(edits),skipped_marker_indices=skipped,
        normal_net_counts=[normal0,normal1],all_other_normal_net_tokens_sha256_identical=actual_others==others,all_target_headers_and_exact_path_multisets=exact,
        native_original_count=sum(old.values()),native_candidate_count=sum(new.values()),added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
        scope='Batch of bounded observed same-net via-pair edge replacements on old523 only. Every source wire and second via is kept; each missing via has an explicit alternate M2/source-wire path. Token-normalized original NETS/header and exact path multiset checks are not a geometric terminal-connectivity, RCX/STA, full GDS/function/LEC or delivery qualification. No combination with separate232 corner fills or transfer to current588.')
    (out/'revision300-v-via-batch.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Batch diagnostic rejected; preserve evidence and original source'
