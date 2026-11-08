"""Check the scoped main import and resolve the unchanged CFJ control snapshot."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def locked_control():
    lock = json.loads((ROOT / 'project/experiments/cfj_leaf_base/control64-lock.json').read_text())
    resolved = {}
    for name, expected in lock['files'].items():
        path = ROOT / name
        if not path.is_file() or blob(path) != expected['git_blob']:
            path = HERE / 'frozen_inputs' / name
        if not path.is_file() or blob(path) != expected['git_blob'] or sha(path) != expected['sha256']:
            raise ValueError('CFJ frozen dependency mismatch: ' + name)
        resolved[name] = path
    return resolved


def frozen_control(out):
    out.mkdir(parents=True, exist_ok=False)
    for name, source in locked_control().items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return out


def check():
    lock = json.loads((HERE / 'main-lock.json').read_text())
    for name, expected in lock['files'].items():
        if blob(ROOT / name) != expected['git_blob']:
            raise ValueError('main-authoritative source mismatch: ' + name)
    helpers = json.loads((HERE / 'physical-dependencies.json').read_text())
    for name, expected in helpers['files'].items():
        if blob(ROOT / name) != expected['git_blob']:
            raise ValueError('main physical helper mismatch: ' + name)
    same = [('project/control_rtl_min_v0_1/' + n, 'project/rtl/mother_control_v1/' + n)
            for n in ('mc_min_controller.sv', 'mc_ports.svh', 'instruction_fetch.svh')]
    same += [('project/control_boot_v1/control_pm.sv', 'project/rtl/mother_control_v1/control_pm.sv')]
    for left, right in same:
        assert (ROOT / left).read_bytes() == (ROOT / right).read_bytes(), (left, right)
    u = json.loads((ROOT / 'work/YUZE-LU/212/u-native-hardware-lock.json').read_text())
    for name, expected in u['files'].items():
        assert sha(ROOT / name) == expected, name
    return dict(main_files=len(lock['files']), physical_helpers=len(helpers['files']), cfj_frozen_files=len(locked_control()),
                mother_shared_files=len(same), u_hardware_files=len(u['files']),
                instruction_bits=64, upstream_main=lock['upstream_main'])


if __name__ == '__main__':
    print('PASS main64 source', json.dumps(check()))
