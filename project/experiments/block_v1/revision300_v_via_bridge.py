"""Single observed same-net via-pair bridge replacement, on a failed copy."""
from collections import Counter
import json,re
from pathlib import Path


def net_records(path,name):
    from native_escape import records
    others=Counter();selected=None;count=0
    for record in records(path):
        count+=1
        if record.lstrip().split()[1].replace('\\','')==name:
            assert selected is None;selected=record
        else:others[re.sub(r'\s+',' ',record).strip()]+=1
    assert selected is not None
    return selected,others,count


def path_key(path):
    return path['layer'],tuple(tuple(p)for p in path['points']),path['via']


def probe(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import parse
    from revision300_v_corner_probe import violations
    assert cpus==16
    base=out.parents[2];prior=base/'block-v1-20261030-557/tasks/revision300-v-spacing-localize'
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']
    report=prior/'revision300-v-physical-localization.json';assert file_sha(report)==receipt['outputs'][report.name]
    d=json.loads(report.read_text());marker=d['markers'][0]['marker']
    assert marker['layer']=='metal1'and marker['bbox_dbu']==[2325550,1598030,2325650,1598170]
    name=marker['net'].replace('\\','');odb=Path(d['input_odb'])
    assert file_sha(odb)==d['input_odb_sha256']
    previous=base/'block-v1-20261030-562/tasks/revision300-v-marker-readback'
    pr=json.loads((previous/'receipt.json').read_text());assert pr['passed']
    original_def=previous/'original.def';assert file_sha(original_def)==pr['outputs'][original_def.name]
    record,others0,n0=net_records(original_def,name);header,paths=parse(record)
    a=(2325410,1598100);b=(2325790,1598100)
    assert all(point[2]is None for p in paths for point in p['points'])
    bridge=[p for p in paths if p['layer']=='metal1'and not p['via']and {tuple(t[:2])for t in p['points']}=={a,b}]
    assert len(bridge)==1
    def via_at(point):
        found=[p for p in paths if p['layer']=='metal1'and p['via']=='via1_7'and tuple(p['points'][0][:2])==point]
        assert len(found)==1;return found[0]
    remove=via_at(a);keep=via_at(b)
    for point in (a,b):
        assert any(p['layer']=='metal2'and not p['via']and point in [tuple(t[:2])for t in p['points']]for p in paths)
    # Preserve the old M1 bridge and the second via. Every former A via
    # connection is replaced by A(M2)->B(M2)->B(M1)->A(M1). Nothing is detached.
    addition=dict(layer='metal2',points=[(*a,None),(*b,None)],via=None)
    updated=[p for p in paths if p is not remove]+[addition]
    expected=Counter(map(path_key,paths));expected.subtract([path_key(remove)]);expected+=Counter([path_key(addition)])
    assert Counter(map(path_key,updated))==expected and keep in updated and bridge[0]in updated
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\nset matches {}\n'
    script+='set wanted [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]\n'
    script+='foreach net [$block getNets] {if {[string map [list [format %c 92] {}] [$net getName]] eq $wanted} {lappend matches $net}}\nif {[llength $matches] != 1} {error "Ambiguous target"}\nset net [lindex $matches 0]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
    for p in updated:
        script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+p['layer']+'] ROUTED\n'
        for x,y,_ in p['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
        if p['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+p['via']+']\n'
    script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\nwrite_db bridge-candidate.odb\nwrite_def bridge-candidate.def\ndrt::check_drc_cmd bridge-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'bridge-probe.tcl').write_text(script)
    (out/'expected-route-edit.json').write_text(json.dumps(dict(net=name,removed_via=remove,added_wire=addition,preserved_source_bridge=bridge[0],preserved_via=keep),indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'bridge-probe.tcl'],'bridge-probe.log')
    assert file_sha(odb)==d['input_odb_sha256']
    actual,others1,n1=net_records(out/'bridge-candidate.def',name);h1,p1=parse(actual)
    exact=(Counter(map(path_key,p1))==expected and re.sub(r'\s+',' ',header).strip()==re.sub(r'\s+',' ',h1).strip()and others0==others1 and n0==n1)
    native=prior/'native-whole-drc.rpt';assert file_sha(native)==receipt['outputs'][native.name]
    old=violations(native.read_text());new=violations((out/'bridge-native-drc.rpt').read_text())
    result=dict(passed=exact and not(new-old)and sum(new.values())<sum(old.values()),
                diagnostic_only=True,physical_qualified=False,original_unchanged=True,
                input_odb_sha256=file_sha(odb),original_def_sha256=file_sha(original_def),
                localization_receipt_sha256=file_sha(prior/'receipt.json'),
                original_def_receipt_sha256=file_sha(previous/'receipt.json'),
                normal_net_counts=[n0,n1],all_other_normal_net_records_unchanged=others0==others1,
                target_exact_one_via_removed_one_m2_bridge_added=exact,
                native_original_count=sum(old.values()),native_candidate_count=sum(new.values()),
                added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='One actual observed via-pair path replacement only, keeping all old wire metal and the second via. A connected alternate same-net path replaces the removed via. Fresh full physical connectivity/RCX/STA/electrical/GDS/function/LEC and delivery remain mandatory; partial DRC improvement is not qualification.')
    (out/'revision300-v-via-bridge.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Single via-bridge diagnostic rejected; retain all evidence'
