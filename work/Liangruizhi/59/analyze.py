"""Post-run descriptive readback; no evaluation-based parameter selection."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/down_scale'))
from common import save,digest


def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    data=np.load(a.run/'capture02/capture.npz',allow_pickle=False);ints=np.load(a.run/'numeric04/integers.npz',allow_pickle=False)
    num=json.loads((a.run/'numeric04/numeric.json').read_text());summary=json.loads((a.run/'numeric04/summary.json').read_text())
    pairs=json.loads((a.run/'service04/pairs.json').read_text());cost=json.loads((a.run/'service04/service.json').read_text())
    chosen=['static_original32_max_8192_8192','dynamic_none_max_8192_8192','dynamic_none_max_128_8192','dynamic_none_max_128_128']
    rows=[]
    for pr in chosen:
        cases=[r for r in num if r['profile']==pr]
        rows.append({'profile':pr,'max_case_relative_rmse':max(r['after_final_RQ']['relative_rmse'] for r in cases),
            'heldout':[{k:r[k] for k in ['phase','before_final_RQ','after_final_RQ','A_zero_fraction','A_clip_count','required_signed_bits_for_this_scale_matrix']} for r in cases if r['text']=='heldout'],
            'mid_limb_cost_pairs':[p for p in pairs if p['profile']==pr and p['limb_cycles']==2]})
    # Exact format-admissible worst case for one output with the ACTUAL W8 codes.
    # This is synthetic format safety, not a captured model overflow observation.
    boundary=[];name='dynamic_none_max_128_128';qw=ints[name+'.W_i8'];ew=ints[name+'.W_e']
    for text in ['systems','arithmetic','heldout']:
        key=name+'.'+text+'.prefill';ea=ints[key+'.A_e'];worst=(0,None)
        for i in range(len(ea)):
            for j in range(16):
                units=ea[i].astype(np.int16)+ew[j].astype(np.int16);e0=int(np.min(units))
                bound=sum(127*int(np.sum(abs(qw[j,g*128:(g+1)*128].astype(np.int64))))*(1<<(int(unit)-e0)) for g,unit in enumerate(units))
                if bound>worst[0]:worst=(bound,(i,j,e0,units.tolist()))
        bound,(i,j,e0,units)=worst
        codes=(np.sign(qw[j].astype(np.int16))*127).astype(np.int8)
        # Positive sign-weight product maximizes the selected aligned output.
        parts=np.array([int(codes[g*128:(g+1)*128].astype(np.int64)@qw[j,g*128:(g+1)*128].astype(np.int64)) for g in range(64)],dtype=np.int64)
        acc=sum(int(v)<<(u-e0) for v,u in zip(parts,units))
        if acc!=bound:raise AssertionError('adversary bound')
        source=np.empty(8192,dtype=np.int64)
        regenerated=[]
        for g,e in enumerate(ea[i]):
            source[g*128:(g+1)*128]=codes[g*128:(g+1)*128].astype(np.int64)*(1<<(int(e)+20))
            need=(int(np.max(abs(source[g*128:(g+1)*128])))+126)//127
            regenerated.append(-20+max(0,(need-1).bit_length()) if need else -20)
        if regenerated!=ea[i].tolist() or np.max(abs(source))>=2**31:raise AssertionError('adversary source scale domain')
        boundary.append({'text':text,'row':i,'output':j,'exact_weight_aware_aligned_max':bound,'signed_bits':bound.bit_length()+1,
            'exceeds_i32':bound>2**31-1,'source32_valid':True,'dynamic_exponents_reproduced':True,
            'observed_capture_max':max(r['observed_max_abs_aligned_acc'] for r in num if r['profile']==name and r['text']==text)})
    cal_stats=[]
    for text in ['calibration','cal_science','cal_code','cal_dialogue']:
        x=data[text+'.A'];cal_stats.append({'text':text,'max_abs':float(np.max(abs(x))),
            'median_abs':float(np.median(abs(x))),'max_row':int(np.unravel_index(np.argmax(abs(x)),x.shape)[0])})
    result={'status':'PASS','scope':'post-hoc descriptive analysis and synthetic format bound, no new heldout tuning or quality acceptance',
        'input_sha256':{str(p.relative_to(a.run)):digest(p) for p in [a.run/'capture02/capture.npz',a.run/'numeric04/integers.npz',a.run/'numeric04/numeric.json',a.run/'service04/service.json']},
        'source_sha256':digest(__file__),'chosen':rows,'weight_aware_adversarial_bound':boundary,'calibration_stats':cal_stats,
        'numerical_screen_pass_profiles':[r['name'] for r in summary['profiles'] if r['local_screen_passed']],
        'all_profiles_cost_fraction_range':[min(r['cycle_reduction_fraction'] for r in pairs),max(r['cycle_reduction_fraction'] for r in pairs)],
        'all_output_saturations':sum(r['output_saturation_count'] for r in num),'all_early_rounding_mismatches':sum(r['early_group_RQ_mismatches'] for r in num),
        'mid_limb_rows4_cost_details':[{k:r[k] for k in ['profile','cycles','metadata_buffer_bytes','wide_accumulator_bytes','partial_staging_bytes','wide_updates','bytes','busy']} for r in cost if r['profile']in chosen and r['rows']==4 and r['limb_cycles']==2 and r['placement']=='near' and r['batch']==1 and r['policy']=='critical']}
    save(a.output,result);print(json.dumps({'screen_pass':result['numerical_screen_pass_profiles'],'boundary':boundary}))


if __name__=='__main__':main()
