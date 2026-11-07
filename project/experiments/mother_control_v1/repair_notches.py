"""Clone a final mother candidate, fill verified same-net M2/M3 gaps, re-extract."""
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent

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
    assert 0 < len(blocks) <= 32
    patches = []
    for block in blocks:
        assert block.startswith('Metal Spacing\n') and block.count('net:') == 1, block
        net = re.search(r'srcs: net:(.*?)\n', block)[1]
        match = re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)', block)
        assert match and match[5] in ('metal2','metal3'), block
        coords = [round(float(match[i]) * 2000) for i in range(1, 5)]
        assert all(x % 10 == 0 for x in coords), coords
        x0,y0,x1,y1 = coords
        assert 0 < x1-x0 <= 300 and 0 < y1-y0 <= 300, coords
        patches.append((net, match[5], x0-10, y0-10, x1+10, y1+10))
    patch_file = out / 'native-notch-patches.tsv'
    patch_file.write_text(''.join('\t'.join(map(str,row))+'\n' for row in patches))
    for name in ('5_route.sdc','1_synth_lec.v'):
        shutil.copyfile(original / name, target / name)
    shutil.copyfile(source / 'config.mk', out / 'config.mk')
    for path in source.glob('*.lib'):
        shutil.copyfile(path, out / path.name)
    checkpoint = original / '5_route.odb'
    original_sha = sha(checkpoint)
    env = dict(os.environ, MC_NOTCH_INPUT=str(checkpoint), MC_NOTCH_OUTPUT=str(target / '5_route.odb'), MC_NOTCH_PATCHES=str(patch_file))
    commands = []
    def run(command, log):
        with (out / log).open('w') as stream:
            subprocess.run(list(map(str, command)), env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
        commands.append(dict(command=list(map(str,command)), log=log, log_sha256=sha(out/log)))
    run(['openroad','-no_init','-exit',HERE / 'repair_notches.tcl'], 'patch.log')
    make = ['make','-C','/OpenROAD-flow-scripts/flow', 'DESIGN_CONFIG='+str(out/'config.mk'), 'WORK_HOME='+str(out/'flow'), 'NUM_CORES='+os.environ['SLURM_CPUS_PER_TASK']]
    for stage in ('do-finish','do-gds'):
        run(make+[stage], stage+'.log')
    assert sha(checkpoint) == original_sha
    inputs = json.loads((source / 'inputs.json').read_text())
    inputs.update(geometry_repair=dict(source_candidate=str(source), checkpoint=str(checkpoint), checkpoint_sha256=original_sha,
        drc_sha256=sha(a.drc), patch_file_sha256=sha(patch_file), count=len(patches),
        tcl_sha256=sha(HERE/'repair_notches.tcl'), python_sha256=sha(Path(__file__)),
        adds_only_same_net_metal=True, fresh_extraction_required=True), qualified=False)
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')

if __name__ == '__main__':
    main()
