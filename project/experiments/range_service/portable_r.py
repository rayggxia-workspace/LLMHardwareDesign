"""Small self-contained real R retry evidence collector and independent replay.

Only encoded integer causal continuity is qualified. Source floating compilers,
the omitted prefix/full256 quality, hardware capacity and PPA are not rerun.
"""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import platform
import time
import types
import zipfile

import numpy as np

ORACLE_SHA='e1f4feac39c582dc06574894fcea88bd52dd6451d62de0bca1490b758d599ace'
BEGIN,END=2,14
MAX_BYTES=15*(1<<20)


def require(ok,label):
    if not ok:raise AssertionError(label)


def jbytes(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def digest(data):return hashlib.sha256(data).hexdigest()
def descriptor(data):return {'bytes':len(data),'sha256':digest(data)}
def sha(path):return digest(Path(path).read_bytes())
def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def oracle_module(data):
    require(digest(data)==ORACLE_SHA,'frozen independent oracle source SHA')
    m=types.ModuleType('portable_issue68_independent_oracle');m.__file__='source/receive_range.py'
    exec(compile(data,m.__file__,'exec'),m.__dict__);return m


def npz_bytes(arrays):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name,a in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(a),allow_pickle=False)
            info=zipfile.ZipInfo(name+'.npy',(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b.getvalue())
    return buf.getvalue()


def zip_bytes(members):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED) as z:
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name,(2026,10,24,0,0,0));z.writestr(info,data)
    return buf.getvalue()


def write_bundle(members,path):
    members=dict(members);members['index.json']=jbytes({'schema':'issue68-portable-r/1','artifacts':{n:descriptor(d) for n,d in sorted(members.items())}})
    data=zip_bytes(members);require(len(data)<=MAX_BYTES,'portable R bundle exceeds15MiB')
    with Path(path).open('xb') as f:f.write(data)
    return descriptor(data)


def checked_file(root,name,desc):
    root=Path(root).resolve();p=(root/name).resolve()
    require(p.is_relative_to(root) and p.is_file(),'safe source path')
    require(descriptor(p.read_bytes())=={k:desc[k] for k in ('bytes','sha256')},'source artifact SHA/bytes '+name)
    return p


def source_rows(root,metrics):
    m=read_json(root/'manifest.json');require(m['status']=='PASS','source execution status')
    rows=read_json(checked_file(root,metrics,m['artifacts'][metrics]));return m,{r['id']:r for r in rows}


