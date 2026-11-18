from pathlib import Path
import json,hashlib
p=Path.cwd()
def rows(name):return set((p/name).read_text().splitlines())
a=rows('original-geometry.tsv');b=rows('candidate-geometry.tsv')
removed=sorted(a-b);added=sorted(b-a)
pg=lambda s:s.split('\t')[0]=='PIN' and s.split('\t')[1] in ('VDD','VSS')
signal_removed=[s for s in removed if not pg(s)];signal_added=[s for s in added if not pg(s)]
drivers=[s.split('\t') for s in (p/'drivers.tsv').read_text().splitlines()]
assert len(drivers)==153 and len({s[0] for s in drivers})==153 and all(s[3]=='BUF_X8' for s in drivers)
result=dict(accepted=False,signal_die_macro_pin_geometry_exact=not signal_removed and not signal_added,all_geometry_exact=not removed and not added,selected_outputs=153,selected_outputs_all_BUF_X8=True,removed=removed,added=added,pg_bpin_diff_requires_explicit_review=any(pg(s) for s in removed+added),scope='Original exact overlay CTS die/BPins/all-layer macro pins/transforms and selected X8 read-only check; no timing or physical-rule pass implied.',hashes={str(p/f):hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ('original-geometry.tsv','candidate-geometry.tsv','drivers.tsv')})
(p/'receipt.json').write_text(json.dumps(result,indent=2));assert result['signal_die_macro_pin_geometry_exact'],result
