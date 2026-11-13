"""Audit work/traffic lower bounds independently of SystemC event scheduling."""
import argparse,json,math
from pathlib import Path

def workload(path):
    lines=path.read_text().splitlines();nt,no,tokens=map(int,lines[0].split())
    tensors=[tuple(map(int,x.split())) for x in lines[1:1+nt]]
    ops=[]
    for line in lines[1+nt:]:
        x=line.split();ops.append(dict(out=int(x[0]),kind=x[1],elements=int(x[2]),r=int(x[3]),n=int(x[4]),k=int(x[5]),batches=int(x[6]),layout=int(x[8]),inputs=list(map(int,x[10:]))))
    assert len(ops)==no
    return tensors,ops,tokens

def audit(result,trace):
    ts,ops,tokens=workload(trace);p=result['profile']
    native=p not in ('packed_k1','packed_k32','local_stream','unfused','slow_vector')
    resident='resident' in p or p.startswith('queued')
    weight_bits=8 if 'w8' in p else 16
    chunk=256 if 'k256' in p or p.startswith(('stream','queued')) else 1 if p=='packed_k1' else 32
    tiles=commands=minimum_weights=macs=0
    for o in ops:
        if o['kind']!='Dot':continue
        abits=ts[o['inputs'][0]][2];bbits=weight_bits if o['layout']==0 else ts[o['inputs'][1]][2]
        macs+=o['batches']*o['r']*o['n']*o['k']
        if o['layout']==0:minimum_weights+=o['batches']*math.ceil(o['r']/8)*o['n']*o['k']*(bbits//8)
        for rr in range(0,o['r'],8):
            r=min(8,o['r']-rr)
            limit=min(chunk,max(8,((16384-r*8*12-1024)//(2*(r*(abits//8)+8*(bbits//8)))//8)*8))
            full_a=r*o['k']*(abits//8)
            if resident and full_a+r*8*12+1024<16384:
                fit=(16384-full_a-r*8*12-1024)//(2*8*(bbits//8))
                if fit>=8:limit=min(limit,(fit//8)*8)
            count=o['batches']*math.ceil(o['n']/8)*math.ceil(o['k']/limit)
            tiles+=count;commands+=count*(1 if native else (3 if abits==32 else 1)*(3 if bbits==32 else 1))
    assert result['M_tiles']==tiles,(p,tiles,result['M_tiles'])
    assert result['M_commands']==commands
    assert result['logical_read_bytes']>=minimum_weights
    assert result['P_scratch_peak_bytes']<=16384 and result['U_cache_peak_bytes']+4096<=16384
    assert abs(result['seconds']-result['ticks']/300e6)<=1/300e6+1e-10
    assert abs(result['tokens_per_second']*result['seconds']-tokens)<1e-8
    assert abs(sum(result['spans_ticks'].values())-result['ticks'])<=len(result['spans_ticks'])
    assert result['KV_state_write_bytes']==(73728 if result['workload'].startswith('decode') else 0)
    return {'workload':result['workload'],'profile':p,'matrix_MACs':macs,'static_weight_read_lower_bound_bytes':minimum_weights,'M_tiles':tiles}

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-cases',type=int,default=34);args=p.parse_args()
    results=json.loads(Path('generated/results.json').read_text());rows=[]
    assert len(results)==args.expected_cases,('incomplete/stale sweep',len(results),args.expected_cases)
    for r in results:rows.append(audit(r,Path('generated')/(r['workload']+'.trace')))
    report={'scope':'independent work, weight-traffic lower bound, finite S, KV write extent and clock conversion audit','cases':rows}
    Path('generated/audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('AUDIT_PASS',len(rows))

if __name__=='__main__':main()