def collect(legacy,integer,oracle,audit,chunks,out,binding=None):
    legacy=Path(legacy).resolve();integer=Path(integer).resolve();out=Path(out)
    require(not out.exists(),'refuse existing output directory')
    oracle_data=Path(oracle).read_bytes();o=oracle_module(oracle_data)
    source={'portable_r_sha256':sha(__file__),'receive_range_sha256':ORACLE_SHA}
    if binding:
        b=read_json(binding)
        for key in source:require(b.get(key)==source[key],'collector source binding '+key)
        source.update(commit=b['commit'],binding_sha256=sha(binding))
    sm,srows=source_rows(legacy,'state-results.json');rm,rrows=source_rows(integer,'range-results.json')
    require(rm['schema']=='issue68-range/1' and rm['suite']=='legacy','legacy range contract')
    require(rm['source']['legacy']['manifest_sha256']==sha(legacy/'manifest.json'),'range original input source')
    am=read_json(audit);cm=read_json(chunks)
    require(am['status']=='PASS_INDEPENDENT_ARITHMETIC' and am['integer_manifest_sha256']==sha(integer/'manifest.json'),'independent receipt source')
    require(cm['status']=='PASS_CHECKPOINT_CONTINUATION' and cm['source']['legacy']['range_manifest_sha256']==sha(integer/'manifest.json'),'chunk receipt source')
    members={'source/portable_r.py':Path(__file__).read_bytes(),'source/receive_range.py':oracle_data,
             'provenance/source-manifest.json':(legacy/'manifest.json').read_bytes(),
             'provenance/range-manifest.json':(integer/'manifest.json').read_bytes(),
             'provenance/independent-audit.json':Path(audit).read_bytes(),'provenance/checkpoint-check.json':Path(chunks).read_bytes()}
    cases=[]
    for bits in (16,32):
        sid='layer0-end8192.S'+str(bits)+'.D31';rid='legacy.'+sid+'.guard_rescale';sr=srows[sid];rr=rrows[rid]
        require(rr['status']=='EXECUTED' and rr['committed_tokens']==256 and rr['source_artifact']==sr['artifact'],'fixed full256 provenance')
        require(rr['quality_accepted'] is False and rr['hardware_implemented'] is False,'candidate evidence boundary')
        rawpath=checked_file(legacy,sr['artifact']['name'],sr['artifact']);fullpath=checked_file(integer,rr['artifact']['name'],rr['artifact'])
        tracepath=checked_file(integer,rr['transaction_trace']['name'],rr['transaction_trace']);trace=read_json(tracepath)
        require([e['token'] for e in trace['rescale_events']]==[3,12],'predeclared actual two rescale tokens')
        with np.load(rawpath,allow_pickle=False) as z,np.load(fullpath,allow_pickle=False) as f:
            arrays={k:z[k][BEGIN:END] for k in ('q','k','v','beta','decay')};arrays['value_units']=z['value_units']
            arrays.update({k:f[k][BEGIN:END+1] for k in ('state_trace','state_units_trace','epoch_trace')})
            arrays.update({k:f[k][BEGIN:END] for k in ('output_codes','output_units')})
            require(arrays['state_trace'].shape==(13,2,128,128),'complete head/K/V slice')
            name='selected/S'+str(bits)+'.npz';data=npz_bytes(arrays);members[name]=data
            sliced_trace={'tokens':trace['tokens'][BEGIN:END],'rescale_events':[e for e in trace['rescale_events'] if BEGIN<=e['token']<END]}
            tracename='selected/S'+str(bits)+'.json';members[tracename]=jbytes(sliced_trace)
            original_members={}
            for label,path,names in [('encoded',rawpath,('q','k','v','beta','decay','value_units')),('range',fullpath,('state_trace','state_units_trace','epoch_trace','output_codes','output_units'))]:
                with zipfile.ZipFile(path) as zz:
                    original_members[label]={n+'.npy':descriptor(zz.read(n+'.npy')) for n in names}
            cases.append({'id':rid,'format':rr['format'],'begin':BEGIN,'end':END,'source_row':sr,'range_row':rr,
                          'initial_snapshot':trace['tokens'][BEGIN]['before'],'final_snapshot':trace['tokens'][END-1]['commit']['new'],
                          'artifact':dict(name=name,**descriptor(data)),'transaction_trace':dict(name=tracename,**descriptor(members[tracename])),
                          'original_NPZ_members':original_members,'selected_array_digests':{n:o.digest_array(a) for n,a in arrays.items()}})
    members['selected.json']=jbytes({'schema':'issue68-portable-r/1','source':source,'selection':'fixed layer0-end8192 S16/S32 D31 guard_rescale token[2,14), fullH2K128V128',
                                    'source_manifest_sha256':sha(legacy/'manifest.json'),'range_manifest_sha256':sha(integer/'manifest.json'),'cases':cases,
                                    'limitations':'Integer inputs and pre-existing boundary2 only. No replay of omitted first2 or remaining242 tokens, floating compiler, full256 quality, real memory/ports/RTL/PPA.'})
    out.mkdir(parents=True);desc=write_bundle(members,out/'portable-r.zip')
    delivery={'status':'PACKAGED_NOT_YET_RECEIVED','source':source,'bundle':dict(name='portable-r.zip',**desc),'conditions':2,'tokens_each':12,'real_rescale_waves_each':2}
    (out/'delivery.json').write_bytes(jbytes(delivery));print(json.dumps(delivery),flush=True)


def load_bundle(path):
    require(Path(path).stat().st_size<=MAX_BYTES,'bundle compressed-size cap')
    with zipfile.ZipFile(path) as z:
        names=z.namelist();require(len(names)==len(set(names)),'duplicate ZIP members')
        require(sum(i.file_size for i in z.infolist())<30*(1<<20),'bundle expanded-size cap')
        for name in names:
            p=PurePosixPath(name);require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,'safe bundle member')
        members={name:z.read(name) for name in names}
    index=json.loads(members.pop('index.json'));require(index['schema']=='issue68-portable-r/1','bundle schema')
    require(index['artifacts']=={n:descriptor(d) for n,d in members.items()},'every bundle member SHA/bytes')
    return members


