"""Freeze only relevant result evidence, without modifying other sessions."""
from pathlib import Path
from hashlib import sha256
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE='work/Melodydt/280'
paths=[BASE+'/report-sync/sync06-remote-provenance.json',
       'output/pdf/seven-model-sync06-20261118-r2/frequency-estimates.json',
       'output/pdf/seven-model-sync06-20261118-r2/source-manifest.json',
       'work/Melodydt/293/prefill-energy-300-v3/results.json',
       'work/Melodydt/293/prefill-energy-300-v3/publication-receipt.json']
for model in ('qwen35','falcon'):
    paths.append(BASE+'/'+model+'_tlm_power_v3_arithmetic.json')
    for phase in ('prefill','decode'):
        paths += [BASE+'/closure-v5/'+kind+'/'+model+'-'+phase+'.json' for kind in ('timing-ledger','dma-ledger','special-candidate-ledger')]
        paths.append(BASE+'/closure-v5/deployments/'+model+'-'+phase+'-e32-18/result/acceptance.json')
for model in ('qwen35','falcon-wide'):
    paths += [BASE+'/recurrent-step1/'+model+'-calibration.json',BASE+'/recurrent-step1/results/'+model+'/power/gate-replay-receipt.json']
paths += [BASE+'/recurrent-step1/'+n for n in ('input-bindings.json','signed-graph-audit.json','calibration-tb-check.json','sample-coverage.json','candidate-rollup.json')]
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/BASE/'arithmetic-calibration-results').glob('power-*-calibration.json'))]
dest=HERE/'inputs';assert not dest.exists();dest.mkdir()
locked=json.loads((ROOT/'output/pdf/seven-model-sync06-20261118-r2/source-manifest.json').read_bytes())['files']
manifest={}
for rel in paths:
    raw=(ROOT/rel).read_bytes();h=sha256(raw).hexdigest()
    if rel in locked:assert h==locked[rel]['sha256'],rel
    p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    manifest[rel]={'sha256':h,'bytes':len(raw),'matched_sync06_lock':rel in locked}
(HERE/'input-manifest.json').write_text(json.dumps({'files':manifest,'scope':'new 300 MHz source freeze; no upstream mutation'},indent=2)+'\n')
print('FROZEN',len(manifest))
