"""Audited Boolean view of physically present, input-only protection cells.

The default removes only ANTENNA_X1. The separately controlled C8 path then
encodes true constant-cell functions. Full physical netlists, Liberty loads,
placement, PG, routing and gate simulation retain every cell.
"""
import copy
import json
import re


def project(data,liberty):
    from native_cell_gate import group,attribute
    from structural_view import digest
    body=group(liberty,'cell','ANTENNA_X1')
    names=re.findall(r'\bpin\s*\(\s*"?([A-Za-z_][A-Za-z_0-9]*)"?\s*\)',body)
    assert names==['A'],'Protection master has unexpected signal pins'
    pin=group(body,'pin','A')
    assert attribute(pin,'direction')=='input'
    assert not re.search(r'\b(?:ff|ff_bank|latch|latch_bank|statetable)\s*\(',body)
    assert attribute(pin,'function',False)is None
    assert float(attribute(pin,'capacitance'))>0
    result=copy.deepcopy(data);removed={}
    for name,module in result['modules'].items():
        if module.get('attributes',{}).get('blackbox'):continue
        cells=module.get('cells',{})
        for cell,entry in list(cells.items()):
            if entry['type']!='ANTENNA_X1':continue
            assert entry.get('parameters',{})=={}
            assert entry['port_directions']=={'A':'input'}
            assert set(entry['connections'])=={'A'} and len(entry['connections']['A'])==1
            removed[name+'/'+cell]=entry
            del cells[cell]
    # The inverse must reconstruct the entire original parsed graph, including
    # all aliases, constants, ports, sequential pins, metadata and other cells.
    inverse=copy.deepcopy(result)
    for key,entry in removed.items():
        module,cell=key.split('/',1)
        assert cell not in inverse['modules'][module]['cells']
        inverse['modules'][module]['cells'][cell]=entry
    assert inverse==data
    return result,dict(schema='block-v1-input-only-logic-projection/1',passed=True,
        removed_instances=removed,removed_count=len(removed),original_graph_sha256=digest(data),
        projected_graph_sha256=digest(result),exact_inverse_reconstruction=True,
        allowed_master='ANTENNA_X1',liberty_signal_pins={'A':'input'},
        scope='Input-only, stateless, no-function ANTENNA_X1 Boolean removal only; physical and simulation views retain cells and real loads')


def used_model_audit(data,liberty):
    """Reject instantiated Liberty models that Kepler reports unsupported."""
    from native_cell_gate import group
    used={entry['type'] for module in data['modules'].values()
          if not module.get('attributes',{}).get('blackbox')
          for entry in module.get('cells',{}).values()}
    assert used,'No actual instantiated library models'
    for master in sorted(used):
        body=group(liberty,'cell',master)
        assert not re.search(r'\b(?:statetable|state_function)\s*[:(]',body),('Unsupported instantiated library model',master)
    return dict(passed=True,instantiated_masters=sorted(used),
        unsupported_instantiated_statetable_or_state_function=[],
        scope='Actual instantiated masters contain none of the statetable/state_function constructs warned unsupported by the native frontend; this is not a general frontend completeness proof')


def export(root,out,run,netlist,library,top,label,constant_functions=False):
    from io_slots import file_sha
    from structural_view import compare
    original=out/(label+'-physical.json')
    script='read_liberty -lib '+str(library)+'\nread_verilog '+str(netlist)+'\nhierarchy -check -top '+top+'\nwrite_json '+str(original)+'\n'
    ys=out/(label+'-parse.ys');ys.write_text(script)
    run(['yosys','-s',str(ys)],label+'-parse.log')
    data=json.loads(original.read_text())
    liberty=library.read_text()
    projected,proof=project(data,liberty)
    if constant_functions:
        from native_tie_projection import project as project_constants
        proof['used_model_audit']=used_model_audit(data,liberty)
        projected,constants=project_constants(projected,liberty)
        assert constants['original_graph_sha256']==proof['projected_graph_sha256']
        proof['constant_functions']=constants
        proof['final_graph_sha256']=constants['projected_graph_sha256']
    graph=out/(label+'-logic.json');graph.write_text(json.dumps(projected)+'\n')
    target=out/(label+'-logic.v');reparsed=out/(label+'-reparsed.json')
    script='read_json '+str(graph)+'\nwrite_verilog -norename -noattr -noexpr '+str(target)+'\n'
    script+='design -reset\nread_liberty -lib '+str(library)+'\nread_verilog '+str(target)+'\nhierarchy -check -top '+top+'\nwrite_json '+str(reparsed)+'\n'
    ys=out/(label+'-emit.ys');ys.write_text(script)
    run(['yosys','-s',str(ys)],label+'-emit.log')
    proof['emitted_structural_proof']=compare(projected,json.loads(reparsed.read_text()))
    proof.update(full_netlist_sha256=file_sha(netlist),logic_netlist_sha256=file_sha(target),liberty_sha256=file_sha(library))
    (out/(label+'-logic-proof.json')).write_text(json.dumps(proof,indent=2)+'\n')
    return target,proof
