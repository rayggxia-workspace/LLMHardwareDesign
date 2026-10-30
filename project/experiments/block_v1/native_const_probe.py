"""Qualify real tie-cell import against source constants, never waive floats."""
import copy
import json
from pathlib import Path


def restore(before,after,liberty):
    from native_cell_gate import group,attribute
    from structural_view import compare
    result=copy.deepcopy(after);added={}
    for name,module in result['modules'].items():
        if module.get('attributes',{}).get('blackbox'):continue
        original=before['modules'][name]['cells'];constants={}
        for cell,entry in list(module['cells'].items()):
            if cell in original:continue
            master=entry['type'];assert master in ('LOGIC0_X1','LOGIC1_X1')
            value='0'if master=='LOGIC0_X1'else'1'
            body=group(liberty,'cell',master);pin=group(body,'pin','Z')
            assert attribute(pin,'direction')=='output' and attribute(pin,'function')==value
            assert entry['port_directions']=={'Z':'output'}and entry.get('parameters',{})=={}
            assert set(entry['connections'])=={'Z'}and len(entry['connections']['Z'])==1
            bit=entry['connections']['Z'][0];assert type(bit)is int and bit not in constants
            constants[bit]=value;added[cell]=dict(master=master,output_bit=bit,value=value)
            del module['cells'][cell]
        for category in ('ports','netnames'):
            for entry in module[category].values():entry['bits']=[constants.get(b,b)for b in entry['bits']]
        for entry in module['cells'].values():
            for pin,bits in entry['connections'].items():entry['connections'][pin]=[constants.get(b,b)for b in bits]
    assert added
    proof=compare(before,result)
    return result,dict(passed=True,added_ties=added,exact_literal_restoration=proof)


def verify(root,out,cpus,run):
    from io_slots import file_sha
    from structural_view import compare
    assert cpus>=8
    base=out.parents[2]
    source=base/'block-v1-20261027-080/tasks/native-run-shared109-c'
    bound=json.loads((source/'receipt.json').read_text());assert bound['passed']is True
    results=source/'flow/results/nangate45/bv1_shared109_C/base'
    netlist=results/'1_2_yosys.v';assert file_sha(netlist)==bound['outputs'][str(netlist.relative_to(source))]
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
    ys='read_liberty -lib '+str(lib)+'\nread_verilog '+str(netlist)+'\nhierarchy -check -top shared109\nflatten\n'
    ys+='write_json literal.json\nhilomap -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\n'
    ys+='write_json tied.json\nwrite_verilog -norename -noattr -noexpr tied.v\n'
    (out/'tie-map.ys').write_text(ys);run(['yosys','-s','tie-map.ys'],'tie-map.log')
    before=json.loads((out/'literal.json').read_text());after=json.loads((out/'tied.json').read_text())
    target={name:before['modules']['shared109']['ports'][name]['bits'][bit]for name,bit in [('adebug',6),('mdebug',4)]}
    assert target==dict(adebug='0',mdebug='0'),target
    restored,proof=restore(before,after,lib.read_text())
    # Actual source-bit mutation after restoration must still be rejected.
    restored['modules']['shared109']['ports']['mdebug']['bits'][4]='1'
    try:compare(before,restored)
    except AssertionError:proof['wrong_constant_negative_rejected']=True
    else:raise AssertionError('Changed constant output accepted')
    inputs={str(netlist):file_sha(netlist),str(lib):file_sha(lib)}
    reports={}
    candidates=[('c8-before',results/'1_synth.odb',source,bound),('c8-after',results/'6_final.odb',source,bound)]
    t6=base/'block-v1-20261027-111/tasks/native-diode-run-transaction6k-a'
    tr=json.loads((t6/'receipt.json').read_text());assert tr['passed']is True
    candidates.append(('t6k-after',t6/'flow/results/nangate45/bv1_transaction6k_A/base/6_final.odb',t6,tr))
    for label,path,owner,receipt in candidates:
        inputs[str(path)]=file_sha(path);assert inputs[str(path)]==receipt['outputs'][str(path.relative_to(owner))]
        text='read_liberty '+str(lib)+'\nread_db {'+str(path)+'}\n'
        text+='set ::env(BV1_UNDRIVEN_REPORT) {'+str(out/(label+'.tsv'))+'}\n'
        text+='source {'+str(root/'project/experiments/block_v1/native_undriven.tcl')+'}\n'
        (out/(label+'.tcl')).write_text(text);run(['openroad','-no_init','-exit',label+'.tcl'],label+'.log')
        reports[label]=(out/(label+'.tsv')).read_text().splitlines()
    text='read_lef '+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'\n'
    text+='read_lef '+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'\nread_liberty '+str(lib)+'\n'
    text+='read_verilog tied.v\nlink_design shared109\n'
    text+='set ::env(BV1_UNDRIVEN_REPORT) {'+str(out/'tied-import.tsv')+'}\n'
    text+='source {'+str(root/'project/experiments/block_v1/native_undriven.tcl')+'}\n'
    (out/'tied-import.tcl').write_text(text);run(['openroad','-no_init','-exit','tied-import.tcl'],'tied-import.log')
    reports['tied-import']=(out/'tied-import.tsv').read_text().splitlines()
    assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    record=dict(schema='block-v1-source-constant-import-control/1',passed=True,input_sha256=inputs,
        original_target_literals=target,tie_mapping_proof=proof,undriven_reports=reports,
        tied_verilog_sha256=file_sha(out/'tied.v'),physical_repair_qualified=False,
        scope='Exact original source constants, real Liberty tie-cell restoration, changed-constant rejection and actual used-net driver inventories; no repaired full block or relaxed LEC')
    (out/'native-constant-control.json').write_text(json.dumps(record,indent=2)+'\n')
