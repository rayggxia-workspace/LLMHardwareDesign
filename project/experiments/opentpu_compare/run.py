"""Compute-node operations. Frozen old experiments are read-only inputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
SPEC = json.loads((ROOT/'spec.json').read_text())
PLATFORM = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
OLD = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7')
SOURCES = {name: OLD/'parallel-blocks-wave2-06'/task for name,task in
           [('act','act-cap20'),('mxu','mxu-cap20'),('merged','merged-cap20')]}
INPUTS = {}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def track(path):
    INPUTS[str(path)] = digest(path)
    return path

def result(source):
    meta=json.loads((source/'experiment.json').read_text())
    if 'result_relative' in meta: return source/meta['result_relative']
    return source/'flow/results/nangate45'/('parallel_'+meta['case'].replace('-','_'))/'base'

def tcl_read(source):
    r=result(source)
    text='read_liberty {'+str(track(PLATFORM/'lib/NangateOpenCellLibrary_typical.lib'))+'}\n'
    for lib in sorted((source/'memory-model/macros').glob('*.lib')):
        text+='read_liberty {'+str(track(lib))+'}\n'
    for ext,cmd in [('odb','read_db'),('sdc','read_sdc'),('spef','read_spef')]:
        text+=cmd+' {'+str(track(r/('6_final.'+ext)))+'}\n'
    return text+'set_propagated_clock [all_clocks]\n'

def run_tcl(name,text):
    path=ROOT/(name+'.tcl'); path.write_text(text)
    with (ROOT/(name+'.log')).open('w') as f:
        subprocess.run(['openroad','-exit',str(path)],stdout=f,stderr=subprocess.STDOUT,check=True)

def probe():
    for name,source in SOURCES.items():
        script=tcl_read(source)
        script+='report_check_types -max_capacitance -violators\n'
        script+='report_checks -path_delay max -group_path_count 5 -format full_clock_expanded\n'
        script+='report_checks -path_delay min -group_path_count 3 -format full_clock_expanded\n'
        script+='report_clock_min_period\n'
        script+='write_abstract_lef -bloat_factor 0 {'+str(ROOT/(name+'.lef'))+'}\n'
        script+='write_timing_model {'+str(ROOT/(name+'.lib'))+'}\n'
        script+='set b [ord::get_db_block]\nset out [open {'+str(ROOT/(name+'-masters.tsv'))+'} w]\n'
        script+='foreach inst [$b getInsts] {puts $out "[$inst getName]\\t[[$inst getMaster] getName]"}\nclose $out\n'
        run_tcl(name,script)
    snippets={}
    for relative in ['Makefile','scripts/global_route.tcl','scripts/pdn.tcl','scripts/load.tcl','platforms/nangate45/pdn.tcl']:
        path=Path('/OpenROAD-flow-scripts/flow')/relative
        if path.exists(): snippets[relative]=path.read_text()
    (ROOT/'flow-source-snippets.json').write_text(json.dumps(snippets,indent=2)+'\n')

if __name__ == '__main__':
    sys.modules['run'] = sys.modules[__name__]
    if SPEC['mode']=='probe': probe()
    else:
        from implementation import execute
        execute(SPEC)
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
