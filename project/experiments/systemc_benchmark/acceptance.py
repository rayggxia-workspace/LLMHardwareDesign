"""Acceptance is independent of SystemC timing/energy estimation code.

Unknown energy, synthetic coefficients and unequal workloads cannot pass the
FPGA target. Platform-native best validated configurations are retained.
"""
import math


def assess(ours,peer):
    reasons=[]
    fields=('checkpoint_sha256','token_ids_sha256','batch','prompt_tokens','decode_steps','quality_gate_id')
    for field in fields:
        if field not in ours or field not in peer or ours[field]!=peer[field]:
            reasons.append('workload/quality mismatch: '+field)
    for label,r in [('ours',ours),('peer',peer)]:
        if not r.get('numeric_passed'):reasons.append(label+': numerical qualification missing')
        if not r.get('best_mapping_evidence'):reasons.append(label+': best mapping/search evidence missing')
        if not r.get('complete_energy_scope'):reasons.append(label+': energy coverage incomplete')
        if not r.get('energy_calibration_sha256'):reasons.append(label+': calibrated energy missing')
        if r.get('coefficient_class') in (None,'synthetic','unknown'):reasons.append(label+': unqualified energy coefficients')
        for key in ('decode_tokens_per_second','joules_per_decode_token'):
            v=r.get(key)
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<=0:
                reasons.append(label+': invalid '+key)
    if ours.get('timing_backend')!='systemc':reasons.append('ours: actual SystemC time required')
    if not peer.get('native_optimized_configuration'):reasons.append('peer: native optimized configuration missing')
    if reasons:return {'passed':False,'comparable':False,'reasons':reasons}
    speed=ours['decode_tokens_per_second']/peer['decode_tokens_per_second']
    energy=ours['joules_per_decode_token']/peer['joules_per_decode_token']
    return {'passed':speed>=1 and energy<=1,'comparable':True,'speed_ratio':speed,
            'energy_ratio':energy,'reasons':([] if speed>=1 else ['slower than optimized FPGA'])+
            ([] if energy<=1 else ['higher J/token than optimized FPGA']),
            'boundary':'point estimates only; final comparison must also disclose uncertainty and energy scope'}