def verify_segment(case,arrays,trace,o):
    bits=int(case['format']['state_bits']);df=int(case['format']['decay_fraction']);begin,end=case['begin'],case['end']
    current=arrays['state_trace'][0].astype(np.int64);units=arrays['state_units_trace'][0].astype(np.int16);vu=arrays['value_units'].astype(np.int16)
    initial=case['initial_snapshot'];epoch=initial['epoch'];version=initial['version'];position=initial['position'];sequence=initial['sequence']
    require(o.stamp(current,units,epoch,version,position,sequence)==initial,'true carried checkpoint snapshot')
    require(int(arrays['epoch_trace'][0])==epoch,'initial epoch array/snapshot equality')
    require(initial['version']==begin and initial['epoch']==0,'fixed boundary2 version/epoch')
    require(len(trace['tokens'])==end-begin,'continuous selected token count')
    expected_events=[];guard_rejections=0
    for local,t in enumerate(range(begin,end)):
        token=trace['tokens'][local];before=o.stamp(current,units,epoch,version,position,sequence)
        require(token['token']==t and token['before']==before,'causal predecessor/position')
        trial=current.copy();tu=units.copy();te=epoch;committed=False
        for n,attempt in enumerate(token['attempts']):
            require(n<=8 and attempt['attempt']==n and attempt['trial_old_sha256']==o.digest_array(trial) and attempt['units']==tu.astype(int).tolist() and attempt['epoch']==te,'trial state/units/epoch continuity')
            p,new,y,guard,maxima=o.oracle_step(trial,arrays['q'][local],arrays['k'][local],arrays['v'][local],arrays['decay'][local],arrays['beta'][local],tu,vu,bits,df)
            require(attempt['proposed_state_sha256']==o.digest_array(p) and attempt['guard_count_by_head']==guard and attempt['guard_count']==sum(guard),'complete-K proposal/range oracle')
            bad=np.asarray(guard)>0
            if bad.any():
                guard_rejections+=1;require(attempt['outcome']=='ABORT_RANGE' and attempt['output_work_performed'] is False,'guard before output publication')
                maxima.pop('output_dot');previous=trial.copy();oldu=tu.copy();trial,tu=o.rescale(trial,tu,bad);te+=1
                cells=trial.shape[1]*trial.shape[2];count=int(bad.sum());payload=cells*(bits//8)
                expected_events.append({'token':t,'after_attempt':n,'heads':np.flatnonzero(bad).tolist(),'trial_epoch':te,'old_units':oldu.astype(int).tolist(),'new_units':tu.astype(int).tolist(),
                    'old_trial_state_sha256':o.digest_array(previous),'recoded_trial_state_sha256':o.digest_array(trial),'state_scan_elements':count*cells,'RNE_elements':count*cells,
                    'nonexact_halvings':int(np.count_nonzero(previous[bad]-trial[bad]*2)),'state_read_bytes':count*payload,'state_write_bytes':count*payload,
                    'scale_descriptor_write_bytes':count,'epoch_descriptor_write_bytes':4,'published':False,'cause':'current token proposal range/I64 guard only'})
            else:
                require(attempt['outcome']=='COMMIT' and attempt['output_work_performed'] is True and n==len(token['attempts'])-1,'whole-token final commit')
                current=new;units=tu;epoch=te;version+=1;position+=1;after=o.stamp(current,units,epoch,version,position,sequence)
                expected={'old':before,'new':after,'output_sha256':o.digest_array(y),'publication':'state/output/units/epoch one token commit'}
                require(token['outcome']=='COMMITTED' and token['commit']==expected,'atomic state/output/scale/epoch commit')
                require(np.array_equal(arrays['state_trace'][local+1],current) and np.array_equal(arrays['state_units_trace'][local+1],units) and int(arrays['epoch_trace'][local+1])==epoch,'committed boundary oracle')
                require(np.array_equal(arrays['output_codes'][local],y) and np.array_equal(arrays['output_units'][local],units),'integer output/unit oracle');committed=True
            require(attempt['observed_absolute_max']==maxima and attempt['observed_signed_bits']=={k:max(1,int(v).bit_length()+1) for k,v in maxima.items()},'observed wide stages')
            if committed:break
        require(committed,'selected token must completely commit')
    require(trace['rescale_events']==expected_events and [e['token'] for e in expected_events]==[3,12],'two real rescale waves and full event costs')
    require(o.stamp(current,units,epoch,version,position,sequence)==case['final_snapshot'],'final carried snapshot')
    return {'id':case['id'],'tokens':end-begin,'real_rescale_waves':len(expected_events),'guard_rejections':guard_rejections,
            'final_snapshot':case['final_snapshot'],'complete_K_pythonint_oracle':True,'quality_accepted':False,'hardware_implemented':False}


def verify_members(members):
    o=oracle_module(members['source/receive_range.py']);selected=json.loads(members['selected.json'])
    require(selected['schema']=='issue68-portable-r/1' and len(selected['cases'])==2,'selected schema')
    require(selected['source']['receive_range_sha256']==ORACLE_SHA and descriptor(members['source/portable_r.py'])['sha256']==selected['source']['portable_r_sha256'],'collector/helper source binding')
    require(digest(members['provenance/source-manifest.json'])==selected['source_manifest_sha256'] and digest(members['provenance/range-manifest.json'])==selected['range_manifest_sha256'],'provenance manifests')
    rows=[]
    for bits,case in zip((16,32),selected['cases']):
        require(case['id']=='legacy.layer0-end8192.S'+str(bits)+'.D31.guard_rescale' and case['begin']==BEGIN and case['end']==END,'fixed selected conditions')
        require(case['format']['state_bits']==bits and case['format']['decay_fraction']==31,'selected format contract')
        for key in ('artifact','transaction_trace'):
            desc=case[key];require(descriptor(members[desc['name']])=={k:desc[k] for k in ('bytes','sha256')},'selected data index')
        with np.load(io.BytesIO(members[case['artifact']['name']]),allow_pickle=False) as z:arrays={n:z[n] for n in z.files}
        require(arrays['state_trace'].shape==(13,2,128,128) and arrays['output_codes'].shape==(12,2,128),'complete native head dimensions')
        require(arrays['state_trace'].dtype==np.dtype('int16' if bits==16 else 'int32') and arrays['state_units_trace'].dtype==np.int8 and arrays['epoch_trace'].dtype==np.uint32 and arrays['output_codes'].dtype==np.int64,'typed state/output/metadata')
        typed={'q':((12,2,128),np.int16),'k':((12,2,128),np.int16),'v':((12,2,128),np.int16),
               'beta':((12,2),np.uint16),'decay':((12,2),np.uint32),'value_units':((2,),np.int8),
               'state_units_trace':((13,2),np.int8),'epoch_trace':((13,),np.uint32),'output_units':((12,2),np.int8)}
        require(set(arrays)==set(typed)|{'state_trace','output_codes'},'exact selected array fields')
        for key,(shape,dtype) in typed.items():require(arrays[key].shape==shape and arrays[key].dtype==np.dtype(dtype),'typed selected '+key)
        require(case['selected_array_digests']=={n:o.digest_array(a) for n,a in arrays.items()},'selected array digests')
        rows.append(verify_segment(case,arrays,json.loads(members[case['transaction_trace']['name']]),o))
    return rows


def verify(bundle,out,negative=False):
    out=Path(out);require(not out.exists(),'refuse existing receipt');out.parent.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();members=load_bundle(bundle);rows=verify_members(members);negatives=[]
    if negative:
        for field in ('output_codes','epoch_trace'):
            mutated=dict(members);s=json.loads(mutated['selected.json']);case=s['cases'][1];name=case['artifact']['name']
            with np.load(io.BytesIO(mutated[name]),allow_pickle=False) as z:arrays={n:z[n] for n in z.files}
            arrays[field].flat[-1]+=1;mutated[name]=npz_bytes(arrays);case['artifact'].update(descriptor(mutated[name]))
            o=oracle_module(mutated['source/receive_range.py']);case['selected_array_digests'][field]=o.digest_array(arrays[field]);mutated['selected.json']=jbytes(s)
            path=out.parent/(out.stem+'.negative-'+field+'.zip');write_bundle(mutated,path);rehash=load_bundle(path)
            try:verify_members(rehash)
            except AssertionError as exc:negatives.append({'mutation':field,'rehashed_bundle':dict(name=path.name,**descriptor(path.read_bytes())),'SHA_passed':True,'semantic_rejected':True,'error':str(exc)})
            else:raise AssertionError('rehashed incorrect integer data accepted '+field)
    receipt={'status':'PASS_PORTABLE_INDEPENDENT_R','bundle':dict(path=str(Path(bundle).resolve()),**descriptor(Path(bundle).read_bytes())),
             'source':{'portable_r_sha256':sha(__file__),'receive_range_sha256':ORACLE_SHA},'rows':rows,'negative_checks':negatives,
             'seconds':time.monotonic()-start,'environment':{'python':platform.python_version(),'numpy':np.__version__},
             'limitations':'Only packaged real token[2,14) from carried boundary2. Does not requalify omitted prefix/full256 quality, FP compilers, memory/port/PPA or original model.'}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(jbytes(receipt));print(json.dumps({'status':receipt['status'],'conditions':len(rows)}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='action',required=True)
    c=subs.add_parser('collect')
    for name in ('legacy','integer','oracle','audit','chunks','out'):c.add_argument('--'+name,type=Path,required=True)
    c.add_argument('--binding',type=Path)
    v=subs.add_parser('verify');v.add_argument('--bundle',type=Path,required=True);v.add_argument('--out',type=Path,required=True);v.add_argument('--negative',action='store_true')
    a=p.parse_args()
    if a.action=='collect':collect(a.legacy,a.integer,a.oracle,a.audit,a.chunks,a.out,a.binding)
    else:verify(a.bundle,a.out,a.negative)


if __name__=='__main__':main()
