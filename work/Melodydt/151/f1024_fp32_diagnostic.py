"""Selected fixture FP32 counterpart; not checkpoint/model quality acceptance."""
import argparse,json,math,struct,hashlib
from pathlib import Path
from f1024_integer_reference import weight


def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]


def linear(x,matrix,nout,seed):
    if not any(x):return [0.0]*nout
    distinct=[]
    for n in range(251):
        value=0.0
        for k,a in enumerate(x):
            value=f32(value+f32(a*f32(weight(matrix,n,k,seed)/128.0)))
        distinct.append(value)
    return [distinct[n%251] for n in range(nout)]


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();d=a.directory
    source=d/'f1024-contract-vectors.json';data=json.loads(source.read_text(encoding='utf-8'));results=[]
    for v in data['vectors']:
        x=[f32(t/1024.0) for t in v['X']];gamma=[f32(t/1024.0) for t in v['gamma']]
        sumsq=0.0
        for value in x:sumsq=f32(sumsq+f32(value*value))
        epsilon=f32(2.0**-20);inv=f32(1.0/f32(math.sqrt(f32(f32(sumsq/1024.0)+epsilon))))
        norm=[f32(f32(value*inv)*g) for value,g in zip(x,gamma)]
        gate=linear(norm,0,3072,v['seed']);up=linear(norm,1,3072,v['seed']);mid=[]
        for value,g in zip(gate,up):
            sigmoid=f32(1.0/(1.0+math.exp(-value))) if value>=0 else f32(math.exp(value)/(1.0+math.exp(value)))
            mid.append(f32(f32(value*sigmoid)*g))
        down=linear(mid,2,1024,v['seed']);output=[f32(a+b) for a,b in zip(down,x)]
        integer=[t/1024.0 for t in v['expected']['final']];errors=[a-b for a,b in zip(integer,output)]
        results.append({'fixture':v['id'],'elements':1024,'max_absolute_error':max(map(abs,errors)),
          'RMSE':math.sqrt(sum(e*e for e in errors)/1024),'integer_done_saturated':v['expected']['done_saturated'],
          'FP32_max_absolute_output':max(map(abs,output)),
          'FP32_output_sha256_little_endian':hashlib.sha256(b''.join(struct.pack('<f',t) for t in output)).hexdigest()})
    result={'status':'SELECTED_SYNTHETIC_FIXTURE_DIAGNOSTIC_NOT_TRAINED_QWEN3_QUALITY',
      'source_vectors_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'arithmetic':'FP32-rounded products and sequential full-K accumulation; n-period reuse only; no S16 clip in FP32 counterpart',
      'epsilon_real':2.0**-20,'epsilon_note':'integer code1 counterpart,not exact source-model 1e-6',
      'scope':'two synthetic quantized-parameter fixtures only;error includes intentional integer rounding/clipping;not a trained-model threshold or acceptance',
      'results':results}
    (d/'f1024-fp32-fixture-diagnostic.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
    for item in results:print(item['fixture'],'maxAbs',item['max_absolute_error'],'RMSE',item['RMSE'])


if __name__=='__main__':main()
