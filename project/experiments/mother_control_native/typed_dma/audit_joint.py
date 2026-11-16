"""Audit existing three-P DMA traces; no simulation or regenerated payload."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tarfile

def stats(values):
    v=sorted(values)
    return {'n':len(v),'min':v[0],'p50':v[math.ceil(len(v)*.5)-1],
            'p95':v[math.ceil(len(v)*.95)-1],'max':v[-1]}

def audit(text):
    stage={}
    transport={}
    global_live={}
    staged_counts=[0]*3
    stage_max=[0]*3
    mode=[0]*3
    issue_cycles=[[],[]]
    n={'accepted':0,'issued':0,'returned':0,'reserved_cancel':0,
       'good_stage':0,'rejected_stage':0,'cancelled_stage':0,'mode':0}
    timings={2:{},4:{}}
    pressure={}
    for row in csv.reader(io.StringIO(text)):
        ev=row[0]
        if ev=='PERF_WINDOW':
            continue
        cy=int(row[1])
        if ev=='MODE':
            c,new=map(int,row[2:4])
            assert not any(k[0]==c for k in transport) and staged_counts[c]==0
            mode[c]=new;n['mode']+=1
        elif ev=='RESERVE':
            c,tag,ch=map(int,row[2:5]);key=(c,tag)
            assert key not in transport
            transport[key]=[ch,None,False];n['accepted']+=1
            if c<3 and mode[c]:
                assert tag%2==0 and key in stage and stage[key]['admit']<cy
                stage[key]['reserve']=cy
        elif ev=='ISSUE':
            c,tag,lane,gid=map(int,row[2:6]);key=(c,tag);ch=lane//2
            assert transport[key]==[ch,None,False] and gid not in global_live
            transport[key][1]=gid;global_live[gid]=key;n['issued']+=1
            issue_cycles[ch].append(cy)
            if len(issue_cycles[ch])>=5:
                assert issue_cycles[ch][-5]<cy-2
            if key in stage:
                stage[key]['issue']=cy
        elif ev=='DDR_RETURN':
            lane,gid,bad=map(int,row[2:5])
            if not bad:
                key=global_live[gid];assert transport[key]==[lane//2,gid,False]
                transport[key][2]=True
        elif ev=='CLIENT_RETURN':
            c,tag=map(int,row[2:4]);key=(c,tag);_,gid,landed=transport.pop(key)
            assert landed and global_live.pop(gid)==key
            n['returned']+=1
        elif ev=='CANCEL_ACK':
            c,tag,reject=map(int,row[2:5]);key=(c,tag)
            if not reject:
                assert transport.pop(key)[1:] == [None,False]
                n['reserved_cancel']+=1
        elif ev=='STAGE_CMD':
            c,tag,dst,first,words=map(int,row[2:7]);key=(c,tag)
            assert key not in stage and mode[c] and words in (2,4) and first+words<=4
            stage[key]={'admit':cy,'dst':dst,'first':first,'words':words,'req':[],'ack':[]}
            staged_counts[c]+=1;stage_max[c]=max(stage_max[c],staged_counts[c])
            assert staged_counts[c]<=2
        elif ev.startswith('STAGE_'):
            c,tag=map(int,row[2:4]);key=(c,tag);s=stage[key]
            if ev=='STAGE_CAPTURE':
                assert s['issue']<cy
                s['capture']=cy
            elif ev=='STAGE_RAW_FIRST':
                assert s['capture']<cy
                s['raw_first']=cy
            elif ev=='STAGE_SREQ':
                assert s['raw_first']<cy and int(row[4])==s['dst']+len(s['req'])
                assert len(s['req'])-len(s['ack'])<2
                s['req'].append(cy)
            elif ev=='STAGE_SACK':
                i=len(s['ack'])
                assert s['req'][i]<cy and int(row[4])==i+1
                s['ack'].append(cy)
            elif ev=='STAGE_RAW_ACK':
                assert s['raw_first']<cy and all(t<cy for t in s['ack'])
                assert len(s['req'])==len(s['ack'])
                s['raw_ack']=cy
            elif ev=='STAGE_CANCEL':
                assert 'capture' not in s
                s['cancel']=cy
            elif ev=='STAGE_DONE':
                mask,error,cancel=map(int,row[4:7])
                if error:
                    assert 'reserve' not in s and 'raw_first' not in s and mask==0 and not s['req']
                    n['rejected_stage']+=1
                elif cancel:
                    assert 'cancel' in s and s['raw_ack']<cy and mask==0 and not s['req']
                    n['cancelled_stage']+=1
                else:
                    words=s['words']
                    assert s['raw_ack']<cy and mask==(1<<words)-1
                    assert len(s['req'])==len(s['ack'])==words
                    n['good_stage']+=1
                    deltas={
                        'admit_to_reserve':s['reserve']-s['admit'],
                        'reserve_to_DDR_capture':s['capture']-s['reserve'],
                        'DDR_capture_to_raw_first':s['raw_first']-s['capture'],
                        'raw_first_to_first_S_req':s['req'][0]-s['raw_first'],
                        'raw_first_to_last_S_ack':s['ack'][-1]-s['raw_first'],
                        'last_S_ack_to_raw_ack':s['raw_ack']-s['ack'][-1],
                        'raw_first_to_raw_ack':s['raw_ack']-s['raw_first'],
                        'raw_ack_to_done_take':cy-s['raw_ack'],
                        'admit_to_done_take':cy-s['admit'],
                    }
                    for k,v in deltas.items():timings[words].setdefault(k,[]).append(v)
                    if 11100<=tag//2<=11243:
                        pressure[key]=(s['admit'],cy)
                stage.pop(key);staged_counts[c]-=1
        elif ev=='FENCE_OFFER':
            assert not transport and not global_live
    assert not stage and not transport and not global_live
    assert n=={'accepted':5542,'issued':5541,'returned':5541,'reserved_cancel':1,
               'good_stage':434,'rejected_stage':5,'cancelled_stage':1,'mode':8}
    assert len(pressure)==432 and stage_max==[2,2,2] and mode==[0,0,0]
    span=max(y for _,y in pressure.values())-min(x for x,_ in pressure.values())+1
    return n, stage_max, timings, span

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    rows=[]
    total={2:{},4:{}}
    with tarfile.open(a.archive) as f:
        for m in sorted(f.getmembers(),key=lambda x:x.name):
            if not re.search(r'/joint-\d-\d\.csv$',m.name):
                continue
            b=f.extractfile(m).read()
            n,owners,times,span=audit(b.decode())
            rows.append({'trace':m.name,'sha256':hashlib.sha256(b).hexdigest(),
                         'counts':n,'peak_owners_per_P':owners,'mixed_432_dynamic_span_cycles':span})
            for w in (2,4):
                for k,v in times[w].items():total[w].setdefault(k,[]).extend(v)
    assert len(rows)==18
    report={'schema':'actual-three-P-typed-DMA-joint-audit/1','slurm':102487,
            'exact_archive_sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest(),
            'qualification':'True three stage + three four-bank S + finite typed fabric. DDR peer, no complete dot or model timing.',
            'trials':rows,'cycles':{w:{k:stats(v) for k,v in t.items()} for w,t in total.items()},
            'mixed_432_dynamic_span_cycles':stats([r['mixed_432_dynamic_span_cycles'] for r in rows])}
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('cycles','mixed_432_dynamic_span_cycles')}))

if __name__=='__main__':
    main()

