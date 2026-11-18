"""Compare every original full-deck marker to the frozen focused diagnostics."""
from pathlib import Path
import collections
import hashlib
import json
import xml.etree.ElementTree as ET

p = Path(__file__).resolve().parent
f = p / 'full-C-v27-joint-e20-h30'
focused = p / 'C-v27-physical/focused-receipt.json'
sha = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
assert (f / 'inputs-before.sha256').read_bytes() == (f / 'inputs-after.sha256').read_bytes()
manifest = (f / 'inputs-before.sha256').read_text()
assert 'cc3f80b43858fb882d9d2d391edfd73b40921f3ccb221c6c15a2c69ea6702a58' in manifest
assert '4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147' in manifest
receipt = json.loads((f / 'receipt.json').read_text())
assert sha(f / 'full.lyrdb') == receipt['report_sha256']
r = json.loads(focused.read_text())

def key(category, cell, values):
    return category.strip("'\""), cell, tuple(sorted(values))

actual = collections.Counter(
    key(x.findtext('category'), x.findtext('cell'), [v.text for v in x.findall('values/value')])
    for x in ET.parse(f / 'full.lyrdb').findall('.//items/item')
)
expected = collections.Counter(
    key(x['category'], x['cell'], x['values'])
    for kind in ('upper', 'antenna') for x in r[kind]['markers']
)
assert not (expected - actual), 'Focused marker missing from full deck'
extra = actual - expected
assert sum(extra.values()) == 1
assert next(iter(extra))[:2] == ('METAL1.5', 'OAI221_X4')
assert sum(actual.values()) == receipt['full_deck_items'] == 42
result = dict(
    diagnostic_comparison_passed=True, backend_accepted=False,
    scope='Frozen failing v27 only. Exact category/cell/value multiset comparison; no physical waiver or final v28 acceptance.',
    full_markers=42, exact_focused_markers=41, focused_upper=24, focused_antenna=17,
    full_only=[dict(category=k[0], cell=k[1], values=list(k[2]), count=n) for k, n in extra.items()],
    source_sha256={str(q.relative_to(p)): sha(q) for q in (
        focused, f / 'receipt.json', f / 'full.lyrdb',
        f / 'inputs-before.sha256', f / 'inputs-after.sha256', Path(__file__).resolve(),
    )},
)
(f / 'focused-comparison.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
