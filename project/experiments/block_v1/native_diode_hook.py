"""Run the actual prefabrication hook and pin-access options on sealed CTS."""
import json


def verify(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus>=8
    source=out.parents[2]/'block-v1-20261027-080/tasks/native-run-transaction6k-a'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    results=source/'flow/results/nangate45/bv1_transaction6k_A/base'
    inputs={}
    for name in ['4_cts.odb','4_cts.sdc']:
        path=results/name;inputs[str(path)]=file_sha(path)
        assert inputs[str(path)]==receipt['outputs'][str(path.relative_to(source))]
    script='read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib\n'
    script+='read_db {'+str(results/'4_cts.odb')+'}\nread_sdc {'+str(results/'4_cts.sdc')+'}\n'
    script+='set_thread_count '+str(cpus)+'\nset ::env(RESULTS_DIR) {'+str(out)+'}\n'
    script+='proc detailed_placement_helper {} {detailed_placement}\n'
    script+='source {'+str(root/'project/experiments/block_v1/native_input_diodes.tcl')+'}\n'
    script+='set_routing_layers -signal metal1-metal10\npin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10\n'
    script+='write_db protected-cts.odb\nwrite_verilog protected-cts.v\n'
    (out/'probe.tcl').write_text(script)
    run(['openroad','-no_init','-exit',str(out/'probe.tcl')],'hook-probe.log')
    rows=[line.split('\t')for line in(out/'bv1-input-diodes.tsv').read_text().splitlines()]
    placed=[line.split('\t')for line in(out/'bv1-input-diodes-placed.tsv').read_text().splitlines()]
    assert rows and len(rows)==len(placed)
    expected={r[0]:r[2]for r in rows};actual={r[0]:r[1]for r in placed}
    assert expected==actual and all(r[-1]in ('PLACED','FIRM','LOCKED','COVER')for r in placed)
    assert all(file_sha(__import__('pathlib').Path(p))==digest for p,digest in inputs.items())
    record=dict(schema='block-v1-native-diode-hook/1',passed=True,input_sha256=inputs,
        diode_count=len(rows),added_master_area_um2=len(rows)*.266,added_input_cap_ff=len(rows)*.023429,
        root_connections=expected,placed_connections=actual,pin_access_arguments=['-via_in_pin_bottom_layer','metal10','-via_in_pin_top_layer','metal10'],
        source_receipt_sha256=file_sha(source/'receipt.json'),qualified_block_repair=False,
        scope='Actual OpenDB instantiation/connection, legal placement and M10 via-in-pin access on sealed CTS; no complete routing, RCX, STA, full DRC, PG or function acceptance')
    (out/'native-diode-hook.json').write_text(json.dumps(record,indent=2)+'\n')
