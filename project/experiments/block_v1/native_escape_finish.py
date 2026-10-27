"""Regenerate native final artifacts from an accepted pre-freeze escape edit.

Only the ordinary final-report step runs: no placement, CTS, filler insertion,
reroute or optimization. All final database geometry is read back unchanged.
Actual full-chip router DRC is rerun; no old DRC report or SPEF is substituted.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from io_slots import file_sha,slot
from native_allocation_group import memory_snapshot
from native_escape_audit import def_inventory
from native_reroute import config_suffix


FLOW_HASHES={
    'Makefile':'910877da96dd7bf40b99f5a23f0f5b158aa5bf8bbd9b45d0eda4815a29bff854',
    'scripts/final_report.tcl':'93f8cca87ec112990ef7e5334b2eb16c66a2b9c4393958cce23769b8a3d6cd04',
    'scripts/final_connect.tcl':'cc85781e0387a787e2ac32a43db004390c5e62130f69a109b08cdaed836f4580',
    'scripts/final_outputs.tcl':'b56f8584f32520191869a7f6da061843b27d1cf574176902c281c7f11a159168',
    'scripts/formal_check.tcl':'2c4ace8d3a90000f0bd0d22dccab6659c3af28e43b42db3d1a1712fc4d8a89f5'}


def checked_config(source,receipt,original):
    """Bind new artifacts to the real accepted edit and exact native config."""
    path=source/'native-escape-finish.json';assert file_sha(path)==receipt['outputs'][path.name]
    proof=json.loads(path.read_text());assert proof['passed']is True
    assert all(proof['checks'].values())and proof['regenerated_rc']is True
    probe=Path(proof['probe']);r=json.loads((probe/'receipt.json').read_text());assert r['passed']is True
    assert file_sha(probe/'receipt.json')==proof['probe_receipt_sha256']
    p=probe/'native-escape-probe.json';assert file_sha(p)==r['outputs'][p.name]==proof['probe_report_sha256']
    edit=json.loads(p.read_text());assert edit['passed']is True and all(edit['checks'].values())
    assert edit['edited_odb_sha256']==proof['accepted_edit_odb_sha256']
    for name in ['config.mk','input-diodes.tcl','native-candidate.json']:
        assert file_sha(source/name)==receipt['outputs'][name]
    assert (source/'config.mk').read_bytes()==original.read_bytes()+config_suffix(40,.005,source/'input-diodes.tcl','metal10').encode()
    candidate=json.loads((source/'native-candidate.json').read_text());assert candidate['pipeline_completed']is True
    assert candidate['native_escape_repair']is True and candidate['actual_config_sha256']==file_sha(source/'config.mk')
    assert proof['actual_flow_scripts']==FLOW_HASHES
    assert file_sha(source/'native-router-drc.rpt')==receipt['outputs']['native-router-drc.rpt']==proof['native_router_drc_sha256']
    assert not(source/'native-router-drc.rpt').read_text().strip()
    return source/'config.mk'


def implement(root,out,cpus,run,policy):
    assert cpus==16 and policy in ('A','C')
    base=out.parents[2];config=json.loads((root/'project/experiments/block_v1/native_pipeline_escape.json').read_text())
    probe_run=base/config['escape_probe_run'];group=probe_run/'tasks/native-escape-probe-group'
    gr=json.loads((group/'receipt.json').read_text());assert gr['passed']is True
    gp=group/'native-escape-group.json';assert file_sha(gp)==gr['outputs'][gp.name]
    g=json.loads(gp.read_text());assert g['passed']is True and len(g['children'])==2
    probe=probe_run/'tasks'/('native-escape-probe-'+policy.lower())
    pr=json.loads((probe/'receipt.json').read_text());assert pr['passed']is True
    child=next(r for r in g['children']if r['policy']==policy.lower());assert child['passed']is True and child['receipt_sha256']==file_sha(probe/'receipt.json')
    pp=probe/'native-escape-probe.json';assert file_sha(pp)==pr['outputs'][pp.name]==child['proof_sha256']
    p=json.loads(pp.read_text());assert p['passed']is True and p['policy']==policy and all(p['checks'].values())
    helpers=['native_escape.py','native_escape_audit.py','native_escape_geometry.tcl','native_escape_gds.rb','native_escape_probe.py']
    if config.get('escape_short_repair'):helpers.append('native_escape_relocate.py')
    for name in helpers:
        path=root/'project/experiments/block_v1'/name
        assert file_sha(path)==pr['inputs'][str(path.relative_to(root))]
    for name in ['edited.odb','after.def','after.v','after-geometry.tsv']:
        assert file_sha(probe/name)==pr['outputs'][name]
    assert file_sha(probe/'edited.odb')==p['edited_odb_sha256']
    original=Path(p['source']);old=json.loads((original/'receipt.json').read_text());assert old['passed']is True
    assert file_sha(original/'receipt.json')==p['source_receipt_sha256']
    for name,digest in p['source_files'].items():assert file_sha(Path(name))==digest
    prep=base/config['preparation_run']/'tasks/native-prepare';prep_r=json.loads((prep/'receipt.json').read_text());assert prep_r['passed']is True
    blueprint=prep/('transaction6k-'+policy)/'config.mk'
    assert file_sha(blueprint)==prep_r['outputs'][str(blueprint.relative_to(prep))]
    from native_reroute import checked_config as original_config
    original_config(original,old,blueprint,margin=40,hold_margin=.005,diode=True,via_access_layer='metal10')
    relative=Path('flow/results/nangate45')/('bv1_transaction6k_'+policy)/'base'
    results=out/relative;results.mkdir(parents=True)
    for category in ['logs','reports','objects']:
        (out/'flow'/category/'nangate45'/('bv1_transaction6k_'+policy)/'base').mkdir(parents=True)
    copied={}
    def copy(source,destination,expected):
        assert file_sha(source)==expected
        with slot(base):shutil.copyfile(source,destination)
        assert file_sha(destination)==expected;destination.chmod(0o444);copied[str(destination.relative_to(out))]=expected
    copy(probe/'edited.odb',results/'6_1_fill.odb',p['edited_odb_sha256'])
    oldresults=original/relative
    copy(oldresults/'6_final.sdc',results/'6_1_fill.sdc',old['outputs'][str((relative/'6_final.sdc').as_posix())])
    for name in ['1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv']:
        copy(oldresults/name,results/name,old['outputs'][(relative/name).as_posix()])
    copy(original/'input-diodes.tcl',out/'input-diodes.tcl',old['outputs']['input-diodes.tcl'])
    (out/'config.mk').write_bytes(blueprint.read_bytes()+config_suffix(40,.005,out/'input-diodes.tcl','metal10').encode())
    flow=Path('/OpenROAD-flow-scripts/flow')
    assert {name:file_sha(flow/name)for name in FLOW_HASHES}==FLOW_HASHES
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES='+str(cpus)]
    wanted=dict(TECH_LEF=str(flow/'platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'),MAX_ROUTING_LAYER='metal10',MIN_ROUTING_LAYER='metal1',
        RCX_RULES=str(flow/'platforms/nangate45/rcx_patterns.rules'),KEEP_VARS='1',LEC_CHECK='1',SEC_CHECK='0',CAP_MARGIN='40',HOLD_SLACK_MARGIN='0.005',
        PRE_GLOBAL_ROUTE_TCL=str(out/'input-diodes.tcl'),VIA_IN_PIN_MIN_LAYER='metal10',VIA_IN_PIN_MAX_LAYER='metal10')
    for key,value in wanted.items():
        log='variable-'+key+'.log';run(command+['print-'+key],log)
        m=re.search(r'(?m)^'+key+r': (.+)$',(out/log).read_text());assert m and m[1].strip()==value
    record=dict(schema='block-v1-native-candidate/1',top='transaction6k',policy=policy,cpus=cpus,stages=[],native_escape_repair=True,
        actual_config=str(out/'config.mk'),actual_config_sha256=file_sha(out/'config.mk'),actual_variables=wanted,
        inputs_source=str(prep),inputs_receipt_sha256=file_sha(prep/'receipt.json'),source=str(original),source_receipt_sha256=file_sha(original/'receipt.json'),
        escape_probe=str(probe),escape_probe_receipt_sha256=file_sha(probe/'receipt.json'),qualified_hard_macro=False)
    def save():(out/'native-candidate.json').write_text(json.dumps(record,indent=2)+'\n')
    # This image exposes the compiled six-argument native entry point but not
    # the newer public Tcl wrapper. Verify the installed API before RCX/LEC.
    preflight='if {[llength [info commands ::drt::check_drc_cmd]] != 1} {error "Missing compiled native full-chip DRC checker"}\n'
    preflight+='set stream [open native-checker-api.txt w]\nputs $stream [info commands ::drt::*drc*]\n'
    preflight+='if {![catch {drt::check_drc_cmd} usage]} {error "Native DRC arity probe unexpectedly succeeded"}\nputs $stream $usage\nclose $stream\n'
    (out/'native-checker-preflight.tcl').write_text(preflight)
    run(['openroad','-no_init','-exit','native-checker-preflight.tcl'],'native-checker-preflight.log')
    assert 'drc_file x1 y1 x2 y2 marker_name'in(out/'native-checker-api.txt').read_text(),'Unexpected installed native DRC signature'
    save();run(command+['do-6_report'],'do-6_report.log');record['stages'].append('do-6_report');save()
    # A fresh process checks the actual regenerated final database. The
    # compiled API signature and complete DEF before/after check are retained.
    script='set_thread_count 16\nread_db {%s}\nwrite_def final-readback.def\nwrite_verilog final-all.v\n'% (results/'6_final.odb')
    script+='if {[llength [info commands ::drt::check_drc_cmd]] != 1} {error "Missing compiled native full-chip DRC checker"}\n'
    # Same compiled entry point and whole-block zero box used by the upstream
    # public wrapper; no route repair, clipping, or suppression is requested.
    script+='drt::check_drc_cmd native-router-drc.rpt 0 0 0 0 native_escape_drc\nwrite_def checked-readback.def\n'
    (out/'native-final-check.tcl').write_text(script);run(['openroad','-no_init','-exit','native-final-check.tcl'],'native-final-check.log')
    a,ah=def_inventory(probe/'after.def');b,bh=def_inventory(out/'final-readback.def')
    assert a==b and ah==bh,'Final reporting changed accepted native geometry or hardware'
    assert file_sha(out/'final-readback.def')==file_sha(out/'checked-readback.def'),'Native DRC checker changed geometry'
    assert file_sha(out/'final-all.v')==file_sha(probe/'after.v'),'Final reporting changed full physical/logical netlist'
    assert file_sha(results/'6_final.sdc')==file_sha(oldresults/'6_final.sdc'),'Final reporting changed constraints'
    assert not(out/'native-router-drc.rpt').read_text().strip(),'Actual full-chip native router DRC failed'
    report=out/'flow/reports/nangate45'/('bv1_transaction6k_'+policy)/'base/5_route_drc.rpt'
    shutil.copyfile(out/'native-router-drc.rpt',report)
    assert all(file_sha(out/name)==digest for name,digest in copied.items())
    assert all(file_sha(Path(name))==digest for name,digest in p['source_files'].items())
    checks=dict(accepted_probe=True,exact_final_def_scope=True,exact_final_full_netlist=True,constraints_unchanged=True,
        fresh_native_extraction=(results/'6_final.spef').stat().st_size>0,actual_full_chip_router_drc_zero=True,checker_geometry_unchanged=True)
    proof=dict(schema='block-v1-native-escape-finish/1',passed=all(checks.values()),checks=checks,policy=policy,
        probe=str(probe),probe_receipt_sha256=file_sha(probe/'receipt.json'),probe_report_sha256=file_sha(pp),accepted_edit_odb_sha256=p['edited_odb_sha256'],
        actual_flow_scripts=FLOW_HASHES,regenerated_rc=True,native_router_drc_sha256=file_sha(out/'native-router-drc.rpt'),
        native_checker_api_sha256=file_sha(out/'native-checker-api.txt'),native_checker_command='drt::check_drc_cmd native-router-drc.rpt 0 0 0 0 native_escape_drc',copied_input_hashes=copied,
        full_independent_drc_qualified=False,exact_final_function_qualified=False,qualified_hard_macro=False,
        scope='Ordinary native final outputs/LEC/RCX regenerated from accepted fixed-via edit, exact geometry/hardware/constraints readback and actual whole-chip native router DRC; independent full GDS/DRC/STA/function/macro gates remain required')
    (out/'native-escape-finish.json').write_text(json.dumps(proof,indent=2)+'\n')
    record['pipeline_completed']=True;record['final_files']={f.name:dict(path=str(f),sha256=file_sha(f))for f in results.glob('6_final.*')}
    assert all('6_final.'+ext in record['final_files']for ext in ['odb','sdc','v','spef','def']);save()
    checked_config(out,dict(outputs={name:file_sha(out/name)for name in ['native-escape-finish.json','config.mk','input-diodes.tcl','native-candidate.json','native-router-drc.rpt']}),blueprint)


def group(root,out,cpus,qualify=False):
    assert cpus==32
    specs=[('native-escape-'+role+'-transaction6k-'+p,proof,8 if qualify else 16)
           for role,proof in ([('receive','native-physical-receiver.json'),('final','native-final-function.json')]if qualify else[('run','native-escape-finish.json')])for p in ['a','c']]
    memory=memory_snapshot();child_cpus=specs[0][2]
    simultaneous=next((n for n in ([4,2,1]if qualify else[2,1])if memory['MemAvailable']>=n*32*1024**3*1.2),1)
    assert child_cpus*simultaneous<=cpus
    def execute(spec):
        mode,name,allocated=spec;folder=out.parent/mode;folder.mkdir(exist_ok=False);started=time.time()
        env=dict(os.environ,OMP_NUM_THREADS=str(allocated),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,str(allocated)],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        path=folder/'receipt.json';proof=folder/name;r=json.loads(path.read_text())if path.exists()else{}
        passed=code==0 and r.get('passed')is True and proof.exists()
        if passed:passed=r['cpus']==allocated and r['mode']==mode and file_sha(proof)==r['outputs'][name]and json.loads(proof.read_text())['passed']is True
        return dict(mode=mode,cpus=allocated,started=started,finished=time.time(),returncode=code,passed=passed,
                    receipt_sha256=file_sha(path)if path.exists()else None,proof_sha256=file_sha(proof)if proof.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=simultaneous)as pool:children=list(pool.map(execute,specs))
    record=dict(schema='block-v1-native-escape-'+('qualification'if qualify else'finish')+'-group/1',passed=all(r['passed']for r in children),
        allocated_cpus=cpus,simultaneous_workers=simultaneous,maximum_concurrent_cpu_ceilings=child_cpus*simultaneous,memory_preflight=memory,
        children=children,qualified_hard_macro=False,scope='Independent full native finish or full physical/function children; peer failure retains all evidence, no macro/twelve-layer qualification')
    (out/'native-escape-finish-group.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'Native escape final/qualification child failed; peer evidence preserved'
