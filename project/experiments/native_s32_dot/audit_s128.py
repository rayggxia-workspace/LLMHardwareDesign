"""Offline S request/ACK/operand identity audit and calibrated service fees."""
import argparse
from collections import deque
import csv
import io
import json
from pathlib import Path
import re
from audit import read_run

FIELDS=('kind','key','tag','full_k','offset','length','n','rows','shift','layout',
        'abase','bbase','result_base','committed','error','aborted','done','abort_mode','expected')


def audit_trace(trace,stimulus,mode):
    commands={}
    for line in stimulus.decode().splitlines():
        cmd=dict(zip(FIELDS,(int(v,16) for v in line.split()),strict=True))
        if cmd['kind']!=3:commands[cmd['tag']]=cmd
    frame=None;owner=None;results=[];retired=set()
    queue=deque();rt=[]
    for cycle,kind,a,b,c,d in csv.reader(io.StringIO(trace.decode())):
        cycle,a,b,c,d=map(int,(cycle,a,b,c,d))
        if kind=='CMD':
            assert frame is None and not queue and d not in retired
            command=commands[d];assert (a,b,c)==tuple(command[name] for name in ('kind','offset','length'))
            frame=dict(cmd=command,start=cycle,reads=[],writes=[],input_steps=[],core_done=[],acks=[],rt=[],peak=0)
        else:assert frame is not None
        if kind=='SREQ':
            assert c==len(queue)<2
            queue.append((a,b,cycle));frame['peak']=max(frame['peak'],len(queue))
            frame['writes' if a else 'reads'].append((b,cycle))
        elif kind=='SACK':
            assert c==len(queue) and queue
            wr,address,start=queue.popleft();assert (a,b)==(wr,address)
            latency=cycle-start;assert latency>=2 and (mode or latency==2)
            rt.append(latency);frame['rt'].append(latency);frame['acks'].append((a,b,cycle))
        elif kind=='CORE_IN' and a==1:frame['input_steps'].append((b,c,cycle))
        elif kind=='CORE_OUT' and b:frame['core_done'].append((a,cycle))
        elif kind=='RSP':
            cmd=frame['cmd'];assert not queue and a==cmd['kind'] and b==cycle-frame['start']
            assert c==len(frame['reads'])+len(frame['writes'])==len(frame['acks'])
            if cmd['kind']==0 and not cmd['error']:
                assert owner is None;owner=cmd
            if cmd['kind']==1 and not cmd['error']:
                assert owner is not None and owner['key']==cmd['key']
                rows=owner['rows'];n=owner['n'];layout=owner['layout'];groups=(n+3)//4;length=cmd['length']
                reads=[]
                for k in range(0,length,4):
                    reads.extend(cmd['abase']+r*32+k//4 for r in range(rows))
                    if layout:
                        reads.extend(cmd['bbase']+kk*2+g for kk in range(k,min(k+4,length)) for g in range(groups))
                    else:reads.extend(cmd['bbase']+col*32+k//4 for col in range(n))
                assert [addr for addr,_ in frame['reads']]==reads
                assert [(k,g) for k,g,_ in frame['input_steps']]==[(cmd['offset']+k,g) for k in range(length) for g in range(groups)]
                writes=list(range(owner['result_base'],owner['result_base']+2*rows)) if cmd['done'] else []
                assert [addr for addr,_ in frame['writes']]==writes
                assert d==((1<<len(writes))-1)
                if cmd['done']:
                    assert frame['core_done']==[(1,frame['core_done'][0][1])]
                    assert frame['core_done'][0][1]>frame['acks'][-1][2]
                read_ack=[cy for wr,_,cy in frame['acks'] if not wr]
                write_ack=[cy for wr,_,cy in frame['acks'] if wr]
                results.append(dict(layout='K-major' if layout else 'N-major',rows=rows,n=n,
                    full_k=owner['full_k'],k_offset=cmd['offset'],chunk_k=length,final=bool(cmd['done']),
                    cmd_to_terminal_cycles=b,reads=len(reads),writes=len(writes),
                    first_s_req=frame['reads'][0][1]-frame['start'],last_read_ack=read_ack[-1]-frame['start'],
                    first_core_input=frame['input_steps'][0][2]-frame['start'],
                    last_core_input=frame['input_steps'][-1][2]-frame['start'],
                    last_write_ack=write_ack[-1]-frame['start'] if write_ack else None,
                    max_s_owner=frame['peak'],max_s_rtt=max(frame['rt'])))
                if cmd['done']:owner=None
            elif cmd['kind']==2 and not cmd['error'] or cmd['aborted']:
                if cmd['kind']==1:
                    assert owner is not None
                    true_mask=0
                    for wr,addr,_ in frame['acks']:
                        if wr:true_mask|=1<<(addr-owner['result_base'])
                    assert true_mask==d
                owner=None
            elif cmd['error']:
                assert c==0 and d==0
            retired.add(cmd['tag']);frame=None
    assert frame is None and not queue and owner is None and retired==set(commands)
    return dict(frames=results,largest_observed_S_RTT=max(rt),min_S_RTT=min(rt))


def audit(directory):
    receipt,files,inventory=read_run(directory)
    result=dict(job=receipt['job'],source_commit=receipt['source_commit'],kind=receipt['kind'],
                source_archive_sha256=receipt['source_archive_sha256'],receipts_archive_sha256=receipt['receipts_archive_sha256'],
                rows=[],timing=[])
    real=receipt['kind']=='s128-real'
    for seed in range(25201,25207):
        prefix=f'seed-{seed}/'
        report=json.loads(files[prefix+'result.json']);assert report['job']==receipt['job'] and report['seed']==seed
        assert len(report['affinity'])==10 and bool(report.get('real_s'))==real
        for variant in report['variants']:
            rows=variant['rows_capacity'];p=prefix+f'rows-{rows}/'
            assert inventory[p+'service.txt']==variant['vectors_sha256']
            if not report['passed']:continue
            assert b'%Warning' not in files[p+'build.log']
            for mode in range(2):
                for init in range(3):
                    name=p+f'service-{mode}-{init}.log';log=files.get(name,files.get(name+'.tail',b'')).decode(errors='replace')
                    m=re.search(r'PASS native32 S128 rows=(\d+) lanes=(\d+) mode=(\d+) commands=(\d+) req=(\d+) ack=(\d+) write_ack=(\d+) peak=(\d+) held=(\d+) aborts=(\d+) cycles=(\d+)',log)
                    assert m and 'Error' not in log
                    r,lanes,md,commands,req,ack,wr,peak,held,aborts,cycles=map(int,m.groups())
                    assert (r,lanes,md)==(rows,rows*4,mode) and req==ack and peak<=2 and aborts==4
                    assert wr>0 and held>0
                    if real:
                        cap=re.search(r'real=1 boot=(\d+) readback=(\d+)',log)
                        assert cap and int(cap[1])>0 and int(cap[2])==wr and peak==2
                    result['rows'].append(dict(seed=seed,rows=rows,lanes=lanes,mode=mode,initial=init,commands=commands,
                        s_requests=req,s_acks=ack,result_write_acks=wr,max_owner=peak,held_request_cycles=held,
                        aborted_live_requests=aborts,fixture_total_cycles=cycles))
                trace_name=p+f'timing-{mode}-0.csv'
                if trace_name in files:
                    checked=audit_trace(files[trace_name],files[p+'service.txt'],mode)
                    result['timing'].append(dict(seed=seed,rows_capacity=rows,mode=mode,**checked))
    result['passed']=len(result['rows'])==108
    if not result['passed']:
        assert any(b'%Error' in data for name,data in files.items() if name.endswith('build.log'))
    result['real_S']=real and result['passed']
    result['physical_qualified']=False
    result['scope']='Functional single-S128 service; fixture boot/staging and numerical readback use real SRAM when real_S. No DDR, production controller, 300MHz or whole-model claim.'
    (directory/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);result=audit(p.parse_args().run)
    print(json.dumps(dict(job=result['job'],passed=result['passed'],real_S=result['real_S'],runs=len(result['rows']),
                          audited_event_traces=len(result['timing']))))
