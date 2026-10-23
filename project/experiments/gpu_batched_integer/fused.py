"""Exact-order FP32 dequantization only; INT8 GEMMs stay actual cuBLAS INT32.

NVRTC and cuBLAS come from pinned isolated Torch. No toolkit/driver installation.
Explicit round-to-nearest multiplication/addition preserves the prior partial order.
"""
import ctypes as C
import hashlib
import importlib.util
from pathlib import Path
import types
import torch
import torch.nn.functional as F

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fused_integer_base',HERE/'kernel.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
P=C.c_void_p;I=C.c_int;S=C.c_size_t
SOURCE=r'''
extern "C" __global__ void reduce_parts(const int* a,const float* sa,const float* sw,
float* y,int* maximum,int groups,int rows,int padded,int cols) {
  int index=blockIdx.x*blockDim.x+threadIdx.x;
  int local_max=0;
  if(index<rows*cols) {
    int row=index/cols,col=index%cols;float sum=y[index];
    for(int g=0;g<groups;++g) {
      int acc=a[(g*padded+row)*cols+col];
      int mag=acc<0?-acc:acc;local_max=mag>local_max?mag:local_max;
      float t=__fmul_rn(__int2float_rn(acc),sa[g*rows+row]);
      t=__fmul_rn(t,sw[g*cols+col]);sum=__fadd_rn(sum,t);
    }
    y[index]=sum;
  }
  __shared__ int maxima[256];maxima[threadIdx.x]=local_max;__syncthreads();
  for(int step=128;step;step>>=1) {
    if(threadIdx.x<step) {
      int other=maxima[threadIdx.x+step];
      maxima[threadIdx.x]=other>maxima[threadIdx.x]?other:maxima[threadIdx.x];
    }
    __syncthreads();
  }
  if(threadIdx.x==0) atomicMax(maximum,maxima[0]);
}
'''


class Reduction:
    def __init__(self):
        lib=Path(torch.__file__).parent/'lib'
        self.nvrtc=C.WinDLL(str(lib/'nvrtc64_120_0.dll'));self.driver=C.WinDLL('nvcuda.dll')
        prog=P();create=self.nvrtc.nvrtcCreateProgram
        create.argtypes=[P,C.c_char_p,C.c_char_p,I,P,P];create.restype=I
        assert create(C.byref(prog),SOURCE.encode(),b'group_reduce.cu',0,None,None)==0
        major,minor=torch.cuda.get_device_capability()
        options=[f'--gpu-architecture=compute_{major}{minor}'.encode(),b'--fmad=false',b'--std=c++11']
        opts=(C.c_char_p*len(options))(*options)
        compile_=self.nvrtc.nvrtcCompileProgram;compile_.argtypes=[P,I,P];compile_.restype=I
        status=compile_(prog,len(options),opts)
        size=S();logsize=self.nvrtc.nvrtcGetProgramLogSize;logsize.argtypes=[P,P]
        logsize(prog,C.byref(size));log=C.create_string_buffer(size.value)
        logfn=self.nvrtc.nvrtcGetProgramLog;logfn.argtypes=[P,P];logfn(prog,log)
        if status:raise RuntimeError(f'NVRTC {status}: {log.value.decode()}')
        ptxsize=self.nvrtc.nvrtcGetPTXSize;ptxsize.argtypes=[P,P]
        assert ptxsize(prog,C.byref(size))==0
        ptx=C.create_string_buffer(size.value);ptxfn=self.nvrtc.nvrtcGetPTX;ptxfn.argtypes=[P,P]
        assert ptxfn(prog,ptx)==0
        self.ptx_sha256=hashlib.sha256(ptx.raw).hexdigest()
        destroy=self.nvrtc.nvrtcDestroyProgram;destroy.argtypes=[P];destroy(C.byref(prog))
        self.module=P();load=self.driver.cuModuleLoadData;load.argtypes=[P,P];load.restype=I
        assert load(C.byref(self.module),ptx)==0
        self.function=P();get=self.driver.cuModuleGetFunction;get.argtypes=[P,P,C.c_char_p];get.restype=I
        assert get(C.byref(self.function),self.module,b'reduce_parts')==0
        self.launch=self.driver.cuLaunchKernel
        self.launch.argtypes=[P,I,I,I,I,I,I,I,P,P,P];self.launch.restype=I

    def apply(self,acc,scales,wscales,y,maximum):
        g,padded,n=acc.shape;m=y.shape[0]
        values=[P(t.data_ptr()) for t in (acc,scales,wscales,y,maximum)]+[I(v) for v in (g,m,padded,n)]
        args=(P*len(values))(*(C.cast(C.byref(v),P) for v in values))
        status=self.launch(self.function,(m*n+255)//256,1,1,256,1,1,0,
            torch.cuda.current_stream().cuda_stream,args,None)
        if status:raise RuntimeError(f'FP32 partial reduction CUDA launch failed {status}')


def install(model,mode,factors,group_k=128):
    rows=base.install(model,mode,factors,group_k);engine=base.BatchedInt8();reduce=Reduction()
    model.integer_backend_receipt.update(pointwise='NVRTC explicit rn FP32 serial partial order',
        pointwise_source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),ptx_sha256=reduce.ptx_sha256)
    for module in model.modules():
        if not hasattr(module,'qblocks'):continue
        def forward(self,x):
            shape=x.shape;n=x.numel()//shape[-1];g=self.qblocks.shape[0]
            xf=x.reshape(n,g,group_k).float().permute(1,0,2).contiguous()
            scales=xf.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
            raw=(xf/scales).round();qa=raw.clamp(-127,127).to(torch.int8)
            pad=(-n)%32
            if pad:qa=F.pad(qa,(0,0,0,pad))
            y=torch.zeros((n,self.qblocks.shape[-1]),device=x.device,dtype=torch.float32)
            maximum=torch.zeros((),device=x.device,dtype=torch.int32)
            batch_groups=max(1,min(8,(128*2**20)//(qa.shape[1]*y.shape[-1]*4)))
            for start in range(0,g,batch_groups):
                end=min(start+batch_groups,g);acc=engine.mm(qa[start:end],self.qblocks[start:end])
                reduce.apply(acc,scales[start:end],self.wscales[start:end],y,maximum)
                if self.take_sample and not hasattr(self,'sample'):
                    self.sample={'A':qa[start,:min(2,n)].cpu(),'B':self.qblocks[start,:,:4].cpu(),
                        'accumulator':acc[0,:min(2,n),:4].cpu(),'group':start}
                self.stats['batched_launches']+=1;del acc
            self.stats['calls']+=1;self.stats['int8_gemm_calls']+=g
            self.stats['max_abs_acc']=max(self.stats['max_abs_acc'],int(maximum))
            self.stats['saturation_count']+=int((raw.abs()>127).sum())
            self.stats['activation_scales_logical_bytes']+=n*g*4
            if self.bias is not None:y+=self.bias.float()
            return y.to(x.dtype).reshape(*shape[:-1],-1)
        module.forward=types.MethodType(forward,module)
    return rows
