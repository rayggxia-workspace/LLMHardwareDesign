"""Independent local audit of the Issue 16 frozen ordinary LEF exports.

Uses only Python standard library. Does not import or execute project source.
The small, fail-closed grammar below is for the actual three captured files,
not a general LEF parser. Every nonblank source line must be consumed.
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from decimal import Decimal

HERE = Path(__file__).resolve().parent
SNAP = Path('D:/Projects/Codex/lef-endpoint-export-20261022/frozen-inputs-01')
REPO = Path('D:/Projects/LLMHardwareDesign-lef')
RUN = REPO / 'project/experiments/macro_endpoints/local_runs/issue-16-run01'
COMMIT = '23040b0459cd32297b6562e22f48af5ae812ed25'
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
failures = []
checks = collections.Counter()


def expect(condition, label, details=None):
    checks[label.split(':')[0]] += 1
    if not condition:
        failures.append({'check': label, 'details': details})


def equal(actual, expected, label):
    """Compare nested values, retaining exact decimal source strings and order."""
    if type(actual) is not type(expected):
        expect(False, label, {'actual': str(actual)[:300], 'expected': str(expected)[:300]})
    elif isinstance(expected, dict):
        expect(actual.keys() == expected.keys(), label + ':keys',
               {'actual': list(actual), 'expected': list(expected)})
        for key in expected.keys() & actual.keys():
            equal(actual[key], expected[key], label + ':' + key)
    elif isinstance(expected, list):
        expect(len(actual) == len(expected), label + ':length', [len(actual), len(expected)])
        for i, (av, ev) in enumerate(zip(actual, expected)):
            equal(av, ev, label + ':' + str(i))
    else:
        expect(actual == expected, label, {'actual': actual, 'expected': expected})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


class RawLines:
    def __init__(self, path):
        self.path = path
        self.data = path.read_bytes()
        self.all_lines = self.data.decode('ascii').splitlines()
        self.lines = [(i, s.strip()) for i, s in enumerate(self.all_lines, 1) if s.strip()]
        self.i = 0
        self.keywords = collections.Counter(s.split()[0] for _, s in self.lines)

    def peek(self):
        return self.lines[self.i][1] if self.i < len(self.lines) else None

    def take(self, pattern):
        if self.i >= len(self.lines):
            raise ValueError(f'{self.path.name}: unexpected EOF, wanted {pattern}')
        no, line = self.lines[self.i]
        match = re.fullmatch(pattern, line)
        if match is None:
            raise ValueError(f'{self.path.name}:{no}: unexpected {line!r}, wanted {pattern}')
        self.i += 1
        return no, match.groups()


def independent_lef(path):
    s = RawLines(path)
    _, (version,) = s.take(r'VERSION\s+(\S+)\s+;')
    _, (bus,) = s.take(r'BUSBITCHARS\s+"([^"]+)"\s+;')
    _, (divider,) = s.take(r'DIVIDERCHAR\s+"([^"]+)"\s+;')
    s.take(r'UNITS')
    _, (dbu_text,) = s.take(r'DATABASE\s+MICRONS\s+(\d+)\s+;')
    s.take(r'END\s+UNITS')
    dbu = int(dbu_text)
    expect(dbu == 2000, 'raw:dbu', dbu)

    def exact_dbu(values):
        converted = []
        for text in values:
            val = Decimal(text)
            assert val.is_finite()
            scaled = val * dbu
            expect(scaled == scaled.to_integral_value(), 'raw:integral_dbu', text)
            converted.append(int(scaled))
        return converted

    macro_line, (name,) = s.take(r'MACRO\s+(\S+)')
    foreign_line, (foreign_name, fx, fy) = s.take(r'FOREIGN\s+(\S+)\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+;')
    s.take(r'CLASS\s+BLOCK\s+;')
    _, size = s.take(r'SIZE\s+(' + NUMBER + r')\s+BY\s+(' + NUMBER + r')\s+;')
    size = list(size)
    width, height = exact_dbu(size)
    expect(width > 0 and height > 0, 'raw:positive_size')

    def region(kind, index):
        no, _ = s.take(kind)
        layers, rects, current = [], [], None
        while s.peek() != 'END':
            line = s.peek()
            if line is not None and line.startswith('LAYER '):
                layer_line, (current,) = s.take(r'LAYER\s+(\S+)\s+;')
                layers.append({'name': current, 'line': layer_line})
            else:
                rect_line, values = s.take(r'RECT\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+;')
                expect(current is not None, 'raw:rectangle_has_layer', rect_line)
                values = list(values)
                coords = exact_dbu(values)
                x1, y1, x2, y2 = coords
                expect(0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height,
                       'raw:rectangle_inside_positive_bbox', [path.name, rect_line, coords])
                rects.append({'layer': current, 'rect_um': values, 'rect_dbu': coords, 'line': rect_line})
        s.take(r'END')
        expect(bool(layers) and bool(rects), 'raw:nonempty_region', [kind, no])
        return {'index': index, 'line': no, 'class': None, 'layer_declarations': layers, 'rects': rects}

    pins, names = [], set()
    while s.peek() is not None and s.peek().startswith('PIN '):
        line, (pinname,) = s.take(r'PIN\s+(\S+)')
        expect(pinname not in names, 'raw:unique_pin', pinname)
        expect('\\' not in pinname and '"' not in pinname, 'raw:simple_literal_pin_name', pinname)
        names.add(pinname)
        _, (direction,) = s.take(r'DIRECTION\s+(INPUT|OUTPUT|INOUT)\s+;')
        _, (use,) = s.take(r'USE\s+(SIGNAL|POWER|GROUND|CLOCK)\s+;')
        ports = []
        while s.peek() == 'PORT':
            ports.append(region('PORT', len(ports)))
        expect(bool(ports), 'raw:nonempty_pin', pinname)
        s.take(r'END\s+' + re.escape(pinname))
        pins.append({'name': pinname, 'line': line, 'direction': direction,
                     'output_tristate': False, 'use': use, 'ports': ports})
    obs = []
    while s.peek() == 'OBS':
        obs.append(region('OBS', len(obs)))
    s.take(r'END\s+' + re.escape(name))
    s.take(r'END\s+LIBRARY')
    expect(s.i == len(s.lines), 'raw:all_nonblank_lines_consumed', path.name)
    expect(s.keywords['PIN'] == len(pins), 'raw:pin_keyword_count', path.name)
    expect(s.keywords['PORT'] == sum(len(p['ports']) for p in pins), 'raw:port_keyword_count', path.name)
    expect(s.keywords['RECT'] == sum(len(g['rects']) for p in pins for g in p['ports']) + sum(len(g['rects']) for g in obs), 'raw:rect_keyword_count', path.name)
    expect(s.keywords['LAYER'] == sum(len(g['layer_declarations']) for p in pins for g in p['ports']) + sum(len(g['layer_declarations']) for g in obs), 'raw:layer_keyword_count', path.name)
    model = {
        'profile': 'lef58-single-macro-rect-v1', 'source_name': path.name,
        'header': {'version': version, 'dbu_per_micron': dbu, 'busbitchars': bus, 'dividerchar': divider},
        'end_library_explicit': True,
        'macro': {'name': name, 'line': macro_line, 'class': 'BLOCK',
                  'origin_um': None, 'origin_dbu': None, 'origin_explicit': False,
                  'size_um': size, 'size_dbu': [width, height], 'symmetry': None,
                  'foreign': [{'name': foreign_name, 'point_um': [fx, fy],
                               'point_dbu': exact_dbu([fx, fy]), 'orientation': None,
                               'line': foreign_line, 'tokens': [foreign_name, fx, fy]}],
                  'pins': pins, 'obstructions': obs, 'bbox_check': 'raw_size_box'},
        'diagnostics': [], 'source_sha256': sha(s.data),
    }
    coverage = {'lines_including_blank': len(s.all_lines), 'nonblank_lines_consumed': s.i,
                'leading_keyword_counts': dict(s.keywords), 'ascii': True,
                'carriage_returns': s.data.count(b'\r'), 'bytes': len(s.data), 'sha256': sha(s.data)}
    return model, coverage


def csv_rows(models):
    pin_rows, obs_rows = [], []
    for cid, lef in models.items():
        m = lef['macro']
        for pin in m['pins']:
            for port in pin['ports']:
                for ri, r in enumerate(port['rects']):
                    row = [cid, m['name'], pin['name'], pin['direction'], pin['use'], port['index'], ri, r['layer'], *r['rect_um'], *r['rect_dbu'], r['line']]
                    pin_rows.append([str(x) for x in row])
        for obs in m['obstructions']:
            for ri, r in enumerate(obs['rects']):
                row = [cid, m['name'], obs['index'], ri, r['layer'], *r['rect_um'], *r['rect_dbu'], r['line']]
                obs_rows.append([str(x) for x in row])
    return pin_rows, obs_rows


def derived_summary(lef):
    m = lef['macro']
    pins = m['pins']
    signal = [p for p in pins if p['use'] == 'SIGNAL']
    layers, touches = collections.Counter(), collections.Counter()
    width, height = m['size_dbu']
    for pin in signal:
        pin_layers, pin_touches = set(), set()
        for port in pin['ports']:
            for rect in port['rects']:
                pin_layers.add(rect['layer'])
                x1, y1, x2, y2 = rect['rect_dbu']
                for touched, side in [(x1 == 0, 'left'), (y1 == 0, 'bottom'), (x2 == width, 'right'), (y2 == height, 'top')]:
                    if touched:
                        pin_touches.add(side)
        layers.update(pin_layers)
        touches.update(pin_touches)
    return {
        'macro': m['name'], 'size_um': m['size_um'], 'size_dbu': m['size_dbu'],
        'dbu_per_micron': lef['header']['dbu_per_micron'], 'origin_explicit': False,
        'origin_um': None, 'symmetry': None, 'qualified_hard_macro': False,
        'total_pins': len(pins), 'pins_by_direction': dict(collections.Counter(p['direction'] for p in pins)),
        'pins_by_declared_use': dict(collections.Counter(p['use'] for p in pins)),
        'signal_pins': len(signal), 'pin_ports': sum(len(p['ports']) for p in pins),
        'pin_rectangles': sum(len(g['rects']) for p in pins for g in p['ports']),
        'obstruction_groups': len(m['obstructions']),
        'obstruction_rectangles': sum(len(g['rects']) for g in m['obstructions']),
        'signal_pins_by_layer': dict(layers), 'signal_pin_boundary_touches': dict(touches),
        'boundary_touch_note': 'Raw geometry only; a pin can touch several sides. No legal access conclusion.',
        'diagnostics': []}


def main():
    capture, inputs = read_json(SNAP / 'capture.json'), read_json(SNAP / 'inputs.json')
    manifest, inventory, summary = [read_json(RUN / name) for name in ['manifest.json', 'inventory.json', 'summary.json']]
    all_file_hashes = {}
    for directory, prefix in [(SNAP, 'snapshot'), (RUN, 'export')]:
        for p in sorted(directory.iterdir()):
            if p.is_file():
                data = p.read_bytes()
                all_file_hashes[prefix + '/' + p.name] = {'bytes': len(data), 'sha256': sha(data)}
    expect(len(all_file_hashes) == 10, 'hash:exact_ten_artifact_files', list(all_file_hashes))
    for record, directory, prefix in [(capture, SNAP, 'snapshot'), (manifest, RUN, 'export')]:
        for name, info in record['files'].items():
            equal(all_file_hashes[prefix + '/' + name], info, 'hash:index:' + prefix + ':' + name)
    capture_sha = sha((SNAP / 'capture.json').read_bytes())
    for obj, key in [(manifest, 'input_capture_manifest_sha256'), (inventory, 'capture_manifest_sha256'), (summary, 'capture_manifest_sha256')]:
        equal(obj[key], capture_sha, 'hash:capture_manifest_link')
    equal(capture['config_sha256'], sha((SNAP / 'inputs.json').read_bytes()), 'hash:config')
    equal(inputs['upstream'], capture['upstream'], 'provenance:upstream_capture')
    equal(inputs['upstream'], inventory['upstream'], 'provenance:upstream_inventory')
    equal(inputs['input_version'], inventory['input_version'], 'provenance:input_version')
    source_hashes = {}
    git_env = os.environ.copy()
    git_env['GIT_NO_LAZY_FETCH'] = '1'
    for obj in [capture, manifest]:
        equal(obj['provenance']['source_commit'], COMMIT, 'provenance:source_commit')
        equal(obj['provenance']['source_dirty'], False, 'provenance:recorded_clean')
        for relative, expected_sha in obj['provenance']['source_sha256'].items():
            data = (REPO / relative).read_bytes()
            committed = subprocess.run(['git', '-C', str(REPO), 'cat-file', 'blob', COMMIT + ':' + relative],
                                       check=True, capture_output=True, env=git_env).stdout
            equal(sha(data), expected_sha, 'source:local_sha:' + relative)
            equal(sha(committed), expected_sha, 'source:committed_blob_sha:' + relative)
            source_hashes[relative] = {'bytes': len(data), 'sha256': sha(data), 'matches_pinned_git_blob': True}
    equal((REPO / 'project/experiments/macro_endpoints/inputs.json').read_bytes(),
          (SNAP / 'inputs.json').read_bytes(), 'source:frozen_config_bytes')

    models, coverages, per_macro = {}, {}, {}
    obs_by_id = {o['id']: o for o in capture['observations']}
    expect(set(obs_by_id) == set(inventory['macros']), 'capture:observation_ids')
    for config in inputs['files']:
        cid = config['id']
        lef, coverage = independent_lef(SNAP / (cid + '.lef'))
        models[cid], coverages[cid] = lef, coverage
        equal(lef['macro']['name'], config['macro_name'], 'raw:expected_macro_name:' + cid)
        equal(inventory['macros'][cid], {'source_file': cid + '.lef', 'source_sha256': coverage['sha256'],
                                       'qualified_hard_macro': False, 'lef': lef}, 'inventory:' + cid)
        observation = obs_by_id[cid]
        equal(observation['sha256'], coverage['sha256'], 'capture:observed_sha:' + cid)
        equal(observation['bytes'], coverage['bytes'], 'capture:observed_bytes:' + cid)
        equal(observation['stat_before'], observation['stat_after'], 'capture:recorded_stat_stability:' + cid)
        equal(observation['stat_before'][2], coverage['bytes'], 'capture:stat_size:' + cid)
        equal(observation['requested_path'], inputs['allowed_root'] + '/' + config['relative_path'], 'capture:allowlisted_path:' + cid)
        equal(observation['resolved_path'], observation['requested_path'], 'capture:recorded_resolved_path:' + cid)
        derived = derived_summary(lef)
        equal(summary['macros'][cid], derived, 'summary:' + cid)
        pg = [p for p in lef['macro']['pins'] if p['use'] in {'POWER', 'GROUND'}]
        equal([(p['name'], p['direction'], p['use']) for p in pg],
              [('VDD', 'INOUT', 'POWER'), ('VSS', 'INOUT', 'GROUND')], 'raw:pg_identity:' + cid)
        per_macro[cid] = {**derived, 'pg': [{'name': p['name'], 'declared_use': p['use'],
                                          'ports': len(p['ports']),
                                          'rectangles': sum(len(g['rects']) for g in p['ports']),
                                          'layers': sorted({r['layer'] for g in p['ports'] for r in g['rects']})}
                                         for p in pg], 'source_coverage': coverage}

    pin_rows, obs_rows = csv_rows(models)
    pin_header = ['candidate','macro','pin_raw_name','direction','declared_use','port_index','rect_index','layer','xlo_um','ylo_um','xhi_um','yhi_um','xlo_dbu','ylo_dbu','xhi_dbu','yhi_dbu','source_line']
    obs_header = ['candidate','macro','obs_index','rect_index','layer','xlo_um','ylo_um','xhi_um','yhi_um','xlo_dbu','ylo_dbu','xhi_dbu','yhi_dbu','source_line']
    for name, expected in [('pin-rectangles.csv', [pin_header, *pin_rows]), ('obs-rectangles.csv', [obs_header, *obs_rows])]:
        with (RUN / name).open(encoding='utf-8', newline='') as f:
            equal(list(csv.reader(f)), expected, 'csv:' + name)
    for key, value in [('total_pins', sum(m['total_pins'] for m in per_macro.values())),
                       ('signal_pins', sum(m['signal_pins'] for m in per_macro.values())),
                       ('pin_rectangle_rows', len(pin_rows)), ('obstruction_rectangle_rows', len(obs_rows))]:
        equal(summary[key], value, 'summary:total:' + key)
    expect(summary['unverified'] == ['DEF placement/orientation', 'RTL/Lib pin and bit matching',
           'legal via/spacing/enclosure/OBS access', 'minimum_period/complete arcs/driver-load',
           'PG connectivity', 'source-to-physical equivalence', 'PPA/physical H2'], 'scope:explicit_unverified')
    expect(all(config['upstream_expected_sha256'] is None and config['qualified_hard_macro'] is False for config in inputs['files']), 'scope:no_invented_upstream_hash_or_qualification')
    expect(all(inputs['upstream'][k] is None for k in ['source_rtl_commits','openroad_version','orfs_version','image_sha256']), 'scope:missing_versions_retained')
    report = {
        'audit_schema': 1, 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'pass' if not failures else 'fail', 'source_commit': COMMIT,
        'snapshot': str(SNAP), 'export_run': str(RUN),
        'audit_script_sha256': sha(Path(__file__).read_bytes()), 'python': sys.version,
        'independence': 'Standard library only; no project modules imported, no project code executed. Separate full-line reader with anchored syntax; every nonblank line consumed, raw decimal strings retained, Decimal-to-integer DBU recomputed.',
        'network_or_server_access': False, 'project_files_written': False,
        'checks': dict(checks), 'total_checked_leaves_and_conditions': sum(checks.values()),
        'failures': failures, 'artifact_files': all_file_hashes, 'source_files': source_hashes,
        'totals': {'lef_lines': sum(c['lines_including_blank'] for c in coverages.values()),
                   'nonblank_lef_lines': sum(c['nonblank_lines_consumed'] for c in coverages.values()),
                   'pins': sum(m['total_pins'] for m in per_macro.values()),
                   'signal_pins': sum(m['signal_pins'] for m in per_macro.values()),
                   'ports': sum(m['pin_ports'] for m in per_macro.values()),
                   'pin_rectangles': len(pin_rows), 'obs_rectangles': len(obs_rows),
                   'power_ground_pins': sum(len(m['pg']) for m in per_macro.values())},
        'macros': per_macro,
        'limitations': ['This audit verifies captured local bytes and export correctness only; recorded remote stat stability cannot be independently retraced without another server read.',
                        'Pinned producer indexes lack per-file expected SHA-256/bytes and source RTL/tool/image versions; capture hashes are measured snapshot identities, not an upstream expected-hash comparison.',
                        'Recorded clean=true is corroborated by every indexed source hash matching pinned Git blobs, but historical whole-worktree cleanliness cannot be reconstructed from local artifacts.',
                        'No DEF placement, RTL/Lib matching, legal access/spacing/via, qualified hard macro, complete timing/load, PG connectivity, equivalence, calibrated PPA, H2, or manufacturing conclusion.'],
    }
    output = HERE / 'audit.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    sums = ''.join(sha(p.read_bytes()) + '  ' + p.name + '\n' for p in [Path(__file__), output])
    (HERE / 'SHA256SUMS').write_text(sums, encoding='ascii', newline='\n')
    print(json.dumps({'status': report['status'], 'failures': len(failures), 'checks': sum(checks.values()),
                      'totals': report['totals'], 'audit': str(output), 'audit_sha256': sha(output.read_bytes())}))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
