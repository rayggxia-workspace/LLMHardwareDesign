"""Clone a previously accepted runner, verify it, and add observation-only hooks."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil


def replace(path, old, new):
    content = path.read_text()
    if content.count(old) != 1:
        raise ValueError('unexpected source anchor: ' + str(path) + ': ' + old)
    path.write_text(content.replace(old, new))


def prepare(source, bundle, output):
    for phase in ('prefill', 'decode'):
        if not json.loads((source / phase / 'acceptance.json').read_text())['passed']:
            raise ValueError('source replay was not accepted')
    hashes = json.loads((source / 'instrumented-source.json').read_text())
    for name, expected in hashes.items():
        if sha256((source / 'runner' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('source runner changed: ' + name)
    output.mkdir()
    runner = output / 'runner'
    shutil.copytree(str(source / 'runner'), str(runner))
    for name in ('qualified-windows.json', 'transfer-verified.json', 'projection_math.so'):
        shutil.copy2(str(source / name), str(output / name))
    shutil.copy2(str(bundle / 'arithmetic_observation.py'), str(runner / 'arithmetic_observation.py'))
    replace(runner / 'run_frozen_model_energy.py',
            'from six_model_observation import ModelObservation',
            'from arithmetic_observation import ArithmeticObservation as ModelObservation')
    rms = runner / 'qwen3_rms.py'
    shifted = 'shifted_format=False' in rms.read_text()
    replace(rms, '        def begin(done):\n',
            '        capture_format = ' + ('shifted_format' if shifted else 'False') + '\n'
            '        def begin(done):\n'
            '            self.arithmetic_observer.rms_begin(self, record, capture_format)\n')
    replace(rms, '                    nonlocal extra\n',
            '                    nonlocal extra\n'
            "                    self.arithmetic_observer.rms_values(self, 'source', i, values)\n")
    replace(rms, '            def apply(i, factor):\n',
            '            def apply(i, factor):\n'
            '                if i == 0:\n'
            '                    self.arithmetic_observer.rms_factor(self, factor, extra)\n')
    replace(rms, '                    done()\n',
            '                    self.arithmetic_observer.rms_end(self)\n                    done()\n')
    replace(rms, '                    def gamma_ready(weights):\n',
            '                    def gamma_ready(weights):\n'
            "                        self.arithmetic_observer.rms_values(self, 'gamma', i, weights)\n")
    replace(rms, '                        self.leaf("e_product_packets", 9, lambda: self.write(\n',
            "                        self.arithmetic_observer.rms_values(self, 'expected', i, result)\n"
            '                        self.leaf("e_product_packets", 9, lambda: self.write(\n')
    manifest = {p.name: sha256(p.read_bytes()).hexdigest() for p in runner.iterdir() if p.is_file()}
    (output / 'instrumented-source.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'capture-provenance.json').write_text(json.dumps(dict(
        source=str(source), original_runner_hashes=hashes,
        source_commit=(source / 'source-commit.txt').read_text().strip(),
        probe_commit=(bundle / 'source-commit.txt').read_text().strip(),
        projection_library_sha256=sha256((output / 'projection_math.so').read_bytes()).hexdigest(),
        sampling='first two complete services per window/site/word-count/epsilon/shift signature'), indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('source', 'bundle', 'output'):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    prepare(args.source, args.bundle, args.output)
