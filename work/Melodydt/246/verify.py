import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
index=json.loads((HERE/'index.json').read_text(encoding='utf-8'))
for n,h in index['files_sha256'].items():assert sha(HERE/n)==h,n
for n,h in index['source_sha256'].items():assert sha(ROOT/'project/experiments/sram_capacity_study'/n)==h,n
lock=json.loads((ROOT/'project/experiments/sram_capacity_study/source.json').read_text(encoding='utf-8'))
for n,h in lock['base_functional_sha256'].items():assert sha(ROOT/'project/experiments/p_dma_study'/n)==h,n
rows=json.loads((HERE/'summary.json').read_text());assert len(rows)==28
for r in rows:assert r['scratch_peak']<=r['P_KiB']*1024
for p in (HERE/'results').glob('*.json'):
    raw=json.loads(p.read_text());row=next(r for r in rows if all(r[k]==raw[k] for k in ['workload','profile','variant','P_KiB','P_service_cycles']))
    assert row['tokens_s']==raw['result']['tokens_per_second'] and raw['audit']['passed']
assert index['baseline_16KiB_complete_result_exact'] and index['negative_checks']['passed']
print('PASS: 17 evidence SHA, 4 capacity source SHA, 15 unchanged dependency SHA, 28 summaries and 3 raw cases')
