"""Paired frozen-layer frequency probes, retaining native three-P scheduling.

Only core-coupled timing changes. DDR tick/config and numerical inputs stay fixed.
Skipped layers are replaced by accepted residual snapshots outside timed segments.
This is a representative-layer measurement, not a full-model replay.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
from struct import pack, unpack_from
import sys
import time

from fast_qwen3_short import BatchedClock
from fast_tlm_replay import DramBridge, TICK_PS
import native_tlm_projection
import pr272_native_projection
from projection_math import NativeAccumulator
import qwen3_short as replay
from six_model_observation import ModelObservation
from ddr_window_energy import snapshot, window


def digest(p):
    h = sha256()
    with p.open('rb') as f:
        for data in iter(lambda: f.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def difference(after, before):
    if isinstance(after, dict):
        return {k: difference(v, before.get(k, {} if isinstance(v, dict) else [0]*len(v) if isinstance(v, list) else 0)) for k,v in after.items()}
    if isinstance(after, list):
        return [difference(a,b) for a,b in zip(after,before)]
    if isinstance(after, (int,float)):
        return after-before
    return after


def main():
    p = argparse.ArgumentParser()
    for key in ('model','baseline','library','ini','output'):
        p.add_argument(key)
    p.add_argument('--core-ps', type=int, required=True)
    a=p.parse_args()
    baseline, out = Path(a.baseline), Path(a.output)
    out.mkdir(parents=True)
    frozen=json.loads((baseline/'result.json').read_bytes())
    assets=baseline/'assets'
    plan=json.loads((assets/'plan.json').read_bytes())
    assert digest(assets/'plan.json')==frozen['plan_sha256']
    assert plan['three_p'] and frozen['pr272_profile']=='combined' and TICK_PS==630
    assert a.core_ps in (3334,5000)
    replay.CORE_PS=a.core_ps
    replay.Clock,replay.Dram=BatchedClock,DramBridge
    arithmetic=NativeAccumulator(Path(os.environ['SHORT_PROJECTION_MATH']))
    native_tlm_projection.accumulate=pr272_native_projection.accumulate=arithmetic
    execution=replay.Execution(plan,assets,Path(a.library),Path(a.ini),out,4,'combined')
    assert all(bank.core_ps==a.core_ps and bank.words_per_beat==4 for bank in execution.sram)
    huge=1<<60
    windows={'prefill':{'start_ps':0,'end_ps':huge},'first_token':{'start_ps':0,'end_ps':huge},'decode':{'start_ps':huge,'end_ps':huge}}
    (out/'observation-windows.json').write_text(json.dumps(windows))
    os.environ['QWEN3_COMPONENT_WINDOWS']=str(out/'observation-windows.json')
    observation=ModelObservation(execution)
    active='prefill' if plan['mode']=='prefill' else 'first_token'
    serial=[0]
    def sample_snapshot():
        tag='segment-'+str(serial[0]); serial[0]+=1
        execution.dram.capture_energy(tag)
        observation.write(out/'component-cumulative.json')
        obs=json.loads((out/'component-cumulative.json').read_bytes())['windows'][active]
        obs.pop('boundaries')
        obs['service_calls']={str(k):v for k,v in execution.calls.items()}
        return snapshot(out/('energy-'+tag+'.json')),obs
    segments=[]
    def measure(kind,step,layer,fn):
        start,before=sample_snapshot()
        fn()
        end,after=sample_snapshot()
        if execution.dram.pending:
            raise ValueError('segment left DMA in flight')
        row={'kind':kind,'step':step,'layer':layer,'position':plan['phases'][step]['position'] if step>=0 else None,
             'elapsed_ps':end['replay_ps']-start['replay_ps'],'ddr':window(start,end,1),
             'components':difference(after,before)}
        segments.append(row)
        return row
    addr,size=plan['local']['address'],plan['local']['bytes']
    path=assets/'local.bin'
    _,_,raw=replay.parse_pm_image(path.read_bytes(),path,base=addr,count=size,crc=plan['local']['crc'],role='local',topology=replay.TOPOLOGY)
    def install():
        for target in (replay.U,replay.P,replay.CONTEXT,replay.MID):
            execution.scheduler.install_pm(addr,size,mother=False)
            execution.scheduler.bind_local(target,raw)
    measure('boot',-1,None,install)
    n=plan['layers']
    selected=sorted(set((0,n//2,n-1)))
    # Include both periodic attention variants and recurrent/dense classes.
    if a.model=='gemma': selected=sorted(set(selected+[5]))
    if a.model in ('qwen35','falcon'): selected=sorted(set(selected+[3]))
    input_hashes={'plan':digest(assets/'plan.json'),'frozen_result':digest(baseline/'result.json'),
                  'ini':digest(Path(a.ini)),'ddr_library':digest(Path(a.library))}
    def layer_file(step,layer):
        stem='{}-{}-layer-{}'.format(plan['mode'],step,layer)
        candidates=[baseline/(stem+suffix) for suffix in ('.q16','.s32')]
        found=[p for p in candidates if p.exists()]
        if len(found)!=1:raise ValueError('missing or ambiguous frozen layer '+stem)
        return found[0]
    numerical=[]
    for step,phase in enumerate(plan['phases']):
        execution.memory.step=step
        token=frozen['boundary'][step]['input_id']
        def ingress():
            ready=[]
            def feed(value):
                execution.sram[replay.U].access(execution.token_word,lambda _:ready.append(True),pack('<i12x',value))
            if plan['mode']=='decode':feed(token)
            else:
                def from_ddr():
                    value=unpack_from('<i',execution.memory(plan['prompt']),step*4)[0]
                    assert value==token
                    feed(value)
                execution.dram.submit(replay.Transfer(plan['prompt']),from_ddr,channel=0)
            execution.clock.until(lambda:bool(ready))
            execution.pages(phase['ingress'])
        measure('ingress',step,None,ingress)
        for layer in selected:
            if layer:
                source=layer_file(step,layer-1)
                data=source.read_bytes()
                assert len(data)==execution.hidden*4
                input_hashes[source.name]=sha256(data).hexdigest()
                # Restore the accepted input activation without charging skipped work.
                for word in range(execution.hidden//4):
                    execution.sram[replay.U].words[word]=data[word*16:word*16+16]
            row=measure('layer',step,layer,lambda:execution.pages(phase['layers'][layer]))
            got=b''.join(execution.sram[replay.U].words[word] for word in range(execution.hidden//4))
            reference=layer_file(step,layer)
            expected=reference.read_bytes()
            check={'step':step,'layer':layer,'equal':got==expected,'sha256':sha256(got).hexdigest(),'reference_sha256':sha256(expected).hexdigest()}
            numerical.append(check)
            if got!=expected:raise ValueError('representative layer numeric mismatch '+str(check))
            row['output_sha256']=check['sha256']
            print('LAYER_PASS',a.model,plan['mode'],a.core_ps,step,layer,row['elapsed_ps'],flush=True)
            (out/'progress.json').write_text(json.dumps({'segments':segments,'numerical':numerical},indent=2))
        if plan['mode']=='decode':
            def head():
                execution.read(replay.U,0,execution.hidden//4)
                execution.logits.clear()
                execution.pages(phase['vocabulary'])
            row=measure('head',step,None,head)
            got=pack('<{}i'.format(execution.vocab),*execution.logits)
            expected=(baseline/('logits-{}.bin'.format(step))).read_bytes()
            if got!=expected:raise ValueError('head logits mismatch')
            row['output_sha256']=sha256(got).hexdigest()
        else:
            measure('residual_read',step,None,lambda:execution.read(replay.U,0,execution.hidden//4))
        if execution.memory.recurrent_regions:
            if step==0:
                # The full replay checks all layers. Here retain the committed
                # subset of sampled recurrent layers, and audit its second read.
                declared={base+off for s,base,size in execution.memory.recurrent_regions
                          if s==0 for off in range(0,size,64)}
                execution.memory.recurrent_previous=declared.intersection(execution.memory.committed)
                assert execution.memory.recurrent_previous
            else:
                assert execution.memory.recurrent_reads==execution.memory.recurrent_previous
    stats=dict(execution.dram.stats)
    assert stats.get('reads',0)+stats.get('writes',0)==stats.get('callbacks',0)
    execution.dram.close()
    source={str(Path(mod.__file__).resolve()):digest(Path(mod.__file__)) for mod in list(sys.modules.values())
            if getattr(mod,'__file__',None) and str(mod.__file__).endswith('.py')
            and ('/public/home/' in str(mod.__file__) or '/LLMHardware/zenanyan/' in str(mod.__file__))}
    source[str(Path(__file__).resolve())]=digest(Path(__file__))
    result={'model':a.model,'phase':plan['mode'],'core_ps':a.core_ps,'ddr_tick_ps':TICK_PS,'selected_layers':selected,
            'segments':segments,'numerical':numerical,'ddr_terminal':stats,'input_sha256':input_hashes,'source_sha256':source,
            'baseline':str(baseline),'python':sys.version,'passed':True,
            'scope':'Representative complete-layer/ingress/head replay; accepted residual restoration; not full-model run'}
    (out/'samples.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('FREQUENCY_PROBE_PASS',a.model,plan['mode'],a.core_ps,len(numerical),flush=True)


if __name__=='__main__':main()
