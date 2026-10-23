"""Paired finite-port RQ placements for Llama-sized representative linear tiles."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
from common import provenance,save,digest
from service_model import build,audit_schedule


def execute(config):
    layer,phase,mode,lanes,window,cost,policy,placement=config
    k=2048 if layer=='q_proj' else 8192
    rows=1 if phase=='decode' else (16 if layer=='q_proj' else 8)
    g=build(rows,k,mode,placement,lanes,window,cost)
    s=g.schedule(policy);audit=audit_schedule(g,s)
    result={'layer':layer,'phase':phase,'scale_mode':mode,'lanes':lanes,'window':window,
        'consumer_cost':cost,'policy':policy,'placement':placement,'rows':rows,'K':k,
        'cycles':s['cycles'],'busy':s['busy'],'bytes':dict(g.bytes),'audit':audit}
    # Predetermined trace set, selected before results; no winner sampling.
    witness=None
    if (mode,lanes,window,cost,policy)==('static',1,1,8,'fifo'):
        witness={'configuration':result,'nodes':g.nodes,'packets':g.packets,'leases':g.leases,
                 'sizes':g.sizes,'schedule':s}
    return result,witness


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--development',action='store_true');a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    prod=provenance(a.development)
    try:build(16,8192,'static','near',1,1,8)
    except ValueError as e:rejection=str(e)
    else:raise AssertionError('missing real input capacity rejection')
    configs=[(l,p,m,n,w,c,s,x) for l in ('q_proj','down_proj') for p in ('prefill','decode')
             for m in ('static','dynamic_row') for n in (1,8) for w in (1,2) for c in (1,8,64)
             for s in ('fifo','critical') for x in ('near','shared')]
    a.output.mkdir(parents=True);results=[];witnesses=0
    with ProcessPoolExecutor(max_workers=2) as pool:
        for result,witness in pool.map(execute,configs):
            results.append(result)
            if witness is not None:
                raw=(json.dumps(witness,sort_keys=True,separators=(',',':'))+'\n').encode()
                (a.output/f'witness-{witnesses:02}.json.gz').write_bytes(gzip.compress(raw,mtime=0));witnesses+=1
    pairs=[]
    for a1,a2 in zip(results[::2],results[1::2]):
        assert a1['placement']=='near' and a2['placement']=='shared'
        pairs.append({'configuration':{k:v for k,v in a1.items() if k in
                    ('layer','phase','scale_mode','lanes','window','consumer_cost','policy','rows','K')},
            'near_cycles':a1['cycles'],'shared_cycles':a2['cycles'],
            'cycle_reduction':(a2['cycles']-a1['cycles'])/a2['cycles']})
    # Descriptive equal-freedom policy envelope, not an independent acceptance set.
    envelope=[]
    for l in ('q_proj','down_proj'):
        for p1 in ('prefill','decode'):
            for m in ('static','dynamic_row'):
                for n in (1,8):
                    for c in (1,8,64):
                        scores={x:min(r['cycles'] for r in results if
                            (r['layer'],r['phase'],r['scale_mode'],r['lanes'],r['consumer_cost'],r['placement'])==
                            (l,p1,m,n,c,x)) for x in ('near','shared')}
                        envelope.append({'layer':l,'phase':p1,'scale_mode':m,'lanes':n,'consumer_cost':c,
                            **scores,'cycle_reduction':(scores['shared']-scores['near'])/scores['shared']})
    summary={'runs':len(results),'pairs':len(pairs),'witnesses':witnesses,
        'envelope_pairs':len(envelope),'near_faster_envelope':sum(r['cycle_reduction']>0 for r in envelope),
        'near_slower_envelope':sum(r['cycle_reduction']<0 for r in envelope),
        'max_reduction_envelope':max(r['cycle_reduction'] for r in envelope),
        'min_reduction_envelope':min(r['cycle_reduction'] for r in envelope),
        'prefill16_down_K8192_rejected':rejection,
        'retile':'down prefill8; W/A disjoint in six32KiB input banks, META S6 and outputs S7',
        'scope':'four repetitions of representative N16 tile, prepacked residentS; same resource paired RQ placement, not complete projection/GQA service, M/A attention, RTL, physical or end-to-end speed'}
    for name,obj in [('runs.json',results),('pairs.json',pairs),('envelope.json',envelope),('summary.json',summary)]:save(a.output/name,obj)
    save(a.output/'manifest.json',{'producer':prod,'artifacts':{f.name:{'bytes':f.stat().st_size,'sha256':digest(f)} for f in a.output.iterdir() if f.is_file()}})
    print(json.dumps(summary))


if __name__=='__main__':main()
