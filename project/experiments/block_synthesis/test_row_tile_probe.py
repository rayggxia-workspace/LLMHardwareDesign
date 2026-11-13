"""Evidence reader must reject incomplete/corrupted passive timing receipts."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from row_tile_probe import analyse


def fixture():
    r, k = 3, 7
    manifest = {'kind': 'native-row-tile-probe-v2', 'sha256': {},
                'cases': [{'id': 0, 'rows': r, 'k': k}], 'groups': [],
                'scope': 'fixture only', 'excluded': []}
    record = {'id': 0, 'rows': r, 'k': k, 'a_fires': 3*r*k,
              'b_fires': 2*k, 'wide_reads': k*(2+3), 'store_acks': 5*r,
              'a_stage_words': 3*r*k, 'b_stage_words': k}
    profiles = []
    for boundary in ('p-command', 'native-m'):
        for op, samples in ((4, 3*k), (10, 3*k), (3, r), (5, 4*r)):
            p = {'boundary': boundary, 'rows': r, 'op': op,
                 'samples': samples, 'min': 2, 'max': 2}
            if boundary == 'p-command':
                p['store'] = int(op in (3,5))
            profiles.append(p)
    for reuse in (0,1):
        profiles.append({'boundary': 'feeder', 'rows': r, 'reuse_b': reuse,
                         'samples': k*(1+reuse), 'min': 4, 'max': 5})
    return manifest, record, profiles


class TestRowTileProbe(unittest.TestCase):
    def run_fixture(self, profiles, *, complete=True):
        manifest, record, _ = fixture()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'manifest.json').write_text(json.dumps(manifest))
            lines = ['ROW_TILE '+json.dumps(record)]
            lines += ['ROW_PROFILE '+json.dumps(p) for p in profiles]
            if complete:
                lines.append('PASS native row tile probe')
            log = root/'simulate.log'
            log.write_text('\n'.join(lines)+'\n')
            with redirect_stdout(io.StringIO()):
                analyse(root, log)
            return json.loads((root/'summary.json').read_text())

    def test_complete_profiles_with_variable_latency_preserved(self):
        profiles = fixture()[2]
        result = self.run_fixture(profiles)
        self.assertEqual(result['passive_profiles'], profiles)
        self.assertEqual(result['passed_cases'], 1)

    def test_missing_duplicate_and_wrong_row_profile_rejected(self):
        profiles = fixture()[2]
        wrong_row = deepcopy(profiles)
        wrong_row[-1]['rows'] = 8
        for bad in (profiles[:-1], profiles+[profiles[0]], wrong_row):
            with self.subTest(bad=bad[-1]), self.assertRaises(ValueError):
                self.run_fixture(bad)

    def test_sample_corruption_or_invalid_latency_rejected(self):
        for field, value in (('samples',22), ('min',0), ('max',1)):
            bad = deepcopy(fixture()[2])
            bad[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_fixture(bad)

    def test_truncated_execution_rejected(self):
        with self.assertRaises(ValueError):
            self.run_fixture(fixture()[2], complete=False)
