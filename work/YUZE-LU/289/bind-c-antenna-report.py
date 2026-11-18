"""Bind a completed focused antenna report to its unchanged inputs."""
import hashlib
import json
import sys
from pathlib import Path

directory = Path(sys.argv[1]).resolve()
before = directory / 'inputs-before.sha256'
after = directory / 'inputs-after.sha256'
assert before.read_bytes() == after.read_bytes()
hashes = {}
for line in before.read_text().splitlines():
    expected, name = line.split(maxsplit=1)
    path = Path(name)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    assert digest.hexdigest() == expected, path
    hashes[path] = expected

receipt = json.loads((directory / 'receipt.json').read_text())
report = directory / 'antenna.lyrdb'
report_hash = hashlib.sha256(report.read_bytes()).hexdigest()
assert report_hash == receipt['antenna']['report_sha256']
gds = [path for path in hashes if path.name == '6_final.gds']
assert len(gds) == 1
deck = directory / 'antenna-only-v2.lydrc'
binding = dict(completed=True, accepted=False, gds_path=str(gds[0]),
               gds_sha256=hashes[gds[0]], report_path=str(report),
               report_sha256=report_hash, deck_path=str(deck),
               deck_sha256=hashes[deck], input_manifest_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),
               source_scope=receipt['scope'])
output = directory / 'antenna-binding.json'
assert not output.exists()
output.write_text(json.dumps(binding, indent=2))
print(output)
