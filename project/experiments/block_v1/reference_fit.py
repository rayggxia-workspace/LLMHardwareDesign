"""Fit actual twelve-layer calibration rows through the installed OpenRCX.

The SPEF contains measured master rows and DC resistor patterns only. Ignored
context/edge rows are deliberately absent, not represented as measured zeros.
Raw stochastic data remains immutable; reciprocal estimates are averaged and
insignificant negative physical couplings are projected to zero explicitly.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit(root,out,run):
    base=out.parents[2]
    bindings=[];seen=set();rows={};manifest_path=None;manifest_sha=None
    for index in range(6):
        folder=base/('block-v1-20261027-016/tasks/reference-receive-%d'%index)
        receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed'] is True
        path=folder/'reference-shard.json';assert sha(path)==receipt['outputs'][path.name]
        record=json.loads(path.read_text());assert record['shard']==index and record['receive_only']is True
        if manifest_path is None:
            manifest_path=Path(record['manifest']);manifest_sha=record['manifest_sha256']
        assert record['manifest']==str(manifest_path)and record['manifest_sha256']==manifest_sha
        assert sha(manifest_path)==manifest_sha
        ids={c['id']for c in record['cases']};assert not(ids&seen);seen|=ids
        for command in record['commands']:
            path=Path(command['rows_file']);assert sha(path)==command['rows_sha256']
            binding=dict(path=str(path),sha256=sha(path));bindings.append(binding)
            for line in path.open():
                row=json.loads(line)
                if 'entries'not in row:
                    assert row=={'status':'PASS','mode':'scenelist3d'};continue
                assert int(row['case'])in ids and row['master']not in rows
                rows[row['master']]=row
    manifest=json.loads(manifest_path.read_text())
    assert manifest['schema']=='block-v1-reference-patterns/2'
    assert seen=={c['id']for c in manifest['cases']if not c['name'].startswith('R6_')}
    expected={master for c in manifest['cases']if c['id']in seen for master in c['masters']}
    assert set(rows)==expected
    nets={n['name']:n for case in manifest['cases']for n in case['nets']}
    assert len(nets)==manifest['net_count']
    dc={n['name']for c in manifest['cases']if c['name'].startswith('R6_')for n in c['nets']if not n['context']and n['index']==3}
    assert not(dc&expected)
    matrix={name:{entry['net']:entry for entry in row['entries']}for name,row in rows.items()}
    couplings={};ground={};adjacency=defaultdict(list);projected=[]
    for name,entries in matrix.items():
        ground[name]=max(0,-entries['ground']['cap'])
        if entries['ground']['cap']>0:projected.append(dict(a=name,b='ground',raw_ff=entries['ground']['cap']))
        for other,entry in entries.items():
            if other in (name,'ground'):continue
            pair=tuple(sorted((name,other)))
            if pair in couplings:continue
            value=entry['cap']
            if other in matrix:value=(value+matrix[other][name]['cap'])/2
            cap=max(0,-value);couplings[pair]=cap
            if value>0:projected.append(dict(a=pair[0],b=pair[1],raw_ff=value))
            if cap:
                if pair[0]in matrix:adjacency[pair[0]].append((pair[1],cap))
                if pair[1]in matrix:adjacency[pair[1]].append((pair[0],cap))
    # Mapping includes actual external terminals so coupling targets need no
    # fabricated D_NET for unmeasured context/self-capacitance rows.
    names=sorted(nets);ports=[p for name in names for p in nets[name]['ports']]
    assert len(set(names+ports))==len(names)+len(ports)
    identifiers={name:i+1 for i,name in enumerate(names+ports)}
    selected=sorted(expected|dc)
    totals={name:ground[name]+sum(cap for other,cap in adjacency[name])for name in expected}
    def port(name,end=0):return '*%d'%identifiers[nets[name]['ports'][end]]
    spef=out/'reference.spef'
    with spef.open('w')as stream:
        stream.write('*SPEF "IEEE 1481-1998"\n*DESIGN "bench"\n*DATE "2026-10-27"\n'
                     '*VENDOR "LLMHardwareDesign"\n*PROGRAM "block-v1-reference"\n*VERSION "1"\n'
                     '*DESIGN_FLOW "PARTIAL_CALIBRATION_MASTER_ROWS"\n*DIVIDER /\n*DELIMITER :\n'
                     '*BUS_DELIMITER [ ]\n*T_UNIT 1 NS\n*C_UNIT 1 FF\n*R_UNIT 1 OHM\n*L_UNIT 1 UH\n\n*NAME_MAP\n')
        for name,identifier in identifiers.items():stream.write('*%d %s\n'%(identifier,name))
        stream.write('\n*PORTS\n')
        for name in names:
            stream.write(port(name)+' I\n'+port(name,1)+' O\n')
        for name in selected:
            stream.write('\n*D_NET *%d %.17g\n*CONN\n*P %s I\n*P %s O\n*CAP\n'%
                         (identifiers[name],totals.get(name,0),port(name),port(name,1)))
            count=0
            if name in expected:
                count+=1;stream.write('%d %s %.17g\n'%(count,port(name),ground[name]))
                for other,cap in sorted(adjacency[name]):
                    # One physical coupling appears once globally. The reader
                    # must charge both nets exactly once; audited below.
                    if other in expected and other<name:continue
                    count+=1;stream.write('%d %s %s %.17g\n'%(count,port(name),port(other),cap))
            stream.write('*RES\n1 %s %s %.17g\n*END\n'%(port(name),port(name,1),nets[name]['resistance_ohm']))
    expected_path=out/'expected-rc.tsv'
    expected_path.write_text(''.join('%s\t%.17g\t%.17g\t%.17g\n'%(name,nets[name]['resistance_ohm'],
        ground.get(name,0),sum(cap for other,cap in adjacency[name]))for name in selected))
    patterns=Path(manifest['source_folder'])
    original=json.loads((patterns/'receipt.json').read_text());assert original['passed']is True
    assert sha(patterns/'patterns.odb')==original['outputs']['patterns.odb']
    script='read_db {'+str(patterns/'patterns.odb')+'}\nbench_read_spef reference.spef\n'+r'''
set input [open expected-rc.tsv r]
set output [open received-rc.tsv w]
while {[gets $input line]>=0} {
  set name [lindex [split $line "\t"] 0]
  set net [[ord::get_db_block] findNet $name]
  if {$net eq "NULL" || $net eq ""} { error "Missing reference net $name" }
  puts $output "$name\t[$net getTotalResistance 0]\t[$net getTotalCapacitance 0 false]\t[$net getTotalCouplingCap 0]"
}
close $input
close $output
write_db received.odb
'''
    (out/'receive.tcl').write_text(script)
    run(['openroad','-no_init','-exit','receive.tcl'],'spef-readback.log')
    def table(path):
        result={}
        for line in path.read_text().splitlines():
            name,*values=line.split('\t');assert name not in result
            result[name]=list(map(float,values))
        return result
    want,got=table(expected_path),table(out/'received-rc.tsv');assert want.keys()==got.keys()
    max_errors=[0.,0.,0.]
    for name,values in want.items():
        for index,(a,b)in enumerate(zip(values,got[name])):
            error=abs(a-b)/max(1,abs(a));max_errors[index]=max(max_errors[index],error)
            assert error<2e-5,(name,index,a,b,error)
    (out/'model.tcl').write_text('read_db {'+str(patterns/'patterns.odb')+'}\n'
                               'bench_read_spef reference.spef\nwrite_rules -file research12.rules\n')
    run(['openroad','-no_init','-exit','model.tcl'],'model-fit.log')
    model=out/'research12.rules';text=model.read_text()
    assert re.search(r'(?m)^LayerCount 12\s*$',text)
    layers={int(m.group(1))for m in re.finditer(r'(?m)^Metal (\d+) OVER\s*$',text)}
    assert layers==set(range(1,13)),layers
    record=dict(schema='block-v1-reference-fit/1',manifest=str(manifest_path),manifest_sha256=manifest_sha,
                raw_rows=bindings,reference_master_rows=len(rows),dc_resistor_patterns=len(dc),coupling_pairs=len(couplings),
                positive_noise_projection=projected,reciprocity='mean of two measured entries when both masters exist',
                spef_sha256=sha(spef),model_sha256=sha(model),received_dbu_model=str(out/'received.odb'),
                readback_max_scaled_errors=dict(zip(['resistance_ohm','ground_ff','coupling_ff'],max_errors)),
                qualification='Actual twelve-layer fitted candidate; extraction and held-out validation pending')
    (out/'reference-fit.json').write_text(json.dumps(record,indent=2)+'\n')
