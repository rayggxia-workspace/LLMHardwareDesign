"""Prepared complete-die native check; inactive until the diagnostic is proved.

This changes only an in-memory check partition. It keeps original fragmented
results, all rules, the full die and every geometry byte. It does not issue a
leaf acceptance result. Callers must still run independent full GDS rules.
"""
import json
from pathlib import Path
import shutil
from r_monolithic_drc import compare_grid_only


def control_evidence(root,sha):
    evidence=root/'work/YUZE-LU/143/r-input-hold/geometry-136'
    index=json.loads((evidence/'index.json').read_text())
    for name,digest in index['files'].items():assert sha(evidence/name)==digest
    result=json.loads((evidence/'diagnostic.json').read_text())
    assert result['diagnostic_completed'] and result['partition_effect_reproduced']
    assert result['real_foreign_net_spacing_detected'] and result['real_same_net_notch_detected']
    assert not result['qualified'] and not result['native_leaf_accepted']
    assert len(result['commands'])==3 and all(c['returncode']==0 for c in result['commands'])
    compare_grid_only(evidence/'fragmented.def',evidence/'complete.def')
    assert not (evidence/'complete-drc.rpt').read_bytes()
    return evidence,result


def fresh_controls(root,out,run,sha):
    evidence,old=control_evidence(root,sha)
    tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
    assert sha(tech)==old['technology_sha256']
    output={}
    for label in ('fragmented','complete','spacing-negative'):
        definition=out/('control-'+label+'.def');shutil.copyfile(evidence/(label+'.def'),definition)
        assert sha(definition)==sha(evidence/(label+'.def'))
        report='control-'+label+'-drc.rpt'
        script='set_thread_count 16\nread_lef {'+str(tech)+'}\nread_def {'+str(definition)+'}\ndrt::check_drc_cmd '+report+' 0 0 0 0 complete_native_control\n'
        path=out/('control-'+label+'.tcl');path.write_text(script)
        run(['openroad','-no_init','-exit',path],'control-'+label+'.log')
        # Native report text contains geometry and nets, not output paths.
        assert (out/report).read_bytes()==(evidence/(label+'-drc.rpt')).read_bytes()
        output[label]=dict(report_sha256=sha(out/report),expected_sha256=sha(evidence/(label+'-drc.rpt')))
    return dict(passed=True,source_index_sha256=sha(evidence/'index.json'),technology_sha256=sha(tech),
                real_foreign_spacing_and_same_net_notch_detected=True,exact_fragmented_reproduction=True,results=output)


def check(root,out,odb,run,sha):
    """Do not call until exact full-die135 has passed with unchanged geometry."""
    before_sha=sha(odb);controls=fresh_controls(root,out,run,sha)
    script='set_thread_count 16\nread_db {'+str(odb)+'}\n'+'''
set b [ord::get_db_block];set die [$b getDieArea]
if {[$b getDbUnitsPerMicron]!=2000 || [$die xMin]!=0 || [$die yMin]!=0 || [$die xMax]!=6000000 || [$die yMax]!=6000000} {error "Not the complete declared R die"}
set g [$b getGCellGrid]
if {[$g getNumGridPatternsX]!=1 || [$g getNumGridPatternsY]!=1 || [$g getGridPatternX 0] ne {0 1052 5700} || [$g getGridPatternY 0] ne {0 1052 5700}} {error "Unexpected R grid"}
write_def before.def
drt::check_drc_cmd native-fragmented-drc.rpt 0 0 0 0 native_fragmented_diagnostic
$g resetGrid
$g addGridPatternX 0 2 6000000
$g addGridPatternY 0 2 6000000
if {[$g getGridX] ne {0 6000000} || [$g getGridY] ne {0 6000000}} {error "Complete coverage readback failed"}
write_def complete-grid-before.def
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_complete_die
write_def complete-grid-after.def
$g resetGrid
$g addGridPatternX 0 1052 5700
$g addGridPatternY 0 1052 5700
write_def after.def
puts COMPLETE_DIE_NATIVE_CHECK_COMPLETE
'''
    # Two separate OpenROAD processes are required: TritonRoute caches its
    # imported grid/design after a check. Never reuse that cache for new tiling.
    boundary='drt::check_drc_cmd native-fragmented-drc.rpt 0 0 0 0 native_fragmented_diagnostic\n'
    a,b=script.split(boundary)
    (out/'native-fragmented.tcl').write_text(a+boundary)
    run(['openroad','-no_init','-exit',out/'native-fragmented.tcl'],'native-fragmented.log')
    # Recreate the DB setup in a clean process, omitting the first check.
    (out/'native-complete.tcl').write_text(a+b)
    run(['openroad','-no_init','-exit',out/'native-complete.tcl'],'native-complete.log')
    assert sha(out/'before.def')==sha(out/'after.def')
    assert sha(out/'complete-grid-before.def')==sha(out/'complete-grid-after.def')
    proof=compare_grid_only(out/'before.def',out/'complete-grid-before.def')
    assert sha(odb)==before_sha
    native=(out/'native-whole-drc.rpt').read_text()
    result=dict(passed=not native.strip(),original_source_unchanged=True,source_odb_sha256=before_sha,
                complete_native_rule_check=True,complete_die_box_dbu=[0,0,6000000,6000000],
                one_complete_native_worker=True,no_marker_or_rule_exclusions=True,geometry_proof=proof,
                controls=controls,fragmented_report_sha256=sha(out/'native-fragmented-drc.rpt'),
                fragmented_diagnostic_count=(out/'native-fragmented-drc.rpt').read_text().count('violation type:'),
                native_report_sha256=sha(out/'native-whole-drc.rpt'),native_leaf_accepted=False,
                scope='Unmodified native all-rule full-die check without artificial interior worker clipping; fragmented diagnostic preserved, full GDS deck and other gates remain required')
    (out/'native-complete-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
    return result
