"""Self-contained independent A16 integer oracle; no DUT output input."""
import math
import re

EXP=[round(math.exp(-16+i/64)*32768) for i in range(1025)]

def rne(v,s):
    if not s:return v
    q,r=divmod(v,1<<s);h=1<<(s-1)
    return q+int(r>h or (r==h and q&1))

def clip(v):return max(-32768,min(32767,v)),not(-32768<=v<=32767)
def pack(v,bits=16):return sum((x&((1<<bits)-1))<<(bits*i) for i,x in enumerate(v))
def root(n):
    if n<2:return n
    x=1<<((n.bit_length()+1)//2)
    while True:
        y=(x+n//x)//2
        if y>=x:return x
        x=y

def rms(x,g):
    rad=(sum(v*v for v in x)<<16)//8+(1<<16);rt=root(rad);factor=(1<<38)//rt
    values=[clip(rne(v*factor*gg,30)) for v,gg in zip(x,g)]
    return {'output':[v for v,s in values],'saturated':any(s for v,s in values),'radicand':rad,'root':rt,'factor':factor}

def exp_code(d):
    if d< -16384:return 0
    if d>=0:return 32768
    i,f=divmod(d+16384,16)
    return EXP[i]+rne((EXP[i+1]-EXP[i])*f,4)

def softmax(scores,count):
    ex=[exp_code(v-max(scores[:count])) for v in scores[:count]];factor=(1<<44)//sum(ex)
    values=[max(0,min(16384,rne(v*factor,30))) for v in ex]
    return {'count':count,'exp':ex+[0]*(8-count),'prob':values+[0]*(8-count),'factor':factor,'exp_sum':sum(ex),'saturated':False}

def projection(rows,columns,shift,factor=1):
    raw=[[sum(a*b for a,b in zip(row,col)) for col in columns] for row in rows]
    out=[[clip(rne(v*factor,shift)) for v in row] for row in raw]
    return {'raw':raw,'output':[[v for v,s in row] for row in out],'saturated':any(s for row in out for v,s in row)}

def rope(x,coeff):
    out=[];sat=False
    for i in range(0,8,2):
        c,s=coeff[i:i+2]
        for v in [x[i]*c-x[i+1]*s,x[i+1]*c+x[i]*s]:
            y,ss=clip(rne(v,14));out.append(y);sat|=ss
    return out,sat

def coefficients(position):
    result=[]
    for pair in range(4):
        angle=position/(10000**(2*pair/8))
        result.extend([round(math.cos(angle)*16384),round(math.sin(angle)*16384)])
    return result

def validate_exp_table(text):
    parsed={int(i):int(v) for i,v in re.findall(r"11'd(\d+):exp_lut=16'd(\d+);",text)}
    if parsed!=dict(enumerate(EXP)):raise AssertionError('independent EXP/source table mismatch')
    return {'nodes':1025,'all_equal':True,'math_formula':'round(exp(-16+i/64)*32768)','DUT_table_not_oracle_input':True}

def a16(x,gamma,wq,wk,wv,wo,coeff):
    assert len(x)==2 and len(coeff)==2 and all(len(v)==8 for v in x+coeff+[gamma])
    assert all(-32768<=v<=32767 for row in x+coeff+[gamma] for v in row)
    for w in [wq,wk,wv,wo]:assert len(w)==8 and all(len(c)==8 and all(-128<=v<=127 for v in c) for c in w)
    norm=[rms(row,gamma) for row in x];nn=[n['output'] for n in norm]
    q=projection(nn,wq,7);k=projection(nn,wk,7);v=projection(nn,wv,7)
    qr=[rope(q['output'][i],coeff[i]) for i in range(2)];kr=[rope(k['output'][i],coeff[i]) for i in range(2)]
    keys=[kr[0][0],kr[1][0]]+[[0]*8 for _ in range(6)]
    vals=[[v['output'][0][c],v['output'][1][c]]+[0]*6 for c in range(8)]
    qk=projection([r[0] for r in qr],keys,25,11585)
    sm=[softmax(qk['output'][i],i+1) for i in range(2)]
    pv=projection([n['prob'] for n in sm],vals,14)
    output=projection(pv['output'],wo,7)
    final=[[clip(a+b) for a,b in zip(output['output'][i],x[i])] for i in range(2)]
    input_words=[pack(x[0]),0,0,0,pack(x[1]),0,0,0]
    for w in [wq,wk,wv,wo]:
        flat=pack([a for col in w for a in col],8);input_words.extend((flat>>(128*i))&((1<<128)-1) for i in range(4))
    input_words.extend([pack(gamma),pack(coeff[0]),pack(coeff[1])])
    history={448+i:[word] for i,word in enumerate(input_words)}
    def store(addr,word):history.setdefault(addr,[]).append(word)
    for a in [482,483,518,519,522,523]:store(a,0)
    for i in range(2):store(480+i,pack(nn[i]))
    for base,result in [(488,q),(490,k),(492,v)]:
        for i in range(2):store(base+i,pack(result['output'][i]))
    for i in range(2):store(488+i,pack(qr[i][0]));store(490+i,pack(kr[i][0]))
    for i in range(8):store(496+i,pack(keys[i]));store(504+i,pack(vals[i]))
    for i in range(2):store(512+i,pack(qk['output'][i]));store(514+i,pack(sm[i]['exp']));store(516+i,pack(sm[i]['prob']));store(520+i,pack(pv['output'][i]));store(524+i,pack(output['output'][i]));store(528+i,pack([v for v,s in final[i]]))
    sats={'N_RMS':any(n['saturated'] for n in norm),'M_Q':q['saturated'],'M_K':k['saturated'],'M_V':v['saturated'],'E_RoPE':any(s for out,s in qr+kr),'M_QK':qk['saturated'],'N_Softmax':False,'M_PV':pv['saturated'],'M_Wo':output['saturated'],'E_residual':any(s for row in final for vv,s in row)}
    return {'norm':norm,'Q_plain':q['output'],'K_plain':k['output'],'V':v['output'],'Q_rotated':[r[0] for r in qr],'K_rotated':[r[0] for r in kr],'K_columns':keys,'V_columns':vals,'M_raw':[q['raw'],k['raw'],v['raw'],qk['raw'],pv['raw'],output['raw']],'M_outputs':[q['output'],k['output'],v['output'],qk['output'],pv['output'],output['output']],'scores':qk['output'],'softmax':sm,'context':pv['output'],'Wo':output['output'],'final':[[v for v,s in row] for row in final],'stage_saturated':sats,'done_saturated':any(sats.values()),'ingress_words':input_words,'S_write_history':history,'S_final':{a:ws[-1] for a,ws in history.items()}}
