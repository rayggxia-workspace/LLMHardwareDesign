"""Locate the exact S spacing failure across native route/fill/final stages."""
import json
from pathlib import Path


def diagnose(root,out,cpus,run,stage):
    from io_slots import file_sha
    assert cpus==16 and stage in ('route','fill','final')
    base=out.parents[2]
    failed=base/'block-v1-20261029-258/tasks/revision300-drc-s'
    fr=json.loads((failed/'receipt.json').read_text());assert not fr['passed']
    fp=failed/'five-macro-drc.json';assert file_sha(fp)==fr['outputs'][fp.name]
    failure=json.loads(fp.read_text())
    assert not failure['passed'] and failure['full_deck']['total_items']==0
    assert failure['native_report'].count('violation type:')==1
    assert 'words\\[674\\][3]' in failure['native_report']
    native=base/'block-v1-20261028-246/tasks/revision300-route-s'
    receipt=json.loads((native/'receipt.json').read_text());assert receipt['passed']
    name={'route':'5_2_route.odb','fill':'5_3_fillcell.odb','final':'6_final.odb'}[stage]
    odb=native/'flow/results/nangate45/bv1_block_v1_s16k/base'/name
    before=file_sha(odb);assert before==receipt['outputs'][str(odb.relative_to(native))]
    helper=root/'project/experiments/block_v1/odb_geometry.tcl'
    code=helper.read_text();needle='  foreach net [$block getNets] {';assert code.count(needle)==1
    code=code.replace(needle,'  foreach net [list [$block findNet {words[674][3]}]] {\n    if {![present $net]} {error "Missing failing net"}')
    (out/'net-geometry.tcl').write_text(code)
    script='set_thread_count 16\nread_db {'+str(odb)+'}\n'
    script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\n'
    script+='source {'+str(out/'net-geometry.tcl')+'}\nbvgeom::export failing-net.tsv\nhelp detailed_route\n'
    (out/'localize.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'localize.tcl'],'localize.log')
    assert file_sha(odb)==before
    text=(out/'native-whole-drc.rpt').read_text()
    (out/'revision300-s-drc-localization.json').write_text(json.dumps(dict(passed=True,
        stage=stage,input_odb=str(odb),input_odb_sha256=before,input_source_receipt_sha256=file_sha(native/'receipt.json'),
        failed_gate_receipt_sha256=file_sha(failed/'receipt.json'),failed_gate_report_sha256=file_sha(fp),
        native_drc=text,violation_count=text.count('violation type:'),
        failing_net_geometry=(out/'failing-net.tsv').read_text(),geometry_helper_sha256=file_sha(helper),
        original_unchanged=True,physical_qualified=False,
        scope='Read-only stage localization and exact failing-net wire/via/terminal geometry; diagnostic completion is not DRC acceptance. All original databases and failed gate retained.'),indent=2)+'\n')
