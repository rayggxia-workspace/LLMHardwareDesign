"""Independent integer oracle for bounded 8-key/D8 QK -> Softmax -> PV.

The EXP table is reconstructed from its mathematical generation formula.
Native source is parsed only to verify version equality, never as expected data.
No RTL outputs, internal memories or simulator results enter this model.
"""
import math
import re

QK_FACTOR=11585  # nearest-even integer of 2^15/sqrt(8), signed S16 positive.
EXP_MATH_TABLE=[round(math.exp(-16+i/64)*32768) for i in range(1025)]


def rne(value,shift):
    if shift==0:return value
    quotient,remainder=divmod(value,1<<shift)
    half=1<<(shift-1)
    return quotient+int(remainder>half or (remainder==half and quotient&1))


def clip_s16(value):
    return max(-32768,min(32767,value)),not(-32768<=value<=32767)


def pack(values,bits):
    return sum((int(v)&((1<<bits)-1))<<(bits*i) for i,v in enumerate(values))


def signed(value,bits):
    value&=(1<<bits)-1
    return value-(1<<bits) if value&(1<<(bits-1)) else value


def mathematical_exp(difference):
    if difference < -16384:return 0
    if difference >= 0:return 32768
    index,fraction=divmod(difference+16384,16)
    lo,hi=EXP_MATH_TABLE[index:index+2]
    return lo+rne((hi-lo)*fraction,4)


def validate_native_exp(text):
    parsed={int(k):int(v) for k,v in re.findall(r"11'd(\d+):exp_lut=16'd(\d+);",text)}
    expected=dict(enumerate(EXP_MATH_TABLE))
    if parsed!=expected:
        raise AssertionError('independent math EXP/source mismatch: '+repr([(k,expected.get(k),parsed.get(k)) for k in sorted(set(parsed)|set(expected)) if parsed.get(k)!=expected.get(k)][:8]))
    return {'all_equal':True,'nodes':1025,'formula':'round(exp(-16+i/64)*32768), i0..1024','node_rounding':'nearest ties even','source_is_not_oracle_input':True}


def softmax8(scores):
    assert len(scores)==8 and all(-32768<=v<=32767 for v in scores)
    maximum=max(scores)
    exponents=[mathematical_exp(v-maximum) for v in scores]
    total=sum(exponents)
    factor=(1<<44)//total
    assert 0<factor<=0xffffffff
    rounded=[rne(v*factor,30) for v in exponents]
    probabilities=[max(0,min(16384,v)) for v in rounded]
    return {'maximum':maximum,'score_sum':sum(scores),'score_sumsq':sum(v*v for v in scores),'exp':exponents,'exp_sum':total,'factor':factor,'prob':probabilities,'prob_sum':sum(probabilities),'saturated':rounded!=probabilities}


def a8(q,keys,values_by_channel):
    """keys[token][dimension], values_by_channel[channel][token], all S8Fin7."""
    assert len(q)==len(keys)==len(values_by_channel)==8
    assert all(len(row)==8 for row in keys+values_by_channel)
    assert all(-128<=v<=127 for row in [q]+keys+values_by_channel for v in row)
    qk_raw=[sum(q[d]*keys[t][d] for d in range(8)) for t in range(8)]
    qk_scaled=[v*QK_FACTOR for v in qk_raw]
    narrowed=[clip_s16(rne(v,19)) for v in qk_scaled]
    scores=[v for v,s in narrowed]
    n=softmax8(scores)
    pv_raw=[sum(n['prob'][t]*values_by_channel[c][t] for t in range(8)) for c in range(8)]
    output=[clip_s16(rne(v,11)) for v in pv_raw]
    final=[v for v,s in output]
    words=[pack(q,8),0,0,0]
    for matrix in (keys,values_by_channel):
        matrix_word=pack([v for row in matrix for v in row],8)
        words.extend((matrix_word>>(128*i))&((1<<128)-1) for i in range(4))
    # Probability source for M's A loader is aligned to four 128-bit words.
    stages={460:pack(scores,16),461:pack(n['exp'],16),464:pack(n['prob'],16),465:0,466:0,467:0,468:pack(final,16)}
    score_carriers=[pack(scores[4*h:4*h+4],32) for h in range(2)]
    output_carriers=[pack(final[4*h:4*h+4],32) for h in range(2)]
    stage_sat={'M_QK_readout':any(s for v,s in narrowed),'N_softmax':n['saturated'],'M_PV_readout':any(s for v,s in output)}
    return {'qk_raw':qk_raw,'qk_scaled':qk_scaled,'scores':scores,'softmax':n,'pv_raw':pv_raw,'output':final,'stage_saturated':stage_sat,'done_saturated':any(stage_sat.values()),'done_error':False,'ingress_words':words,'S_words':stages,'M_QK_op5_carriers':score_carriers,'M_PV_op5_carriers':output_carriers}
