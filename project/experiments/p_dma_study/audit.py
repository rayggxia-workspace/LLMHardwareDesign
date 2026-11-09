"""Independent byte/work/phase checks; no timing constants reused for prediction."""
from collections import Counter
import math


def trace_info(path):
    lines=path.read_text().splitlines()
    nt,no,tokens=map(int,lines[0].split())
    tensors=[tuple(map(int,line.split())) for line in lines[1:nt+1]]
    ops=[]
    for line in lines[nt+1:]:
        x=line.split()
        ops.append(dict(out=int(x[0]),kind=x[1],r=int(x[3]),n=int(x[4]),k=int(x[5]),
                        batches=int(x[6]),layout=int(x[8]),inputs=list(map(int,x[10:]))))
    assert len(ops)==no
    return tensors,ops,tokens


def check(row,path):
    tensors,ops,tokens=trace_info(path)
    d=row['detail']
    assert row['tokens']==tokens
    assert abs(row['tokens_per_second']*row['seconds']-tokens)<1e-8
    assert row['P_scratch_peak_bytes']<=16384 and row['U_cache_peak_bytes']+4096<=16384
    assert row['max_outstanding_beats']<=(8 if d['variant']=='credits8' else 32)
    assert row['max_outstanding_descriptors']<=32
    keys=('logical_read','logical_write','bus_read','bus_write','descriptors')
    total=Counter();flows={}
    for channel in d['channels']:
        local=Counter()
        for name,traffic in channel['flows'].items():
            for key in keys:local[key]+=traffic[key]
            f=flows.setdefault(name,Counter())
            f.update(traffic)
        assert dict(local)==channel['traffic']
        total.update(local)
        assert channel['bus_work_subcycles']<=d['end_subcycles']
        assert channel['beats']*64==local['bus_read']+local['bus_write']
    assert total['logical_read']==row['logical_read_bytes']
    assert total['logical_write']==row['logical_write_bytes']
    assert total['bus_read']==row['read_bus_bytes'] and total['bus_write']==row['write_bus_bytes']
    assert total['descriptors']==row['dma_descriptors']
    for actor in d['P']:
        assert sum(actor[k] for k in ('consumer_ready_wait_subcycles','input_ACK_wait_subcycles',
                                      'service_subcycles','output_subcycles'))==actor['elapsed_subcycles']
        assert actor['write_buffer_peak_bytes']<=512
    assert sum(p['tiles'] for p in d['P'])==row['M_tiles']
    expected_shapes=Counter()
    weights=dynamic=outputs=macs=0
    bits=8 if 'w8' in row['profile'] else 16
    for op in ops:
        if op['kind']!='Dot':continue
        r,n,k,b,layout=(op[x] for x in ('r','n','k','batches','layout'))
        expected_shapes[f'{r}x{n}x{k}b{b}l{layout}']+=1
        macs+=r*n*k*b
        if layout==0:weights+=math.ceil(r/8)*n*k*b*bits//8
        else:dynamic+=math.ceil(r/8)*n*k*b*(tensors[op['inputs'][1]][2]//8)
        outputs+=r*n*b*4
    assert expected_shapes==Counter({s['key']:s['calls'] for s in d['matrix_shapes']})
    assert flows['weight']['logical_read']==weights
    assert flows['dynamic_B']['logical_read']==dynamic
    assert flows['dot_output']['logical_write']==outputs
    for name in ('A','weight','dynamic_B','dot_output'):
        for key in keys:
            assert sum(s['flows'][name][key] for s in d['matrix_shapes'])==flows[name][key]
    assert all(s['service_subcycles']<=d['end_subcycles'] for s in d['S_calendars'])
    return dict(passed=True,shape_count=len(expected_shapes),matrix_MACs=macs,
                minimum_static_weight_payload=weights,dynamic_B_payload=dynamic,
                dot_output_payload=outputs,flow_totals={k:dict(v) for k,v in flows.items()},
                scope='bytes/work/private-S/credit/P-consumer-phase conservation, not numeric/RTL/DDR qualification')
