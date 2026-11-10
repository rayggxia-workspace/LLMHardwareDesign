"""Restore immutable #247 inputs and generate its latest R4 model unchanged."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = '9d987151ee687322c0ce52d69a0a14f2275bd52b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def restore(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    archived = REPO / 'work/Melodydt/247/speed-iterations/round04/run23'
    locks = json.loads((archived / 'inputs.json').read_bytes())['input_sha256']
    for path in (archived / 'frozen-inputs').rglob('*'):
        if not path.is_file():
            continue
        name = path.relative_to(archived / 'frozen-inputs').as_posix()
        if name.endswith('.gz.b64'):
            name = name[:-7]
            data = gzip.decompress(base64.b64decode(path.read_bytes()))
        else:
            data = path.read_bytes()
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for name, digest in locks.items():
        if (out / name).exists() and sha(out / name) != digest:
            raise ValueError('frozen input SHA drift: ' + name)
    generated = out / 'baseline'
    command = [sys.executable, '-B', str(REPO / 'project/experiments/iterative_speed/round04/generate_round4.py'),
               '--repo', str(REPO), '--out', str(generated),
               '--r1-calibration', str(out / 'r1-calibration-result.json'),
               '--r2-calibration', str(out / 'r2-calibration-result.json'),
               '--calibration', str(out / 'calibration-result.json')]
    subprocess.run(command, check=True, stdout=(out / 'generation.log').open('w'))
    return generated


if __name__ == '__main__':
    print(restore(Path(sys.argv[1])))
