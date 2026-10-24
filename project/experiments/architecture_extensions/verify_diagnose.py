"""Independent receiver for Granite route-discontinuity diagnostics.

Never imports the producer. Verifies observations, not acceptance of the failed
reference; counterfactual fixed routing remains a changed algorithm.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def require(value,label):
    if not value:
        raise ValueError(label)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(),parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON '+x)))


def save(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def numbers_close(actual,expected,label):
    if isinstance(expected,dict):
        require(isinstance(actual,dict) and set(actual)==set(expected),label+' keys')
        for k,v in expected.items():numbers_close(actual[k],v,label+'.'+k)
    elif isinstance(expected,list):
        require(isinstance(actual,list) and len(actual)==len(expected),label+' list')
        for i,(a,b) in enumerate(zip(actual,expected)):numbers_close(a,b,label+'.'+str(i))
    elif isinstance(expected,float):
        require(type(actual) in (float,int) and math.isfinite(actual)
                and math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-12),label+' numeric mismatch')
    else:
        require(type(actual)==type(expected) and actual==expected,label+' mismatch')


def independent_error(value,reference):
    a=np.asarray(value,dtype=np.float64);b=np.asarray(reference,dtype=np.float64)
    require(a.shape==b.shape and a.size>0 and np.isfinite(a).all() and np.isfinite(b).all(),'finite matching error operands')
    diff=a-b
    numerator=math.sqrt(float(np.sum(diff*diff,dtype=np.float64)))
    denominator=max(math.sqrt(float(np.sum(b*b,dtype=np.float64))),1e-30)
    return {'relative_l2':numerator/denominator,'max_abs':float(np.max(np.abs(diff)))}


def validate_native_topk(logits,ids):
    logits=np.asarray(logits);ids=np.asarray(ids)
    require(logits.ndim==2 and ids.shape==(logits.shape[0],8) and logits.shape[1]==40,'router complete40/top8 shape')
    require(np.isfinite(logits).all() and ids.dtype.kind in 'iu','router finite/integer')
    require(np.all(ids>=0) and np.all(ids<40),'expert index domain')
    selected=np.take_along_axis(logits,ids,axis=1)
    require(np.all(selected[:,:-1]>=selected[:,1:]),'native top8 score order')
    # Native torch.topk is allowed to choose any tied expert at the cutoff. It
    # must have the same score multiset as the true largest eight, with no duplicates.
    largest=np.partition(logits,32,axis=1)[:,32:]
    require(np.array_equal(np.sort(selected,axis=1),np.sort(largest,axis=1)),'native selected scores are top8')
    require(all(len(set(row.tolist()))==8 for row in ids),'unique selected experts')


def validate_weights(logits,ids,weights):
    require(weights.shape==ids.shape and np.isfinite(weights).all() and np.all(weights>=0),'routing weight shape/finite')
    selected=np.take_along_axis(np.asarray(logits,dtype=np.float64),ids,axis=1)
    exp=np.exp(selected-np.max(selected,axis=1,keepdims=True));expected=exp/np.sum(exp,axis=1,keepdims=True)
    require(np.max(np.abs(weights.astype(np.float64)-expected))<=2e-7,'native FP32 softmax weight consistency')


def route_comparison(full_logits,full_ids,other_logits,other_ids):
    full_logits=np.asarray(full_logits);other_logits=np.asarray(other_logits)
    rows=full_ids.shape[0]
    a=np.zeros((rows,40),dtype=np.bool_);b=np.zeros_like(a)
    np.put_along_axis(a,full_ids,True,axis=1);np.put_along_axis(b,other_ids,True,axis=1)
    replaced=np.count_nonzero(a!=b,axis=1)//2
    fs=np.partition(full_logits,(31,32),axis=1);os=np.partition(other_logits,(31,32),axis=1)
    # The published margins/maxdiff were recorded in captured FP32. Compute in
    # float64, then explicitly round once to that format; do not loosen the
    # 2.98e-8 boundary into a broad report comparison tolerance.
    fm=(fs[:,32].astype(np.float64)-fs[:,31].astype(np.float64)).astype(full_logits.dtype).astype(np.float64)
    om=(os[:,32].astype(np.float64)-os[:,31].astype(np.float64)).astype(other_logits.dtype).astype(np.float64)
    changed=np.flatnonzero(replaced)
    return {'set_changed_tokens':int(len(changed)),
        'ordered_changed_tokens':int(np.count_nonzero(np.any(full_ids!=other_ids,axis=1))),
        'logits_error':independent_error(other_logits,full_logits),
        'minimum_full_top8_margin':float(np.min(fm)),'minimum_other_top8_margin':float(np.min(om)),
        'changes':[{'position':int(i),'replaced_experts':int(replaced[i]),
            'full_ids':full_ids[i].tolist(),'other_ids':other_ids[i].tolist(),
            'full_margin':float(fm[i]),'other_margin':float(om[i]),
            'logit_max_abs':float(np.asarray(np.max(np.abs(full_logits[i].astype(np.float64)-other_logits[i].astype(np.float64))),dtype=full_logits.dtype))}
            for i in changed]}


def verify(args):
    require(not args.out.exists(),'refuse overwrite')
    binding=read(args.binding)
    require(binding.get('commit') and binding.get('verify_diagnose_sha256')==sha(__file__),'receiver source binding')
    manifest=read(args.diagnostic/'manifest.json');original=read(args.capture/'manifest.json')
    require(manifest.get('kind')=='granite_route_diagnostic' and manifest.get('status')=='EXECUTED_DIAGNOSTIC','diagnostic executed scope')
    require(manifest['producer_sha256']==sha(args.producer)==manifest['source']['granite_diagnose_sha256'],'actual diagnostic producer source SHA')
    require(original['source']['granite_sha256']==sha(args.capture_producer),'actual original capture producer source SHA')
    require(sha(args.capture/'manifest.json')==manifest['original_capture_manifest_sha256'],'original manifest SHA')
    require(original['status']==manifest['original_capture_status']=='FAIL','retain original capture FAIL')
    require(original['correctness_gate']==manifest['original_correctness_gate'],'unchanged original failure gate')
    require(original['cases']==manifest['original_case_failures'],'unchanged complete original failure chain')
    require(original['correctness_gate']=={'relative_l2_max':2e-4,'max_abs_max':2e-3,'passed':False},'original gate unchanged')
    require(original['model_revision']==manifest['model_revision'],'original model revision')
    for folder,source in ((args.diagnostic,manifest),(args.capture,original)):
        for artifact in source['artifacts']:
            path=folder/artifact['path']
            require(path.stat().st_size==artifact['bytes'] and sha(path)==artifact['sha256'],'actual artifact SHA '+str(path))
    report=read(args.diagnostic/'report.json')
    require(report['original_capture_status']=='FAIL' and report['unchanged_gate']=={'relative_l2_max':2e-4,'max_abs_max':2e-3},'report retains failure')
    require(report['source_tokens']==original['cases']['evaluation']['tokens'],'original fixed input tokens')
    profiles=('full','cached64','chunk16','chunk16_fixed_ids')
    arrays=np.load(args.diagnostic/'routes.npz',allow_pickle=False)
    checked=0
    for profile in profiles:
        run=report['runs'][profile]
        require(run['tokens']==72 and run['counterfactual']==(profile=='chunk16_fixed_ids'),'counterfactual identity cannot become native reference')
        spans=([[0,72]] if profile=='full' else [[0,64]]+[[i,i+1] for i in range(64,72)]
               if profile=='cached64' else [[i,min(72,i+16)] for i in range(0,72,16)])
        require(run['cache_spans']==spans,'original complete profile spans')
        lm=arrays[profile+'.lm_logits']
        require(lm.shape==(72,49155),'complete LM logits')
        numbers_close(run['logits_vs_full'],independent_error(lm,arrays['full.lm_logits']),profile+' final logits')
        for layer in range(32):
            prefix=profile+'.'+str(layer)+'.'
            logits=arrays[prefix+'logits'];ids=arrays[prefix+'ids'];native=arrays[prefix+'native_ids']
            require(logits.shape==(72,40),'complete router token count')
            validate_native_topk(logits,native)
            if profile=='chunk16_fixed_ids':
                require(np.array_equal(ids,arrays['full.'+str(layer)+'.ids']),'fixed-ID control exactly uses full-run IDs')
            else:
                require(np.array_equal(ids,native),'native profiles cannot silently force expert IDs')
            validate_weights(logits,ids,arrays[prefix+'weights'])
            for key in ('router_input','moe_output','hidden'):
                value=arrays[prefix+key]
                require(value.shape==(72,1536) and np.isfinite(value).all(),'complete finite layer data '+prefix+key)
            checked+=1
    comparisons={}
    for profile in profiles[1:]:
        expected=[]
        for layer in range(32):
            p='full.'+str(layer)+'.';q=profile+'.'+str(layer)+'.'
            record={'layer':layer,**route_comparison(arrays[p+'logits'],arrays[p+'ids'],arrays[q+'logits'],arrays[q+'ids']),
                'router_input_error':independent_error(arrays[q+'router_input'],arrays[p+'router_input']),
                'moe_output_error':independent_error(arrays[q+'moe_output'],arrays[p+'moe_output']),
                'layer_hidden_error':independent_error(arrays[q+'hidden'],arrays[p+'hidden'])}
            expected.append(record)
        result={'layers':expected,'first_set_change_layer':next((r['layer'] for r in expected if r['set_changed_tokens']),None),
                'total_layer_token_set_changes':sum(r['set_changed_tokens'] for r in expected)}
        numbers_close(report['comparisons'][profile],result,profile+' full route comparison')
        comparisons[profile]=result
    capture=np.load(args.capture/'capture.npz',allow_pickle=False)
    links={'original_layer0_input':independent_error(arrays['full.0.router_input'],capture['evaluation_x']),
           'original_last_LM_logits':independent_error(arrays['full.lm_logits'][-1],capture['evaluation_logits_last'])}
    for link in links.values():
        require(link['relative_l2']<=2e-4 and link['max_abs']<=2e-3,'actual original floating tensor link')
    changed=[r for r in comparisons['chunk16']['layers'] if r['set_changed_tokens']]
    result={'audit_status':'DIAGNOSTIC_WITNESS_VERIFIED','checked_profile_layers':checked,
        'original_capture_status':'FAIL','original_correctness_gate':original['correctness_gate'],
        'counterfactual_is_reference':False,'chunk_reference_accepted':False,'quality_accepted':False,
        'first_native_chunk_set_change':changed[0] if changed else None,
        'native_chunk_layer_token_changes':comparisons['chunk16']['total_layer_token_set_changes'],
        'cached_layer_token_changes':comparisons['cached64']['total_layer_token_set_changes'],
        'LM_errors':{p:report['runs'][p]['logits_vs_full'] for p in profiles},'original_tensor_links':links,
        'verification_scope':'all128 native top8 score sets/order and weights; forced-ID identities; all96 comparison records; final LM errors; actual source/artifact SHA',
        'limits':'observational failure localization; not proof of one kernel cause, integer model quality, or hardware timing',
        'source':{'commit':binding['commit'],'verify_diagnose_sha256':sha(__file__),
                  'diagnostic_manifest_sha256':sha(args.diagnostic/'manifest.json'),
                  'original_capture_manifest_sha256':sha(args.capture/'manifest.json'),
                  'producer_sha256':sha(args.producer),'capture_producer_sha256':sha(args.capture_producer)}}
    args.out.mkdir(parents=True);save(args.out/'audit.json',result)


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ('diagnostic','capture','producer','capture-producer','binding','out'):
        p.add_argument('--'+name,type=Path,required=True)
    verify(p.parse_args())


if __name__=='__main__':
    main()
