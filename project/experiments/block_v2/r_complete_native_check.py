"""Prepared complete-die native check; inactive until the diagnostic is proved.

This changes only an in-memory check partition. It keeps original fragmented
results, all rules, the full die and every geometry byte. It does not issue a
leaf acceptance result. Callers must still run independent full GDS rules.
"""
import json
from pathlib import Path
import shutil
import time
from r_monolithic_drc import compare_grid_only


def complete_diagnostic_admission(root,sha,candidate=None):
    """Fail closed until the actual full-die diagnostic is received and bound."""
    evidence=root/'work/YUZE-LU/143/r-input-hold/geometry-135'
    index=json.loads((evidence/'index.json').read_text())
    assert index['sequence']=='135' and index['job']==94492
    assert index['source_commit']=='23a1ee59697935ed80830430264cffbec0934ef8'
    assert index['diagnostic_completed'] and not index['qualified'] and not index['native_leaf_accepted']
    for name,digest in index['files'].items():assert sha(evidence/name)==digest
    result=json.loads((evidence/'diagnostic.json').read_text())
    assert result['mode']=='monolithic' and result['diagnostic_completed'] and result['source_bytes_unchanged']
    assert result['monolithic_native_diagnostic'] and result['native_drc_zero'] and result['native_drc_count']==0
    assert result['original_source_unchanged'] and result['intentional_short_detected']
    assert result['complete_die_box_dbu']==[0,0,6000000,6000000] and result['one_complete_native_worker']
    assert not result['qualified'] and not result['native_leaf_accepted']
    expected=json.loads((root/'work/YUZE-LU/143/r-input-hold/buffer-129/index.json').read_text())['large_remote_files']['candidate.odb']['sha256']
    assert result['candidate_odb_sha256']==expected
    if candidate is not None:assert sha(candidate/'candidate.odb')==expected
    bound=[(path,digest) for path,digest in result['inputs'].items() if path.endswith('/outputs/129/candidate.odb')]
    assert len(bound)==1 and bound[0][1]==expected
    assert len(result['commands'])==2 and all(c['returncode']==0 for c in result['commands'])
    assert [c['log'] for c in result['commands']]==['negative.log','monolithic.log']
    for name in ('native-monolithic-drc.rpt','negative-drc.rpt','grid-only-proof.json'):
        assert sha(evidence/name)==result['outputs'][name]['sha256']
    assert not (evidence/'native-monolithic-drc.rpt').read_bytes()
    assert 'violation type: Short' in (evidence/'negative-drc.rpt').read_text()
    geometry=json.loads((evidence/'grid-only-proof.json').read_text())
    assert geometry==result['grid_only_proof'] and geometry['passed'] and geometry['identical_physical_geometry_and_connections']
    _,control=control_evidence(root,sha)
    assert result['technology_sha256']==control['technology_sha256']
    return dict(passed=True,diagnostic_only=True,source_index_sha256=sha(evidence/'index.json'),
                candidate_odb_sha256=expected,technology_sha256=result['technology_sha256'],
                complete_die_box_dbu=result['complete_die_box_dbu'],geometry_proof=geometry,
                source_report_sha256=sha(evidence/'native-monolithic-drc.rpt'),native_leaf_accepted=False)


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
    admission=complete_diagnostic_admission(root,sha)
    before_sha=sha(odb);controls=fresh_controls(root,out,run,sha)
    observations=[]
    while True:
        available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024
        observations.append(dict(time_unix=time.time(),available_bytes=available,required_bytes=384*1024**3))
        (out/'native-complete-memory-admission.json').write_text(json.dumps(dict(passed=available>=384*1024**3,observations=observations),indent=2)+'\n')
        if available>=384*1024**3:break
        time.sleep(30)
    script='set_thread_count 16\nread_db {'+str(odb)+'}\n'+'''
set b [ord::get_db_block];set die [$b getDieArea]
if {[$b getDbUnitsPerMicron]!=2000 || [$die xMin]!=0 || [$die yMin]!=0 || [$die xMax]!=6000000 || [$die yMax]!=6000000} {error "Not the complete declared R die"}
set g [$b getGCellGrid]
set expected_grid {}
for {set i 0} {$i<1052} {incr i} {lappend expected_grid [expr {$i*5700}]}
if {[$g getNumGridPatternsX]!=1 || [$g getNumGridPatternsY]!=1 || [$g getGridX] ne $expected_grid || [$g getGridY] ne $expected_grid} {error "Unexpected R grid"}
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
                controls=controls,full_die_diagnostic_admission=admission,fragmented_report_sha256=sha(out/'native-fragmented-drc.rpt'),
                fragmented_diagnostic_count=(out/'native-fragmented-drc.rpt').read_text().count('violation type:'),
                native_report_sha256=sha(out/'native-whole-drc.rpt'),native_leaf_accepted=False,
                scope='Unmodified native all-rule full-die check without artificial interior worker clipping; fragmented diagnostic preserved, full GDS deck and other gates remain required')
    (out/'native-complete-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
    return result
