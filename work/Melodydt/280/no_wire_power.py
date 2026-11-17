"""Repeat accepted activity on the same cell network with no wire RC loaded.

Keep the existing mapped cells and their pin capacitances. No placement, routing,
read_spef, or estimate_parasitics is executed. Existing CTS/buffer cells remain
explicitly part of the cell-network reference; this is not a new synthesis result.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess


def digest(path):
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def cases(root, family):
    patterns = {
        'm': ['m-baseline-power/idle-38809728/power/receipt.json',
              'm-baseline-power/m-38809662/*/receipt.json'],
        'control': ['lc-fetch-300-hold/fetch-38815974/*/power/receipt.json',
                    'pm-quiet/quiet-38815532/*/power/receipt.json',
                    'pm-runtime/pm-live-power-38813039/*/power/receipt.json',
                    'pm-arrays/array-38795055/*/receipt.json'],
        'write_u': ['u-component-power/power-3879528[234]/*/receipt.json',
                    'real-span-power/span-38795265/*/power/receipt.json',
                    'pm-real-length/pm-38795749/*/power/receipt.json'],
        'sram': ['sram-macro-power/sram-38814341/s-p/*/receipt.json'],
    }
    paths = sorted({p for pattern in patterns[family] for p in root.glob(pattern)})
    if not paths:
        raise ValueError('no accepted cases for ' + family)
    return paths


def measure(root, out, receipt):
    original = json.loads(receipt.read_bytes())
    timing = original.get('timing', {'window_ps': original.get('time_ps'),
                                     'clock_hz': 300000000})
    if not timing['window_ps'] or timing['clock_hz'] != 300000000:
        raise ValueError('invalid accepted timing: ' + str(receipt))
    original_power = original.get('power_w')
    if original_power is None:
        original_power = {k: original['power']['total'][k + '_w']
                          for k in ('internal', 'switching', 'leakage', 'total')}
    script = receipt.with_name('power.tcl')
    source = script.read_text()
    # Execute the exact recorded case, changing only the external wire-RC read.
    if len(re.findall(r'(?m)^read_spef .*$', source)) != 1:
        raise ValueError('expected one parasitic read: ' + str(script))
    stripped = re.sub(r'(?m)^read_spef .*\n?', '', source)
    if 'estimate_parasitics' in stripped or 'read_spef' in stripped:
        raise ValueError('wire RC still present')
    name = '__'.join(receipt.relative_to(root).parts[:-1])
    target = out / name
    target.mkdir()
    references = re.findall(r'(?m)^read_(?:liberty|db|sdc)\s+\{([^}]+)\}', source)
    references += re.findall(r'(?m)^read_vcd.*?\{([^}]+\.vcd)\}', source)
    inputs = {}
    for item in references:
        path = Path(item)
        if not path.is_absolute():
            # Older M receipts ran from the parent of the power directory.
            path = receipt.parent.parent / path
        if not path.is_file():
            raise ValueError('recorded input absent: ' + str(path))
        actual = digest(path)
        recorded = original.get('input_sha256', {}).get(item)
        if recorded is not None and recorded != actual:
            raise ValueError('accepted input changed: ' + str(path))
        inputs[str(path)] = actual
        stripped = stripped.replace('{' + item + '}', '{' + str(path) + '}')
    if not references:
        raise ValueError('no recorded power inputs')
    (target / 'power.tcl').write_text(stripped)
    with (target / 'power.log').open('w') as log:
        subprocess.run(['openroad', '-no_init', '-threads', '3', '-exit', str(target / 'power.tcl')],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    text = (target / 'power.log').read_text()
    rows = re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)', text)
    annotations = re.findall(r'Annotated (\d+) pin activities\.', text)
    if len(rows) != 1 or len(annotations) != 1 or re.search(r'(?m)^(Error:|\[ERROR)', text):
        raise ValueError('invalid power output: ' + str(target))
    if int(annotations[0]) != original['annotated']:
        raise ValueError('activity coverage changed: ' + str(target))
    power = dict(zip(('internal', 'switching', 'leakage', 'total'), map(float, rows[0])))
    if not 0 <= power['leakage'] <= power['total']:
        raise ValueError('invalid power values')
    result = {'source_receipt':str(receipt), 'source_receipt_sha256':digest(receipt),
              'original_power_w':original_power, 'power_w':power,
              'energy_nj':power['total'] * timing['window_ps'] / 1000,
              'timing':timing, 'annotated':int(annotations[0]),
              'input_sha256':inputs, 'wire_parasitics_loaded':False,
              'cell_composition':'existing implementation including its buffers; not resynthesized',
              'activity':'same accepted VCD, including original port-propagation limits',
              'power_log_sha256':digest(target / 'power.log')}
    (target / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print('NO_WIRE_CASE_PASS', name, flush=True)
    return name, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('family', choices=('m','control','write_u','sram'))
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    paths = cases(args.root, args.family)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = dict(pool.map(lambda p: measure(args.root, args.output, p), paths))
    (args.output / 'calibration.json').write_text(json.dumps({'family':args.family,
        'wire_parasitics_loaded':False, 'windows':results}, indent=2) + '\n')
    print('NO_WIRE_CALIBRATION_PASS', args.family, len(results), flush=True)


if __name__ == '__main__':
    main()
