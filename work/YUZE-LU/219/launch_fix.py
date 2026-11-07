"""Freeze this task's source into a fresh Slurm directory; never touch other jobs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
REMOTE = 'yuzelu@10.129.166.172'
BASE = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('name')
    p.add_argument('script')
    p.add_argument('arguments', nargs='*')
    a = p.parse_args()
    if not a.name.startswith('algorithm-fix-') or any(c not in '-_.abcdefghijklmnopqrstuvwxyz0123456789' for c in a.name):
        raise ValueError('task directory name rejected')
    src = ROOT / 'project/experiments/block_synthesis'
    archive = Path.home() / 'AppData/Local/Codex' / (a.name + '.tar')
    manifest = {}
    with tarfile.open(archive, 'w') as tar:
        for file in sorted(src.iterdir()):
            if file.suffix not in ('.py', '.sbatch', '.cpp', '.hpp', '.vlt', '.sv'):
                continue
            data = file.read_text(encoding='utf-8').encode('utf-8')
            info = tarfile.TarInfo(file.name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            manifest[file.name] = hashlib.sha256(data).hexdigest()
        if a.script in ('native-probe.sbatch', 'leaf-replay.sbatch'):
            for name in ('block_v2/block_v2_m.sv', 'block_v2/block_v2_g.sv',
                         'block_v2/block_v2_g_tables.svh', 'block_v2/block_v2_e.sv',
                         'block_v2/block_v2_e_compact.sv', 'block_v1/transaction6k.sv',
                         'r_local_state/r_stream_local.sv', 'r_local_state/r_state_store.sv'):
                file = ROOT / 'project/rtl' / name
                data = file.read_text(encoding='utf-8').encode('utf-8')
                target = 'frozen-leaves/' + file.name
                info = tarfile.TarInfo(target)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
                manifest[target] = hashlib.sha256(data).hexdigest()
    remote = BASE + '/' + a.name
    subprocess.run(['ssh', REMOTE, 'mkdir', remote], check=True, timeout=30)
    subprocess.run(['scp', str(archive), REMOTE + ':' + remote + '/source.tar'], check=True, timeout=60)
    subprocess.run(['ssh', REMOTE, 'tar', '-xf', remote + '/source.tar', '-C', remote], check=True, timeout=30)
    cmd = ['ssh', REMOTE, 'sbatch', '--parsable', '--output=' + remote + '/slurm.log',
           remote + '/' + a.script, remote] + a.arguments
    job = subprocess.check_output(cmd, timeout=30).decode().strip()
    receipt = {'directory': remote, 'job': job, 'source_sha256': manifest}
    target = Path.home() / 'AppData/Local/Codex' / (a.name + '.json')
    target.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'job': job, 'directory': remote}))


if __name__ == '__main__':
    main()
