"""Explicit Q24 transcendental candidate; never an IEEE FP32 equivalence claim.

Four scalar functions use 1/128 linear interpolation. ROM constants are
generated at build time and synthesized as standard-cell logic, not SRAM.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

Q=1<<24
STEP=Q//128
LOW=-16*Q
HIGH=16*Q
FUNCTIONS=('exp','sigmoid','softplus','gelu')

def f(op,x):
    if op==0:return math.exp(min(x,8))
    if op==1:return 1/(1+math.exp(-x))
    if op==2:return max(x,0)+math.log1p(math.exp(-abs(x)))
    return .5*x*(1+math.tanh(.7978845608028654*(x+.044715*x*x*x)))

def rounded(n,bits):
    q,r=divmod(abs(n),1<<bits)
    q+=r>(1<<(bits-1)) or (r==(1<<(bits-1)) and q&1)
    return -q if n<0 else q

TABLE=[[round(f(op,-16+i/128)*Q) for i in range(4097)] for op in range(4)]

def candidate(op,x):
    if not -(1<<39)<=x<(1<<39):raise ValueError('Q24 input overflow')
    if op==0 and x>8*Q:raise ValueError('exp argument above supported +8')
    if x<=LOW:return 0
    if x>=HIGH:return Q if op==1 else x
    idx,frac=divmod(x-LOW,STEP)
    a,b=TABLE[op][idx:idx+2]
    return a+rounded((b-a)*frac,17)

def generate(out):
    out.mkdir(parents=True,exist_ok=True)
    # A single shared ROM address space, with the function selected in the
    # address. Unknown/unsupported inputs raise the hardware fault flag.
    rows=['%010x'%(v&((1<<40)-1)) for values in TABLE for v in values]
    (out/'special-lut.hex').write_text('\n'.join(rows)+'\n')
    rtl='''`timescale 1ps/1ps
module special_lut_q24(input logic clk, reset, valid,
 output logic ready, input logic [1:0] opcode,
 input logic signed [39:0] x, output logic out_valid,
 input logic out_ready, output logic signed [39:0] y,
 output logic fault);
 logic signed [39:0] rom [0:16387];
 initial $readmemh("special-lut.hex",rom);
 logic [1:0] state, op;
 logic signed [39:0] value, a, b;
 logic [16:0] fraction;
 logic [14:0] address;
 logic signed [57:0] product;
 logic signed [40:0] difference;
 logic signed [57:0] magnitude, rounded_value;
 assign ready=!reset && state==0;
 assign out_valid=!reset && state==3;
 always_comb begin
   difference=$signed({b[39],b})-$signed({a[39],a});
   product=difference*$signed({1'b0,fraction});
   magnitude=product<0 ? -product : product;
   rounded_value=(magnitude>>>17)+((magnitude[16:0]>17'd65536)||
     (magnitude[16:0]==17'd65536 && magnitude[17]));
   if(product<0) rounded_value=-rounded_value;
 end
 always_ff @(posedge clk) begin
   if(reset) begin state<=0;op<=0;value<=0;a<=0;b<=0;fraction<=0;
     address<=0;y<=0;fault<=0;end
   else case(state)
     0:if(valid) begin
       op<=opcode;value<=x;fault<=0;
       if(opcode==0 && x>40'sd134217728) begin y<=0;fault<=1;state<=3;end
       else if(x<=-40'sd268435456) begin y<=0;state<=3;end
       else if(x>=40'sd268435456) begin y<=opcode==1?40'sd16777216:x;state<=3;end
       else begin address<=15'(int'(opcode)*4097+int'((x+40'sd268435456)>>>17));
         fraction<=x[16:0];state<=1;end
     end
     1:begin a<=rom[address];b<=rom[address+1'b1];state<=2;end
     2:begin y<=40'($signed(a)+rounded_value);state<=3;end
     3:if(out_ready) state<=0;
   endcase
 end
endmodule
'''
    (out/'special_lut_q24.sv').write_text(rtl)
    return {p.name:sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in ('.sv','.hex')}

def samples(directory,out):
    commands=[];groups=[];errors=[]
    for path in sorted(directory.glob('*.json')):
        data=json.loads(path.read_bytes())
        for index,s in enumerate(data.get('samples',[])):
            kind=s['kind'];a=s['inputs'];truth=s['outputs'];start=len(commands);got=[];ref=[]
            def call(op,x):
                xi=round(x*Q);yi=candidate(op,xi);commands.append((op,xi,yi));return yi/Q
            if kind in ('gelu','sigmoid'):
                for gate,up,y in zip(a['gate'],a['up'],truth['result']):
                    approx=call(3 if kind=='gelu' else 1,gate/65536)
                    got.append(rounded(round(approx*65536)*up,16) if kind=='gelu' else round(approx*up));ref.append(y)
            elif kind=='recurrent_factors':
                deltas=[call(2,x*a['a_scale']+bias) for x,bias in zip(a['a'],a['dt_bias'])]
                for log,delta,y in zip(a['a_log'],deltas,truth['decay']):
                    value=call(0,log);got.append(round(call(0,-value*delta)*65536));ref.append(round(y*65536))
                if a['b'] is not None:
                    for x,y in zip(a['b'],truth['beta']):got.append(round(call(1,x)*65536));ref.append(round(y*65536))
            elif kind=='router':
                scores=a['scores_q16'];chosen=sorted(range(len(scores)),key=lambda i:(-scores[i],i))[:s['shape']['top']]
                assert chosen==truth['selected']
                coeff=[call(0,(scores[i]-scores[chosen[0]])/65536) for i in chosen]
                got=[round(x/sum(coeff)*65536) for x in coeff];ref=truth['probability_q16']
            elif kind=='recurrent_norm_gate':
                # Isolate only the captured gate nonlinear function. Full
                # normalization and state arithmetic remain separate components.
                if 'gate' not in a:continue
                for x in a['gate']:
                    got.append(round(call(1,x)*65536));ref.append(round(f(1,x)*65536))
            else:continue
            if len(commands)==start:continue
            delta=[abs(x-y) for x,y in zip(got,ref)]
            groups.append(dict(capture=path.name,capture_sha256=sha256(path.read_bytes()).hexdigest(),
                sample=index,kind=kind,start=start,end=len(commands)))
            errors.append(dict(capture=path.name,sample=index,kind=kind,elements=len(delta),
                max_abs_q16=max(delta,default=None),mismatches=sum(x!=0 for x in delta),
                scope='sampled composite diagnostic; not full-model error bound'))
    # Endpoint, tie, interpolation and tail checks independent of model samples.
    for op in range(4):
        start=len(commands)
        for x in (-32,-16,-15.999,-8,-1.00390625,-.00390625,0,.00390625,1.00390625,7.999,8):
            xi=round(x*Q);commands.append((op,xi,candidate(op,xi)))
        if op!=0:
            for x in (15.999,16,32):commands.append((op,x*Q if isinstance(x,int) else round(x*Q),candidate(op,round(x*Q))))
        groups.append(dict(kind='synthetic_'+FUNCTIONS[op],start=start,end=len(commands)))
    (out/'commands.txt').write_text('\n'.join('%d %010x %010x'%(op,x&((1<<40)-1),y&((1<<40)-1)) for op,x,y in commands)+'\n')
    (out/'groups.json').write_text(json.dumps(groups,indent=2)+'\n')
    (out/'numeric-diagnostics.json').write_text(json.dumps(dict(errors=errors,
        limitations=['Q24 candidate; no IEEE FP32 equivalence or model-accuracy acceptance',
        'Composite checks still use Python multiply/divide; measured RTL scope is four transcendental primitives',
        'Recurrent Softplus ingress uses captured a, scale and dt_bias; multiply/add remain Python in composite diagnostic',
        'Captured ranges and max errors are samples, not global probabilistic confidence limits'],
        contract=dict(input_output='signed40/Q24',step='1/128',interpolation='nearest ties even',
            exp_domain=[-16,8],other_table_domain=[-16,16],tail='exp lower:0; sigmoid:0/1; softplus and GELU:0/x'),
        commands=len(commands)),indent=2)+'\n')
    return len(commands)

if __name__=='__main__':
    out=Path(sys.argv[2]);hashes=generate(out);n=samples(Path(sys.argv[1]),out)
    print('SPECIAL_CANDIDATE_PREPARED',n,hashes)
