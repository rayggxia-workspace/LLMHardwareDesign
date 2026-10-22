"""Copy verified CTS inputs into a new attempt and reroute explicit drive upgrades."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from repair_hook import build_hook
from resume_config import configure_resume

root = Path.cwd()
spec = json.loads(Path('task.json').read_text())
assert spec['kind'] == 'route-repair'
source = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06')/spec['source_task']
assert spec['source_task'] in ('act-cap10', 'merged-cap20')
assert not (root/'flow').exists()
nickname = 'parallel_'+spec['case'].replace('-', '_')
suffix = Path('flow/results/nangate45')/nickname/'base'
old_results = source/suffix
results = root/suffix
results.mkdir(parents=True)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


manifest = dict((line[66:], line[:64]) for line in (source/'output-files.sha256').read_text().splitlines())
inputs = []


def copy_verified(relative):
    old = source/relative
    expected = manifest[relative]
    actual = digest(old)
    assert actual == expected, relative
    destination = root/relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(old), str(destination))
    assert digest(destination) == expected, relative
    inputs.append(dict(source=str(old), destination=str(destination), sha256=expected))


for name in ('4_cts.odb', '4_cts.sdc'):
    copy_verified((suffix/name).as_posix())
for name in ('boundary.sdc', 'boundary.sv', 'elab.v', 'elab.json'):
    copy_verified(name)
for path in sorted((source/'memory-model').rglob('*')):
    if path.is_file():
        copy_verified(path.relative_to(source).as_posix())
copy_verified('config.mk')
copy_verified('experiment.json')

script = build_hook(spec['replacements'])
hook = root/'targeted-repair.tcl'
hook.write_text(script)
config, source_margin = configure_resume((root/'config.mk').read_text(), source, root, spec['cap_margin'])
config += 'export PRE_GLOBAL_ROUTE_TCL = '+str(hook)+'\n'
(root/'config.mk').write_text(config)
meta = json.loads((root/'experiment.json').read_text())
assert meta['cap_margin'] == source_margin
meta.update(cap_margin=spec['cap_margin'], repair=dict(source_attempt=str(source), checkpoint='4_cts.odb', replacements=spec['replacements'],
    source_cap_margin=source_margin, requested_route_cap_margin=spec['cap_margin'],
    placement_and_cts_reused=True, synthesis_repeated=False, changes='Equivalent port-list cell drive variants; no RTL, IO budget, register or cycle changes'),
    scope='Targeted CTS-checkpoint physical reroute; no full formal equivalence, hard macro qualification or signoff')
(root/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
Path('checkpoint-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
Path('checkpoint-inputs.sha256').write_text(''.join(i['sha256']+'  '+i['source']+'\n' for i in inputs))
Path('physical-temporary-policy.txt').write_text('Tool-default temporary directory; no long TMPDIR override\n')

command = ['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(root/'config.mk'),
    'WORK_HOME='+str(root/'flow'),'NUM_CORES='+os.environ['NUM_CORES']]
for target, logname in [('do-route','flow.log'),('do-finish','finish.log'),('do-generate_abstract','abstract.log')]:
    with Path(logname).open('w') as log:
        subprocess.run(command+[target],stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run(['python3',str(Path(os.environ['LLHD_BATCH'])/'runner/wave2/export_detail.py')],check=True)
if not (results/'6_final.v').is_file():
    Path('export-netlist.tcl').write_text('read_db {'+str(results/'6_final.odb')+'}\nwrite_verilog {'+str(results/'6_final.v')+'}\n')
    with Path('export-netlist.log').open('w') as log:
        subprocess.run(['openroad','-exit','export-netlist.tcl'],stdout=log,stderr=subprocess.STDOUT,check=True)
