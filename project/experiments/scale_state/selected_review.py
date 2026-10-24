"""Portable review of selected Issue66 integer evidence.

Imports only the two SHA-pinned independent receivers, never producer kernels.
Replays two complete32-step integer states and two complete-hidden consumer
paths from already encoded upstream data. This does not re-prove original
capture, down GEMM/weight compiler, full model quality, integer norm or PPA.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import time
import traceback
import zipfile

import numpy as np

HELPERS={
 'project/experiments/scale_state/receive_state.py':'4a08cd4c4242c4a37ba000c21ed06f2ebf44b60c476df163ff28d5d664c83a86',
 'project/experiments/scale_state/consumer_receive.py':'678e2dc7939d09f7edb5e8e917f979c860d1be01769eb67b5a792587341c858b'}
STATE_KEYS={'q','k','v','beta','decay','state_initial','state_trace','output_codes','state_units','value_units'}
AUX_KEYS={'down.Ybase','next.W8','next.We','next.Ybase','next.raw_norm_weight','decode.down.acc','decode.down.e0'}|{'decode.reference.'+x for x in ('down','residual','sum','norm','projection','rows')}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def need(ok,label):
    if not ok:raise ValueError(label)


def resolve(root,name):
    path=(root/name).resolve()
    need(path.is_relative_to(root.resolve()),'path escaped selected root')
    return path


def load_npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}


def artifact(root,entry,subset=False):
    path=resolve(root,entry['path']);d=entry['artifact'] if subset else entry['original_artifact']
    need(path.stat().st_size==d['bytes'] and sha(path)==d['sha256'],'container SHA/size '+entry['path'])
    if subset:
        with zipfile.ZipFile(path) as z:
            need(len(z.namelist())==len(set(z.namelist())),'duplicate NPY members')
            need(set(z.namelist())==set(entry['members']),'selected member set')
            for name,desc in entry['members'].items():
                need(name.endswith('.npy') and '/' not in name and '\\' not in name,'unsafe NPY member')
                raw=z.read(name)
                need(len(raw)==desc['bytes'] and hashlib.sha256(raw).hexdigest()==desc['sha256'],'raw NPY SHA/size '+name)
    return path


def import_receivers(root,index,helpers_root):
    modules={};hashes={}
    need(set(index['sources'])==set(HELPERS),'independent helper source set')
    for name,wanted in HELPERS.items():
        need(index['sources'][name]==wanted,'unreviewed helper source SHA')
        path=(helpers_root or root)/name
        need(path.is_file() and sha(path)==wanted,'independent helper on disk SHA '+name)
        spec=importlib.util.spec_from_file_location('_portable_'+path.stem,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        modules[path.stem]=module;hashes[name]=wanted
    return modules,hashes


def selected_consumer(C,data,aux,row):
    """Only paths supportable by the actual selected inputs; no fake weights."""
    case,profile=row['case'],row['profile']
    need(case=='decode' and profile in ('tile16_delta_ACT8','delta_to_K128_ACT8'),'selected consumer scope')
    acc,e0,base=(aux[key] for key in ('decode.down.acc','decode.down.e0','down.Ybase'))
    R,H=acc.shape;need((R,H)==(32,2560),'full32decode complete hidden shape')
    need(acc.dtype==np.int64 and e0.dtype==np.int16 and base.dtype==np.int8,'encoded upstream formats')
    counts={'Fraction_delta_admissibility_terms':C.delta_check(acc,e0,base,data['outlet_delta'])}
    units=np.broadcast_to(base.astype(np.int16)[None],acc.shape)+np.repeat(data['outlet_delta'].astype(np.int16),16,axis=1)
    need(np.array_equal(units,data['outlet_units']),'outlet base plus tile delta')
    n,sat=C.quant_check(acc,e0,units,data['outlet_codes'],8);counts['Fraction_outlet_codes']=n
    if profile=='delta_to_K128_ACT8':
        need(data['transport_codes'].dtype==np.int8 and data['transport_units'].dtype==np.int8,'K128 transport dtype')
        counts['Fraction_K128_conversion']=C.k128_check(data['outlet_codes'],units,data['transport_codes'],data['transport_units'],data['K128_exponents'])
    else:
        need(data['transport_codes'].dtype==np.int8 and data['transport_units'].dtype==np.int16,'tile transport dtype')
        need(np.array_equal(data['transport_codes'],data['outlet_codes']) and np.array_equal(data['transport_units'],units),'tile transport value/unit')
        need(data['K128_exponents'].shape==(R,0),'unexpected K128 conversion')
    residual=C.float_bridge(aux['decode.reference.residual'])
    need(data['residual_S32Q20'].dtype==np.int32 and np.array_equal(residual,data['residual_S32Q20']),'all residual S32Q20 codes')
    common=np.minimum(data['transport_units'],-20)
    need(data['sum_units'].dtype==np.int16 and np.array_equal(common,data['sum_units']),'residual common unit')
    need(data['sum_acc64'].dtype==np.int64,'residual sum signed64')
    for ij in np.ndindex(acc.shape):
        left=C.binary_power(data['transport_units'][ij])*int(data['transport_codes'][ij])
        right=C.binary_power(-20)*int(residual[ij])
        need(C.binary_power(common[ij])*int(data['sum_acc64'][ij])==left+right,'Fraction exact residual sum')
        origin=int(common[ij])
        operands=(int(data['transport_codes'][ij])<<(int(data['transport_units'][ij])-origin),int(residual[ij])<<(-20-origin),int(data['sum_acc64'][ij]))
        need(all(-(1<<63)<=v<1<<63 for v in operands),'I64 residual operands/sum')
    counts['Fraction_residual_values']=int(acc.size)
    summed=C.real(data['sum_acc64'],common).astype(np.float32)
    need(data['sum_F32_bridge'].dtype==np.float32 and np.array_equal(summed,data['sum_F32_bridge']),'sum explicit FP32 bridge')
    norm=C.rms(summed,aux['next.raw_norm_weight'])
    need(data['norm_F32_bridge'].dtype==np.float32 and np.array_equal(norm,data['norm_F32_bridge']),'zero-centered full-hidden FP32 RMS recipe')
    source,a,ae,witness=C.encode(norm)
    need(np.array_equal(source,data['norm_source_S32Q20']) and np.array_equal(a,data['next.A8']) and np.array_equal(ae,data['next.Ae']),'all post-norm S32Q20/A8/exponent codes')
    counts.update(norm_A_codes=int(a.size),Fraction_norm_A_endpoints=witness)
    w,we=aux['next.W8'],aux['next.We'];need(w.shape==(16,H) and w.dtype==np.int8 and we.shape==(16,H//128) and we.dtype==np.int8,'selected next W8 compiler artifact format')
    na,nu,stat=C.linear_check(a,ae,w,we,C.fields(data,'next.'),full_python=True)
    counts.update({'next_'+k:v for k,v in stat.items()})
    final_unit=np.broadcast_to(aux['next.Ybase'].astype(np.int16)[None],na.shape)
    need(np.array_equal(final_unit,data['next.final_units']),'next output static scales')
    checks,final_sat=C.quant_check(na,nu,final_unit,data['next.final_ACT8'],8);counts['Fraction_next_final_codes']=checks
    upstream=C.real(acc,e0);outlet=C.real(data['outlet_codes'],units);transport=C.real(data['transport_codes'],data['transport_units'])
    metrics={'upstream_down_before_outlet_RQ_vs_native':C.metric(upstream,aux['decode.reference.down']),
      'down_after_outlet_RQ_vs_native':C.metric(outlet,aux['decode.reference.down']),
      'transport_requant_vs_outlet':C.metric(transport,outlet),'sum_vs_native':C.metric(summed,aux['decode.reference.sum']),
      'norm_vs_native':C.metric(norm,aux['decode.reference.norm']),
      'next_projection_vs_native':C.metric(C.real(na,nu),aux['decode.reference.projection']),
      'next_final_ACT8_vs_native':C.metric(C.real(data['next.final_ACT8'],final_unit),aux['decode.reference.projection'])}
    for name,values in metrics.items():
        for key,value in values.items():need(abs(row[name][key]-value)<=1e-11*max(1.,abs(value)),'selected metric '+name+'.'+key)
    need(row['costs']['integer_work']['saturation']==sat and row['next_final_RQ']['saturation']==final_sat,'selected saturation count')
    C.check_cost(row,R,H,row['costs']['source_down_full_K'],len(w),profile,data['transport_codes'])
    need(not row['integer_norm_implemented'] and not row['complete_next8192_projection'] and not row['full_model_quality_accepted'] and not row['hardware_performance_accepted'],'evidence boundary')
    # This is intentionally a memory-only wrong output, not a new file/rehash fixture.
    wrong=data['outlet_codes'][:1,:1].copy();old=int(wrong[0,0]);wrong[0,0]=old+1 if old<127 else old-1
    try:C.quant_check(acc[:1,:1],e0[:1,:1],units[:1,:1],wrong,8)
    except ValueError as exc:negative=str(exc)
    else:raise AssertionError('in-memory changed outlet escaped exact numeric check')
    return {'profile':profile,'status':'PASS','counts':counts,'metrics_recomputed':metrics,
      'in_memory_wrong_outlet_rejected':negative,
      'not_recomputed_metrics':['next_projection_vs_native_norm_same_W8A8','next_projection_vs_upstream_no_outlet_RQ','native_norm_W8A8_vs_native_projection'],
      'scope':'already encoded full-hidden down accumulator/scale -> outlet -> exact residual -> FP32 full-hidden norm bridge -> fresh A8K128 -> completeK next16 -> RQ; source down GEMM/calibration/W compiler/counterfactual references absent'}


def run(root,out,helpers_root=None):
    need(not out.exists(),'refuse existing receipt');started=time.monotonic()
    receipt={'status':'RUNNING','source_sha256':sha(Path(__file__)),'scope':__doc__,'states':[],'consumer':[],
      'environment':{'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform()}}
    try:
        index=json.loads((root/'selected.json').read_text(encoding='utf-8-sig'))
        need(index['schema']=='issue66-selected/1','selected schema')
        receipt['selected_index_sha256']=sha(root/'selected.json')
        modules,source_hashes=import_receivers(root,index,helpers_root);S=modules['receive_state'];C=modules['consumer_receive']
        receipt['independent_receivers']=source_hashes;receipt['integer_boundary_checks']=S.boundary_self_checks()
        need({x['record']['id'] for x in index['states']}=={'evaluation.S16.D15','evaluation.S32.D31'},'two selected actual state profiles')
        for entry in index['states']:
            path=artifact(root,entry,subset=True);data=load_npz(path);row=entry['record'];fmt=row['format']
            need(set(data)==STATE_KEYS,'selected state key set')
            need(row['integer_steps']==32 and row['role']=='independent evaluation','selected state stage/role')
            bits=int(fmt['state_bits']);lo=-32768 if bits==16 else -(1<<31);hi=32767 if bits==16 else 32767<<16
            for key in ('q','k','v'):need(data[key].dtype==np.int16,'selected S16 operand dtype')
            need(data['beta'].dtype==np.uint16 and data['decay'].dtype==np.dtype('uint16' if fmt['decay_fraction']==15 else 'uint32'),'selected unsigned gate dtype')
            need(data['state_initial'].dtype==np.dtype('int16' if bits==16 else 'int32') and data['output_codes'].dtype==np.int64,'selected initial/output dtype')
            need(data['state_units'].dtype==np.int8 and data['value_units'].dtype==np.int8,'selected exponent dtype')
            need(data['state_trace'].dtype==np.dtype('int16' if bits==16 else 'int32'),'selected state storage dtype')
            need(np.array_equal(data['state_units'],fmt['state_unit']) and np.array_equal(data['value_units'],fmt['value_unit']),'selected state exponent descriptors')
            y,states,counts,maxima,widths=S.integer_oracle(data['q'],data['k'],data['v'],data['beta'],data['decay'],data['state_initial'],data['value_units'],data['state_units'],lo,hi,
                wanted_output=data['output_codes'],wanted_states=data['state_trace'],decay_fraction=int(fmt['decay_fraction']))
            S.validate_commits(row,states,y,index['state_capture_manifest_sha256'])
            need(counts['state_saturations']==row['execution']['saturations'],'state saturation report')
            need(maxima==row['execution']['observed_absolute_max'],'all state stage maxima')
            wrong=copy.deepcopy(row);wrong['execution']['commits'][0]['version']+=1
            try:S.validate_commits(wrong,states,y,index['state_capture_manifest_sha256'])
            except AssertionError as exc:negative=str(exc)
            else:raise AssertionError('in-memory stale state commit escaped')
            receipt['states'].append({'id':row['id'],'status':'PASS','artifact_sha256':sha(path),'original_full_artifact':entry['original_artifact'],
                'counts':counts,'observed_absolute_max':maxima,'minimal_signed_bits':widths,'full_state_values':int(states.size),'full_output_values':int(y.size),
                'commit_events':32,'in_memory_wrong_commit_rejected':negative,
                'scope':'all32 integer recurrence and version/state/output commits; omitted float/calibration references not independently rechecked in this portable subset'})
        aux_entry=index['consumer']['auxiliary'];aux_path=artifact(root,aux_entry,subset=True);aux=load_npz(aux_path)
        need(set(aux)==AUX_KEYS,'consumer selected auxiliary key set')
        need(np.array_equal(aux['decode.reference.rows'],np.arange(128,160)),'actual selected decode positions')
        need({e['record']['profile'] for e in index['consumer']['samples']}=={'tile16_delta_ACT8','delta_to_K128_ACT8'},'two consumer samples')
        for entry in index['consumer']['samples']:
            path=artifact(root,entry);result=selected_consumer(C,load_npz(path),aux,entry['record']);result['artifact_sha256']=sha(path);receipt['consumer'].append(result)
        receipt['consumer_auxiliary_sha256']=sha(aux_path)
        receipt['status']='PASS';receipt['limitations']=['No reproof of omitted original native capture or model/weight calibration compilers.','No repeat of source down GEMM or absent counterfactual metrics.','R numerical quality metrics require omitted original float references; integer values and commits are replayed.','Norm in these two consumer samples is an explicit FP32 bridge; newer integer RMS experiments are outside this selected subset.','No model-quality acceptance, target cycles, RTL or PPA.']
    except Exception as exc:
        receipt.update(status='FAIL',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
    receipt['seconds']=time.monotonic()-started;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':receipt['status'],'state_profiles':len(receipt['states']),'consumer_profiles':len(receipt['consumer']),'seconds':receipt['seconds']}),flush=True)
    if receipt['status']!='PASS':raise SystemExit(1)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--helpers',type=Path,help='repository/capsule root containing the two project/experiments/... independent receiver paths; default root')
    a=p.parse_args();run(a.root,a.out,a.helpers)


if __name__=='__main__':main()
