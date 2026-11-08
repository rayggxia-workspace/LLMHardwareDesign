"""Recover complete native-only scalar rows; never trust old owner partitions."""
import hashlib
import json
import os
from pathlib import Path

BASE=Path('/public/home/yuzelu/PingyangHuang')
SAMPLE=BASE/'issue-222-validated-mPI4CdbA/job-100246/result'
ATTEMPT=BASE/'issue-222-lower-interface-cWjNWS71'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    out=Path(os.environ['LOWER_OUT']);out.mkdir();rows={};sources=[]
    candidates=[SAMPLE/'without-upper.jsonl',*sorted(ATTEMPT.glob('job-*/result/without-upper.jsonl'))]
    for path in candidates:
        loaded=[];trailing=0
        expected=None
        if path.parent!=SAMPLE:expected=list(map(int,(path.parent/'masters.txt').read_text().split()))
        for no,raw in enumerate(path.open('rb'),1):
            try:r=json.loads(raw)
            except json.JSONDecodeError:
                assert not raw.endswith(b'\n'),'Malformed complete field row';trailing=len(raw);break
            i=r['master'];assert i not in rows and r['net']=='word_'+format(i,'04')
            assert r['total_ff']>0 and r['values'][i][0]==r['total_ff']
            assert abs(sum(v[0] for v in r['values']))<1e-8*r['total_ff']
            loaded.append(i)
            rows[i]=dict(net=r['net'],master=i,native_without_upper_ff=r['total_ff'],sigma_ff=r['sigma_ff'],
                original_row_sha256=hashlib.sha256(raw).hexdigest(),source_file=str(path),source_line=no,
                statistical_gate=r['sigma_ff']<=.003*r['total_ff'],
                scope='Only whole-conductor native-only scalar. Old origin bins are not reused.')
        if expected:assert loaded==expected[:len(loaded)]
        sources.append(dict(path=str(path),sha256=sha(path),complete_rows=len(loaded),discarded_unterminated_bytes=trailing))
    result=dict(rows={str(k):v for k,v in sorted(rows.items())},sources=sources,
        reused_total_rows=len(rows),qualified_before_rows=sum(v['statistical_gate'] for v in rows.values()),
        missing_or_unqualified_ids=[i for i in range(2491) if i not in rows or not rows[i]['statistical_gate']],
        geometry='Original full native M1-M10, all shared M10 belongs to native in this before scalar.',offset=.25,minimum_walks=1048576,
        old_owner_partitions_reused=False)
    (out/'before-reuse.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','missing_or_unqualified_ids']}),flush=True)

if __name__=='__main__':main()
