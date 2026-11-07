"""Check the physical full-electrode matrix, never symmetrize owner-only rows."""
import argparse
from array import array
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
from statistics import NormalDist


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',type=Path,nargs='+',required=True)
    a=p.parse_args();caps={};errors={};receipts=[]
    sign_limit=NormalDist().inv_cdf(1-.05/(2*2491*2502))
    positive_estimates=0;resolved_positive=0;maximum_positive=0.
    for directory in a.runs:
        meta=json.loads((directory/'solve.json').read_text());receipts.append(meta)
        assert meta['passed'] and not meta['lower_only']
        assert meta.get('surface_interval_merge_fixed')
        assert meta['complete_native_instance_context'] and meta['minimum_native_layer']==1
        source=directory/'rows.jsonl';assert sha(source)==meta['rows_sha256']
        loaded=[]
        with source.open() as f:
            for line in f:
                row=json.loads(line);i=row['master'];assert i not in caps
                assert row['net']=='word_'+format(i,'04')
                values=row['values'];total=row['total_ff']
                assert total>0 and abs(sum(v[0] for v in values))<1e-8*total
                for j,v in enumerate(values):
                    if j==i or v[0]<=1e-10:continue
                    positive_estimates+=1
                    maximum_positive=max(maximum_positive,v[0])
                    resolved_positive+=v[0]>sign_limit*v[1]
                caps[i]=array('d',(v[0] for v in values[:2491]))
                errors[i]=array('d',(v[1] for v in values[:2491]))
                loaded.append(i)
        assert loaded==meta['masters']
    assert set(caps)==set(range(2491)),'Complete paired coverage is required'
    assert len({(m['scene_metadata_sha256'],m['offset'],m['solver_sha256']) for m in receipts})==1
    pairs=2491*2490//2
    z_limit=NormalDist().inv_cdf(1-.05/(2*pairs))
    failures=0;worst=[];maximum_asymmetry=0.
    for i in range(2491):
        for j in range(i):
            delta=abs(caps[i][j]-caps[j][i]);bound=errors[i][j]+errors[j][i]
            z=delta/bound if bound else (0. if delta==0 else float('inf'))
            maximum_asymmetry=max(maximum_asymmetry,delta)
            failures+=z>z_limit
            item=(z,i,j,delta,bound)
            if len(worst)<20:heapq.heappush(worst,item)
            elif item>worst[0]:heapq.heapreplace(worst,item)
    report=dict(passed=(failures==0 and resolved_positive==0),upper_nets=2491,pairs=pairs,
                familywise_alpha=.05,normal_approximation_z_limit=z_limit,
                outlier_pairs=failures,maximum_absolute_asymmetry_ff=maximum_asymmetry,
                positive_offdiagonal_estimates=positive_estimates,
                statistically_resolved_positive_offdiagonals=resolved_positive,
                offdiagonal_sign_z_limit=sign_limit,maximum_positive_estimate_ff=maximum_positive,
                all_total_statistical_gates=all(m['all_rows_statistical_gate'] for m in receipts),
                source_runs=[str(x) for x in a.runs],
                uncertainty='Sum of pair standard deviations bounds unknown cross-row correlation; Gaussian multiple-comparison threshold.',
                qualification='Tests full-net Maxwell reciprocity and statistically resolved sign violations. Small positive raw estimates are retained with their uncertainty. Owner-source partitions need not be symmetric.',
                direct_macro_reuse_qualified=False)
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    (out/'reciprocity.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'worst-pairs.json').write_text(json.dumps([dict(z=v[0] if math.isfinite(v[0]) else None,
                first=v[1],second=v[2],difference_ff=v[3],sigma_bound_ff=v[4]) for v in sorted(worst,reverse=True)],indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
