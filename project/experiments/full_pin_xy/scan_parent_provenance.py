"""Read completed parent/union/top metadata only; never modifies source runs."""
from pathlib import Path
import json,datetime
ROOT=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')
RUNS=Path('/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs')
cfg=json.loads((ROOT/'inputs/sources.json').read_text());wanted={s['expected_sha256']:c for c,s in cfg['physical_blocks'].items()}
records=[];scanned=0;partial=0
def leaves(v,prefix=''):
    if isinstance(v,dict):
        for k,x in v.items():yield from leaves(x,prefix+'/'+k)
    elif isinstance(v,list):
        for n,x in enumerate(v):yield from leaves(x,prefix+'/'+str(n))
    elif isinstance(v,str):yield prefix,v
for p in sorted(RUNS.glob('*/execution.json')):
    name=p.parent.name.lower()
    if not any(k in name for k in ['parent','union','top']):continue
    try:j=json.loads(p.read_text())
    except (ValueError,OSError):partial+=1;continue
    if not j.get('completed_utc') and not j.get('finished_utc'):partial+=1;continue
    scanned+=1;flat=list(leaves(j));matches=[{'case':wanted[value],'metadata_field':key,'source_hash':value} for key,value in flat if value in wanted]
    odbs=[{'field':key,'path':value} for key,value in flat if value.endswith('.odb')][:30]
    records.append({'run':name,'metadata':str(p),'status':j.get('status'),'exact_leaf_odb_hash_matches':matches,'odb_path_hints':odbs})
out=ROOT/'parent_provenance';out.mkdir(exist_ok=True);dest=out/'scan-r01.json'
with dest.open('x') as f:json.dump({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metadata_runs_scanned':scanned,'partial_or_unfinished_skipped':partial,
  'scope':'Only completed Issue55 run metadata named parent/union/top, matching original leaf ODB SHA. LEF-only derivation and actual geometry still require separate trace. No original parent handoff/layer sequence established by this scan.',
  'records':records},f,indent=2)
print('PARENT_PROVENANCE_METADATA_SCAN',scanned,'completed; exact source matches',sum(bool(r['exact_leaf_odb_hash_matches']) for r in records),'handoff mapping NOT verified')
