"""Reroute immutable CTS with temporary keepouts; remove them before final export."""
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--drc', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    source = a.candidate.resolve()
    original = source / 'flow/results/nangate45/mother_control_64/base'
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = out / original.relative_to(source)
    target.mkdir(parents=True)
    blocks = a.drc.read_text().strip().split('violation type: ')[1:]
    assert 0 < len(blocks) <= 64
    guards = []
    for block in blocks:
        assert block.startswith(('Metal Spacing\n','Cut Spacing\n')), block
        match = re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)', block)
        assert match and match[5] in ('metal2','metal3','metal9','metal10','via9'), block
        coords = [round(float(match[i]) * 2000) for i in range(1,5)]
        assert all(v % 10 == 0 for v in coords)
        x0,y0,x1,y1 = coords
        assert 0 < x1-x0 <= 6000 and 0 < y1-y0 <= 6000
        guards.append((match[5], x0-10, y0-10, x1+10, y1+10))
    guards = sorted(set(guards))
    guard_file = out / 'routing-guards.tsv'
    guard_file.write_text(''.join('\t'.join(map(str,row))+'\n' for row in guards))
    create = out / 'create-guards.tcl'
    create.write_text('set block [ord::get_db_block]\nset tech [[ord::get_db] getTech]\n'+''.join('odb::dbObstruction_create $block [$tech findLayer '+layer+'] '+ ' '.join(map(str,coords))+'\n' for layer,*coords in guards))
    remove = out / 'remove-guards.tcl'
    remove.write_text('set mc_guards {\n'+''.join(' {'+' '.join(map(str,row))+'}\n' for row in guards)+''' }
set block [ord::get_db_block]
set removed 0
foreach obstruction [$block getObstructions] {
 set b [$obstruction getBBox]
 set row [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
 if {[lsearch -exact $mc_guards $row]>=0} {odb::dbObstruction_destroy $obstruction;incr removed}
}
if {$removed!=[llength $mc_guards]} {error "Temporary routing guard removal mismatch"}
puts "MC_ROUTING_GUARDS_REMOVED $removed"
''')
    pre = out / 'pre-route.tcl'
    pre.write_text('source {'+str(source/'input-diodes.tcl')+'}\nsource {'+str(create)+'}\n')
    post = out / 'post-route.tcl'
    post.write_text('source {'+str(source/'landing-patches.tcl')+'}\nsource {'+str(remove)+'}\n')
    config = (source/'config.mk').read_text()
    config += '\nexport PRE_GLOBAL_ROUTE_TCL = '+str(pre)+'\nexport POST_DETAIL_ROUTE_TCL = '+str(post)+'\n'
    (out/'config.mk').write_text(config)
    for name in ('4_cts.odb','4_cts.sdc','1_synth_lec.v'):
        shutil.copyfile(original/name,target/name)
    commands = []
    make = ['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES='+os.environ['SLURM_CPUS_PER_TASK']]
    inputs = json.loads((source/'inputs.json').read_text())
    inputs.update(qualified=False,reroute_guards=dict(source_candidate=str(source),cts_odb_sha256=sha(original/'4_cts.odb'),
        drc_sha256=sha(a.drc),guard_file_sha256=sha(guard_file),count=len(guards),manufactured=False,
        removal_required_before_final=True,script_sha256=sha(Path(__file__))))
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    for stage in ('do-route','do-finish','do-gds'):
        with (out/(stage+'.log')).open('w') as log:
            result = subprocess.run(make+[stage],stdout=log,stderr=subprocess.STDOUT)
        commands.append(dict(stage=stage,returncode=result.returncode,log_sha256=sha(out/(stage+'.log'))))
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        result.check_returncode()
    assert sha(original/'4_cts.odb') == inputs['reroute_guards']['cts_odb_sha256']

if __name__ == '__main__':
    main()