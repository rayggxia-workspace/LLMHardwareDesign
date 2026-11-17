"""Verify the small published six-model receipts without copying model weights.

This checks published evidence and repeats component integration. It does not
rerun the full numerical model, FP32 reference, RTL, or physical implementation.
"""

import hashlib
import json
from math import isclose
from pathlib import Path

from six_model_tlm_power import calibration, integrate


HERE = Path(__file__).resolve().parent
MODELS = ('llama', 'granite', 'phi', 'falcon', 'gemma', 'qwen35')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(model, coefficients):
    root = HERE / 'six-model-results' / model
    manifest = {}
    for line in (root / 'results.sha256').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        manifest[relative[2:] if relative.startswith('./') else relative] = digest
    checked = 0
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if not path.is_file() or relative.parts[0] == 'power' or relative.as_posix() == 'results.sha256':
            continue
        require(sha(path) == manifest.get(relative.as_posix()), 'replay manifest: ' + str(path))
        checked += 1
    require(checked == 17, model + ': incomplete small receipt set')
    for stage in ('prefill', 'decode'):
        acceptance = json.loads((root / stage / 'acceptance.json').read_bytes())
        for field in ('passed', 'complete_result_equal', 'numerical_files_equal',
                      'ddr_terminal_reconciled', 'sram_observer_reconciled'):
            require(acceptance.get(field) is True, model + '/' + stage + ': ' + field)
    result_path = HERE / (model + '_tlm_power_v1.json')
    raw = result_path.read_bytes()
    require(raw == (root / 'power' / result_path.name).read_bytes(), model + ': server result differs')
    digest = sha(result_path)
    power_manifest = (root / 'power' / 'results.sha256').read_text().splitlines()
    require(any(line.startswith(digest + '  ') and line.endswith('/' + result_path.name)
                for line in power_manifest), model + ': power manifest differs')
    computed = integrate(model, root, coefficients)
    require(raw == (json.dumps(computed, indent=2, allow_nan=False) + '\n').encode(),
            model + ': local integration bytes differ')
    for window, row in computed['windows'].items():
        label = model + '/' + window
        for edge in (0, 1):
            total = row['covered_subtotal']
            require(isclose(sum(c['energy_nj_per_window'][edge] for c in row['components'].values()),
                            total['energy_nj_per_window'][edge], rel_tol=1e-12), label + ': component sum')
            require(isclose(total['average_power_w'][edge] * row['elapsed_ps'] / 1e9 / row['tokens'],
                            total['energy_mj_per_token'][edge], rel_tol=1e-12), label + ': units')
            for metric in ('energy_nj_per_window', 'energy_mj_per_token', 'average_power_w'):
                require(isclose(row['covered_on_chip_subtotal'][metric][edge]
                                + row['components']['ddr_devices'][metric][edge],
                                total[metric][edge], rel_tol=1e-12), label + ': chip + DDR')
    return {'model': model, 'passed': True, 'verified_small_replay_files': checked,
            'accepted_stages': ['prefill', 'decode'], 'local_server_integration_bytes_equal': True,
            'result_sha256': digest}


def main():
    coefficients = calibration(HERE)
    result = {'scope': 'Published receipts and component reintegration; no full-model or FP32 rerun',
              'models': [verify(model, coefficients) for model in MODELS]}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
