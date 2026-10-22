"""Issue-15 physical implementations, with every attempt in a fresh directory."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from run import ROOT, PLATFORM, SOURCES, INPUTS, digest, track, result, run_tcl

def verified_copy(source, relative, destination):
    entries = {line[66:]:line[:64] for line in (source/'output-files.sha256').read_text().splitlines()}
    old=source/relative
    assert digest(old)==entries[relative], relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(old,destination)
    assert digest(destination)==entries[relative]
    track(old)

def repair(spec):
    source=SOURCES['merged']
    suffix=result(source).relative_to(source)
    dest=ROOT/suffix
    for name in ('4_cts.odb','4_cts.sdc'):
        verified_copy(source,(suffix/name).as_posix(),dest/name)
    for name in ('config.mk','boundary.sdc','boundary.sv','elab.v','elab.json','experiment.json'):
        verified_copy(source,name,ROOT/name)
    for path in (source/'memory-model').rglob('*'):
        if path.is_file(): verified_copy(source,path.relative_to(source).as_posix(),ROOT/path.relative_to(source))
    margin=int(spec.get('cap_margin',30))
    assert 0<=margin<100
    config=(ROOT/'config.mk').read_text().replace(str(source),str(ROOT))
    config,n=re.subn(r'^export CAP_MARGIN = \d+$','export CAP_MARGIN = '+str(margin),config,flags=re.M)
    assert n==1
    # Cell swaps are deliberately not dont_touch: the prior frozen BUF input
    # prevented InsertBufferBeforeLoads and caused RSZ-3006 in both margin runs.
    hook='set b [ord::get_db_block]\nset f [open {'+str(ROOT/'replacements.tsv')+'} w]\n'
    replacements=[('place15504','BUF_X1','BUF_X4'),('place15492','BUF_X1','BUF_X4'),('place15563','BUF_X1','BUF_X4')]
    for name,before,after in replacements:
        hook+='set inst [$b findInst {'+name+'}]\n'
        hook+='if {$inst eq "NULL" || [[$inst getMaster] getName] ne {'+before+'}} {error {Unexpected repair instance}}\n'
        hook+='if {![replace_cell {'+name+'} {'+after+'}]} {error {Cell replacement failed}}\n'
        hook+='puts $f {'+name+' '+before+' -> '+after+'}\n'
    hook+='close $f\ndetailed_placement_helper\ncheck_placement -verbose\n'
    (ROOT/'repair.tcl').write_text(hook)
    config+='export PRE_GLOBAL_ROUTE_TCL = '+str(ROOT/'repair.tcl')+'\n'
    (ROOT/'config.mk').write_text(config)
    meta=json.loads((ROOT/'experiment.json').read_text())
    meta.update(cap_margin=margin,repair=dict(checkpoint=str(source/'4_cts.odb'),
        freeze_cells=False,replacements=replacements,reason='Remove conflicting dont_touch; stronger buffer drive; unchanged logical functions and clock/IO budget'))
    (ROOT/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(ROOT/'config.mk'),
             'WORK_HOME='+str(ROOT/'flow'),'NUM_CORES='+str(spec['cores'])]
    for target in ('do-route','do-finish','do-generate_abstract'):
        with (ROOT/(target+'.log')).open('w') as f:
            subprocess.run(command+[target],stdout=f,stderr=subprocess.STDOUT,check=True)
    run_tcl('detail','read_db {'+str(dest/'6_final.odb')+'}\nwrite_abstract_lef -bloat_factor 0 {'+str(dest/'llhd_opentpu_act_mxu.detailed.lef')+'}\n')

def execute(spec):
    if spec['mode']=='repair': repair(spec)
    else: raise ValueError('Not implemented: '+spec['mode'])
