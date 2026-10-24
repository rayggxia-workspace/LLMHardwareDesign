"""Bounded checkpoint continuation qualification against frozen Issue68 full runs.

Replays only four predetermined D31 guard_rescale conditions, not all84.
This is a producer continuation test, not an independent arithmetic oracle.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import platform
import time

import numpy as np

_spec=importlib.util.spec_from_file_location('issue68_range_checkpoint',Path(__file__).with_name('range.py'))
r=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(r)
ORIGINAL_RANGE_SHA256='83ef2b0f59800b03526e6a0858a57703f92863dfc7b89fb776000c9b56962e3f'


def checked_artifact(root,name,desc):
    root=Path(root).resolve();p=(root/name).resolve()
    if not p.is_relative_to(root) or not p.is_file() or p.stat().st_size!=desc['bytes'] or r.old.sha(p)!=desc['sha256']:raise ValueError('artifact mismatch '+str(name))
    return p


def load_selected(root,ids,kind):
    root=Path(root).resolve();m=json.loads((root/'manifest.json').read_text())
    if m.get('status')!='PASS':raise ValueError('unaccepted source '+str(root))
    metrics='range-results.json' if kind=='range' else 'state-results.json'
    rows=json.loads(checked_artifact(root,metrics,m['artifacts'][metrics]).read_text())
    chosen=[x for x in rows if x['id'] in ids]
    if len(chosen)!=len(ids):raise ValueError('missing/duplicate frozen conditions')
    for row in chosen:
        for key in (('artifact','transaction_trace') if kind=='range' else ('artifact',)):
            desc=row[key];name=desc['name']
            if {k:desc[k] for k in ('bytes','sha256')}!=m['artifacts'].get(name):raise ValueError('row/manifest artifact mismatch')
            checked_artifact(root,name,desc)
    return m,{x['id']:x for x in chosen}


def compare_chunks(encoded,initial,units,value_units,bits,df,position,sequence,full,full_trace,boundaries):
    length=len(encoded['q']);starts=[0]+list(boundaries);ends=list(boundaries)+[length]
    state=initial.astype(np.int64);su=units.astype(np.int16);resume=None
    assembled={'state_trace':[state.copy()],'state_units_trace':[su.copy()],'epoch_trace':[0], 'output_codes':[],'output_units':[]}
    tokens=[];events=[];checkpoints=[]
    for begin,end in zip(starts,ends):
        if not 0<=begin<end<=length:raise ValueError('chunk boundaries')
        encoded_part={k:v[begin:end] for k,v in encoded.items()}
        a,stats=r.run(encoded_part,state,su,value_units,bits,df,'guard_rescale',position+begin,sequence,resume)
        if stats['status']!='EXECUTED' or stats['committed_tokens']!=end-begin:raise AssertionError('continuation did not commit complete chunk')
        for key in ('state_trace','state_units_trace','epoch_trace'):assembled[key].extend(a[key][1:])
        for key in ('output_codes','output_units'):assembled[key].extend(a[key])
        for token in stats['tokens']:
            token['token']+=begin;tokens.append(token)
        for event in stats['rescale_events']:
            event['token']+=begin;events.append(event)
        state=a['state_trace'][-1].astype(np.int64);su=a['state_units_trace'][-1].astype(np.int16)
        resume=r.checkpoint(stats['final'],r.resume_contract(bits,df,value_units,'guard_rescale'))
        checkpoints.append({'after_tokens':end,'checkpoint':resume,'state_sha256':r.old.digest_array(state),'units':su.astype(int).tolist()})
    for key,values in assembled.items():
        got=np.asarray(values,dtype=full[key].dtype)
        if not np.array_equal(got,full[key]):raise AssertionError('continuation differs from frozen full '+key)
    if tokens!=full_trace['tokens'] or events!=full_trace['rescale_events']:raise AssertionError('continuation transaction/event trace differs')
    if stats['final']!=full_trace['final']:raise AssertionError('continuation final version/epoch/position differs')
    return {'boundaries':list(boundaries),'chunks':len(ends),'complete_bitexact':True,
            'transaction_events_bitexact':True,'final':stats['final'],'checkpoints':checkpoints}


def negative_checks(encoded,initial,units,value_units,bits,df,position,sequence,full):
    # Use an actual nonzero committed position, retaining the original global epoch.
    after=min(8,len(encoded['q'])-1)
    state=full['state_trace'][after].astype(np.int64);su=full['state_units_trace'][after].astype(np.int16)
    snapshot=r.stamp(state,su,int(full['epoch_trace'][after]),after,position+after,sequence)
    cp=r.checkpoint(snapshot,r.resume_contract(bits,df,value_units,'guard_rescale'))
    part={k:v[after:after+1] for k,v in encoded.items()};results=[]
    variants=[]
    for field in ('epoch','units','position'):
        bad=copy.deepcopy(cp)
        if field=='units':bad['snapshot'][field][0]+=1
        else:bad['snapshot'][field]+=1
        variants.append((field+'_descriptor',bad,state,su,position+after))
    wrongunits=su.copy();wrongunits[0]+=1;variants.append(('units_payload',cp,state,wrongunits,position+after))
    wrongstate=state.copy();wrongstate.flat[0]+=1;variants.append(('state_payload',cp,wrongstate,su,position+after))
    variants.append(('position_argument',cp,state,su,position+after+1))
    for name,bad,s,u,p in variants:
        try:r.run(part,s,u,value_units,bits,df,'guard_rescale',p,sequence,bad)
        except ValueError as exc:results.append({'name':name,'rejected':True,'error':str(exc)})
        else:raise AssertionError('bad checkpoint accepted '+name)
    return results


def execute(native,legacy,range_native,range_legacy,out,binding=None):
    out=Path(out)
    if out.exists():raise ValueError('refuse existing output file')
    source={'chunk_check_sha256':r.old.sha(__file__),'range_sha256':r.old.sha(Path(__file__).with_name('range.py')),
            'state_sha256':r.old.sha(r.OLD_PATH),'original_range_sha256':ORIGINAL_RANGE_SHA256}
    if binding:
        b=json.loads(Path(binding).read_text())
        for field in ('chunk_check_sha256','range_sha256','state_sha256'):
            if b.get(field)!=source[field]:raise ValueError('source binding '+field)
        source.update(commit=b['commit'],binding_sha256=r.old.sha(binding))
    start=time.monotonic();rows=[]
    for role,rawroot,rangeroot,stem in [('native',Path(native),Path(range_native),'evaluation'),('legacy',Path(legacy),Path(range_legacy),'layer0-end8192')]:
        originals=[stem+'.S'+str(bits)+'.D31' for bits in (16,32)]
        ids=[role+'.'+name+'.guard_rescale' for name in originals]
        sm,srows=load_selected(rawroot,originals,'state');rm,rrows=load_selected(rangeroot,ids,'range')
        if rm['source']['range_sha256']!=ORIGINAL_RANGE_SHA256 or rm['source']['state_sha256']!=source['state_sha256']:raise ValueError('frozen original source hash')
        if rm['source'][role]['manifest_sha256']!=r.old.sha(rawroot/'manifest.json'):raise ValueError('original source provenance')
        source[role]={'raw':str(rawroot.resolve()),'range':str(rangeroot.resolve()),'raw_manifest_sha256':r.old.sha(rawroot/'manifest.json'),
                      'range_manifest_sha256':r.old.sha(rangeroot/'manifest.json'),'range_source':rm['source']}
        for bits in (16,32):
            sid=stem+'.S'+str(bits)+'.D31';rid=role+'.'+sid+'.guard_rescale';sr=srows[sid];rr=rrows[rid]
            if rr['source_artifact']!=sr['artifact'] or rr['status']!='EXECUTED' or rr['committed_tokens']!=rr['requested_tokens']:raise ValueError('selected source/complete trace')
            with np.load(rawroot/sr['artifact']['name'],allow_pickle=False) as z,np.load(rangeroot/rr['artifact']['name'],allow_pickle=False) as f:
                encoded={k:z[k] for k in ('q','k','v','decay','beta')};initial=z['state_initial'].astype(np.int64)
                units=z['state_units'].astype(np.int16);vu=z['value_units'].astype(np.int16);full={k:f[k] for k in f.files}
                trace=json.loads((rangeroot/rr['transaction_trace']['name']).read_text());length=len(encoded['q'])
                position=int(sr['execution']['final_position'])-length;sequence=sr['format']['sequence']
                if not np.array_equal(full['state_trace'][0],initial) or not np.array_equal(full['state_units_trace'][0],units):raise ValueError('initial data changed')
                plans=[('chunk8',list(range(8,length,8))),('chunk16',list(range(16,length,16)))]
                # Predetermined rule uses actual old log event boundaries, never quality.
                boundaries=sorted({b for e in trace['rescale_events'] for b in (e['token'],e['token']+1) if 0<b<length})
                if boundaries:plans.append(('rescale_boundaries',boundaries))
                checked=[]
                for name,boundaries in plans:
                    report=compare_chunks(encoded,initial,units,vu,bits,31,position,sequence,full,trace,boundaries)
                    checked.append(dict(report,name=name))
                negatives=negative_checks(encoded,initial,units,vu,bits,31,position,sequence,full)
                rows.append({'id':rid,'source_artifact':sr['artifact'],'frozen_artifact':rr['artifact'],'frozen_trace':rr['transaction_trace'],
                             'tokens':length,'rescale_waves':len(trace['rescale_events']),'plans':checked,'negative_checks':negatives,
                             'quality_accepted':False,'independent_arithmetic_oracle':False})
    out.parent.mkdir(parents=True,exist_ok=True)
    r.old.save(out,{'status':'PASS_CHECKPOINT_CONTINUATION','source':source,'conditions':len(rows),'rows':rows,'seconds':time.monotonic()-start,
                   'environment':{'python':platform.python_version(),'numpy':np.__version__,'host':platform.node(),'SLURM_JOB_ID':os.environ.get('SLURM_JOB_ID')},
                   'scope':'same integer producer checkpoint/chunk qualification against pre-extension frozen full traces; independent arithmetic receipt remains separate',
                   'checkpoint_integrity_scope':'unkeyed software checksum, not authentication or measured hardware checkpoint engine'})
    print(json.dumps({'status':'PASS_CHECKPOINT_CONTINUATION','conditions':len(rows)}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native','legacy','range-native','range-legacy','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--binding',type=Path);a=p.parse_args()
    execute(a.native,a.legacy,a.range_native,a.range_legacy,a.out,a.binding)


if __name__=='__main__':main()
