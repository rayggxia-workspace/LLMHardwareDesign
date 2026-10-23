"""Declared fixed-point candidates. LUTs are explicit versioned inputs."""
from fixed import checked, sat, rne_shift, mul_radix7, mul_i16_i8, isqrt48, udiv_restoring, div_rne_unsigned


def silu_i16_f12(x,table,counts=None):
    checked(x,16)
    if len(table)!=257:
        raise ValueError("257 sigmoid entries required")
    index=(x >> 8)+128
    fraction=x & 255
    delta=table[index+1]-table[index]
    interpolated=table[index]+(mul_radix7(delta,fraction,16,8,counts,b_unsigned=True) >> 8)
    product=mul_radix7(x,interpolated,16,16,counts,b_unsigned=True)
    if counts is not None:
        counts["sigmoid_rom_reads"] += 2
    return sat(rne_shift(product,16),16,counts)


def rms_i16_f12(x,gamma_f14,eps_total,gain_numerator,table_free_counts=None):
    counts=table_free_counts
    checked(eps_total,48,False)
    if len(x)!=len(gamma_f14) or not x:
        raise ValueError("nonempty equal row/gamma lengths required")
    total=0
    for value in x:
        checked(value,16)
        total += mul_radix7(value,value,16,16,counts)
        checked(total,48,False)
    total=checked(total+eps_total,48,False)
    root=isqrt48(total,counts)
    inv,_=udiv_restoring(checked(gain_numerator,32,False),max(root,1),32,counts)
    output=[]
    for value,gamma in zip(x,gamma_f14):
        checked(gamma,16)
        xg=checked(mul_radix7(value,gamma,16,16,counts),32)
        wide=mul_radix7(xg,inv,32,32,counts,b_unsigned=True)
        # gain numerator was compiled as round(sqrt(N)*2**20).
        output.append(sat(rne_shift(wide,22),16,counts))
    return output,{"sum_u48":total,"sqrt_u24":root,"inverse_u32":inv}


def softmax_fixed(scores_f8,exp_table,probability_bits,mask=None,counts=None):
    if probability_bits not in (7,15) or len(exp_table)!=4097 or not scores_f8:
        raise ValueError("P7/P15 and 4097-entry exp table required")
    mask=[True]*len(scores_f8) if mask is None else mask
    if len(mask)!=len(scores_f8) or not any(mask):
        raise ValueError("empty or wrong mask")
    for score in scores_f8:
        checked(score,16)
    maximum=max(s for s,valid in zip(scores_f8,mask) if valid)
    numerators=[]
    for score,valid in zip(scores_f8,mask):
        difference=maximum-score
        value=exp_table[difference] if valid and difference<=4096 else 0
        numerators.append(value)
        if counts is not None:
            counts["exp_rom_reads"] += int(valid and difference<=4096)
            counts["exp_cutoff"] += int(valid and difference>4096)
    total=checked(sum(numerators),64,False)
    scale=(1 << probability_bits)-1
    result=[min(scale,div_rne_unsigned(
        mul_radix7(p,scale,32,16,counts,b_unsigned=True),total,64,counts)) for p in numerators]
    return result,{"sum_exp_u64":total,"sum_probability_int":sum(result),"probability_denominator":scale}


def recurrent_delta(q_f14,k_f14,v_f12,beta_f15,decay_f15,state_f20,counts=None):
    """One head, post-normalized q/k input; pure integer state update.

    A global output gated-RMS is outside this kernel. Its absence is explicit,
    not evidence of a full integer Gated DeltaNet/model.
    """
    kd,vd=len(k_f14),len(v_f12)
    if len(q_f14)!=kd or len(state_f20)!=kd or any(len(r)!=vd for r in state_f20):
        raise ValueError("state/query shape mismatch")
    if not 0<=beta_f15<=32768 or not 0<=decay_f15<=32768:
        raise ValueError("beta/decay must be UQ0.15 in [0,1]")
    for x in q_f14+k_f14+v_f12:
        checked(x,16)
    decayed=[[sat(rne_shift(mul_radix7(checked(s,32),decay_f15,32,16,counts,b_unsigned=True),15),32,counts)
              for s in row] for row in state_f20]
    delta=[]
    for j in range(vd):
        projection=0
        for i in range(kd):
            projection=checked(projection+mul_radix7(decayed[i][j],k_f14[i],32,16,counts),64)
        projection=sat(rne_shift(projection,14),32,counts)
        residual=checked((v_f12[j] << 8)-projection,33)
        # Explicit 33-bit residual; this is not the 32-bit requant RTL path.
        delta.append(sat(rne_shift(mul_radix7(residual,beta_f15,33,16,counts,b_unsigned=True),15),32,counts))
    state=[]
    for i in range(kd):
        state.append([sat(decayed[i][j]+rne_shift(mul_radix7(delta[j],k_f14[i],32,16,counts),14),32,counts)
                      for j in range(vd)])
    output=[]
    for j in range(vd):
        total=0
        for i in range(kd):
            total=checked(total+mul_radix7(state[i][j],q_f14[i],32,16,counts),64)
        output.append(sat(rne_shift(total,22),16,counts))
    return output,state
