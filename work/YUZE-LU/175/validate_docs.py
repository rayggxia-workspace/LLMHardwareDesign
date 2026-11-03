"""Read-only validation for Issue175's documentation and rendered diagrams."""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
base = ROOT / 'docs/local-blocks'
manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
errors = []
sha256 = lambda p: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
for item in manifest['local_sources']:
    rev = manifest['baseline_commit'] + ':' + item['path']
    blob = subprocess.check_output(['git', 'rev-parse', rev], cwd=ROOT, text=True).strip()
    blob_bytes = subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=ROOT)
    if (blob != item['git_blob'] or hashlib.sha256(blob_bytes).hexdigest() != item['sha256']
            or sha256(ROOT / item['path']) != item['sha256']):
        errors.append('source mismatch: ' + item['path'])
for item in manifest['artifacts']:
    p = ROOT / item['path']
    if not p.is_file() or sha256(p) != item['sha256']:
        errors.append('artifact missing/stale: ' + item['path'])
for source in (base / 'diagrams').glob('*.mmd'):
    svg = base / 'assets' / (source.stem + '.svg')
    if not svg.is_file():
        errors.append('no rendered SVG: ' + source.name)
        continue
    doc = ET.fromstring(svg.read_bytes())
    if len(doc.attrib.get('viewBox', '').split()) != 4:
        errors.append('invalid SVG viewBox: ' + svg.name)
    if any(x.tag.rsplit('}', 1)[-1] in ('script', 'foreignObject') for x in doc.iter()):
        errors.append('unexpected active/foreign SVG content: ' + svg.name)
if {p.stem for p in (base / 'diagrams').glob('*.mmd')} != {p.stem for p in (base / 'assets').glob('*.svg')}:
    errors.append('diagram/source set mismatch')
paths = manifest['checked_markdown']
for name in paths:
    p = ROOT / name
    for target in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', p.read_text(encoding='utf-8')):
        target = target.strip().strip('<>')
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            continue
        target = unquote(target.split('#', 1)[0])
        if target and not (p.parent / target).is_file():
            errors.append(f'broken local link: {name} -> {target}')
if errors:
    raise SystemExit('\n'.join(errors))
print(f"PASS: {len(manifest['local_sources'])} fixed sources; {len(manifest['artifacts'])} artifact hashes; "
      f"{len(list((base / 'diagrams').glob('*.mmd')))} Mermaid/SVG pairs; {len(paths)} Markdown link sets.")
print('Scope: documentation only; no RTL, numeric quality or physical qualification implied.')
