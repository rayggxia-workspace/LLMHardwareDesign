"""Verify archived precision/RTL evidence and summarize its exact boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
from report import contents


def summarize(root):
    runs={};members=0
    for tag in ('17','18','19'):
        files=contents(root/('run'+tag));members+=len(files)-1
        q=json.loads(files['quality/precision.json'])
        rtl=json.loads(files['results/precision-rtl.json'])
        assert q['passed'] and rtl['passed']
        assert q['source_commit']==rtl['source_commit']
        assert not q['authoritative_INT8_checkpoint']
        assert q['oracle_checks']['RNE_coefficient_checks']==650
        assert rtl['G']['packets']==q['G_frames']
        assert rtl['requant']['frames']==q['requant_frames']
        assert hashlib.sha256(files['quality/precision.json']).hexdigest()==rtl['input_sha256']['precision.json']
        for name in ('g-real-vectors.txt','requant-vectors.txt'):
            assert rtl['input_sha256'][name]==q['retained_artifacts'][name]['sha256']
        runs[tag]=(q,rtl)
    q,rtl=runs['19'];previous=runs['18'][0]
    assert q['checkpoint_sha256']==previous['checkpoint_sha256']
    assert q['input_ids']==previous['input_ids']
    assert q['profiles']==previous['profiles'],'same quality experiment changed unexpectedly'
    assert len(q['profiles'])==9 and len(q['integer_FFN'])==4
    points=sum(min(4,len(ids[0])) for ids in q['input_ids'])
    profiles=[]
    for p in q['profiles']:
        match=sum(v['top1_fraction']*min(4,len(ids[0])) for v,ids in zip(p['metrics_vs_W8'],q['input_ids']))
        profiles.append(dict(name=p['name'],short_text_PPL_diagnostic=p['loss']['perplexity'],
            min_logit_cosine_vs_W8=min(v['cosine'] for v in p['metrics_vs_W8']),
            top1_matches_vs_W8=int(round(match)),selected_positions=points,
            hardware_profile_available=p['hardware_profile_available'],
            G_observed_counts={k:sum(v[k] for v in p['G_stats'].values())
                               for k in next(iter(p['G_stats'].values()),{})}))
    ffn=[]
    for sample in q['integer_FFN']:
        coverage=sample['RTL_conversion_coverage']
        assert set(coverage)=={'gate_to_G','up_to_G','native_gated_Mid_to_down','ungated_G_wide_product_Mid_to_down'}
        assert coverage['gate_to_G']['saturated']==sample['gate_conversion']['saturated']
        assert coverage['up_to_G']['saturated']==sample['up_conversion']['saturated']
        for row in sample['rows']:
            bounded=row['bounded_partial_schedule']
            assert row['K128_tiling_bit_exact'] and bounded['bit_exact']
            assert bounded['max_active_outputs_per_P']<=64 and bounded['Mid_buffer_values']==128
            assert bounded['psum_read_bytes']==bounded['psum_write_bytes']==870400
            assert bounded['requires_new_context_save_reload_service']
            assert not row['hardware_qualified']
        ffn.append(dict(tag=sample['tag'],gate_saturations=sample['gate_conversion']['saturated'],
            up_saturations=sample['up_conversion']['saturated'],product_saturations=sample['G_product_saturated'],
            rows=sample['rows'],RTL_conversion_coverage=coverage))
    for study in q['storage']:
        assert len(study['profiles'])==4
        assert all(p['capacity_pass'] for p in study['profiles'][1]['capacity'])
    result=dict(passed=True,packages=3,verified_members=members,source_commit=q['source_commit'],
        Slurm_job=q['job'],quality_scope=q['scope'],texts=len(q['texts']),
        loss_tokens=q['FP32']['tokens'],selected_positions=points,
        FP32_short_text_PPL=q['FP32']['perplexity'],W8_short_text_PPL=q['W8_float_activation']['loss']['perplexity'],
        profiles=profiles,FFN=ffn,storage=q['storage'],RTL=rtl,
        native_full_model_tokens_s=None,energy_J_token=None,
        full_integer_LLM=False,production_RTL_modified=False,
        SystemC_new_precision_profile_admitted=False)
    (root/'summary.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    return {k:result[k] for k in ('passed','packages','verified_members','source_commit','Slurm_job')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    print(json.dumps(summarize(p.parse_args().root)))
