"""Fetch explicitly pinned public-to-this-repository source inputs using gh.

Only file content is retained; signed download URLs and API credentials are
never printed or written. This is a dependency fetcher, not a Git checkout.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time


REPO = 'rayggxia-workspace/LLMHardwareDesign'
PINS = {
    'pu': ('f5fb8115ece2e125edda6c223f0538ed52c941c6', [
        'project/experiments/pu_leaf_base/contract.json',
        'project/experiments/pu_leaf_base/controlled.py',
        'project/experiments/pu_leaf_base/control_replay.py',
        'project/experiments/pu_leaf_base/smoke.sh',
        'project/experiments/pu_leaf_base/tb_pu_p_group.sv',
        'project/experiments/pu_leaf_base/tb_pu_u_group.sv',
        'project/rtl/pu_leaf_base/pu_p_group.sv',
        'project/rtl/pu_leaf_base/pu_u_group.sv',
        'project/rtl/pu_leaf_base/ucf_s_compute_client.sv']),
    'cfj': ('2729e10550c156550851a6e8a6b390dd32c73e9e', [
        'project/rtl/block_cfj_v1/block_cfj_cf.sv',
        'project/rtl/block_cfj_v1/block_cfj_j.sv',
        'project/experiments/cfj_leaf_base/group_top.py']),
    'bench': ('cc6bf8ed98b8489cafc59305b5def5351e662c11', [
        'project/experiments/qwen_layer_dma/native_engines.hpp',
        'project/experiments/qwen_layer_dma/native_memory.hpp',
        'project/experiments/qwen_layer_dma/prepare.py',
        'project/experiments/qwen_layer_dma/build.sbatch',
        'project/experiments/seven_model_system_bench/run_systemc.py',
        'project/experiments/seven_model_system_bench/offchip_build.sbatch',
        'project/experiments/seven_model_system_bench/README.md',
        'docs/experiments/issue-197-full-model-rtl-gaps.md']),
    'dma': ('24e20d13a71cf65f721a182451308f1ad01ebaec', [
        'project/rtl/hbm_feed/hbm_group_dma.sv',
        'project/rtl/hbm_feed/hbm_s_endpoint.sv',
        'project/experiments/hbm_feed/hbm_dma_system.sv',
        'project/experiments/hbm_feed/test_dma.cpp',
        'docs/HBM_GROUP_DMA.md'])}


def api(path):
    for attempt in range(3):
        try:
            return json.loads(subprocess.run(['gh', 'api', path], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=True, timeout=40).stdout)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def fetch(out, group, commit, name, expected):
    target = out / group / name
    if target.exists():
        data = target.read_bytes()
    else:
        entry = api(f'repos/{REPO}/contents/{name}?ref={commit}')
        if entry.get('encoding') != 'base64':
            raise ValueError(f'Unsupported content response: {name}')
        data = base64.b64decode(entry['content'])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if git_blob != expected:
        raise ValueError('pinned Git blob differs: ' + name)
    return {'group': group, 'commit': commit, 'path': name,
            'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': git_blob,
            'bytes': len(data)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    work = []
    for group, (commit, names) in PINS.items():
        tree = api(f'repos/{REPO}/git/trees/{commit}?recursive=1')
        if tree.get('truncated'):
            raise ValueError('source tree was truncated')
        blobs = {v['path']: v['sha'] for v in tree['tree'] if v['type'] == 'blob'}
        work.extend((group, commit, name, blobs[name]) for name in names)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda x: fetch(args.output, *x), work))
    rows.sort(key=lambda x: (x['group'], x['path']))
    (args.output / 'sources.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps({'files': len(rows), 'bytes': sum(r['bytes'] for r in rows)}))


if __name__ == '__main__':
    main()
