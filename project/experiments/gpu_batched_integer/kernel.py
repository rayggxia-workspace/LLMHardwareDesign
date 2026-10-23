"""Batched actual INT8 GEMMs, using the cuBLAS DLL bundled with pinned Torch.

NVIDIA cublasGemmStridedBatchedEx: CUDA_R_8I inputs, CUDA_R_32I output,
CUBLAS_COMPUTE_32I. No new driver/toolkit, no floating-point GEMM fallback.
Reference: https://docs.nvidia.com/cuda/archive/12.8.1/cublas/index.html
"""
import ctypes as C
import importlib.util
from pathlib import Path
import types
import torch
import torch.nn.functional as F

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('batched_reference_grouping',HERE.parent/'gpu_grouped_repair/run.py')
grouped=importlib.util.module_from_spec(spec);spec.loader.exec_module(grouped)
P=C.c_void_p;I=C.c_int;L=C.c_longlong


class BatchedInt8:
    def __init__(self):
        self.dll_path=Path(torch.__file__).parent/'lib/cublas64_12.dll'
        self.dll=C.WinDLL(str(self.dll_path))
        self.fn=self.dll.cublasGemmStridedBatchedEx
        self.fn.restype=I;self.fn.argtypes=[P,I,I,I,I,I,P,P,I,I,L,P,I,I,L,P,P,I,I,L,I,I,I]
        self.stream=self.dll.cublasSetStream_v2;self.stream.restype=I;self.stream.argtypes=[P,P]
        self.pointer=self.dll.cublasSetPointerMode_v2;self.pointer.restype=I;self.pointer.argtypes=[P,I]

    def mm(self,a,b):
        assert a.is_cuda and b.is_cuda and a.dtype==b.dtype==torch.int8
        assert a.is_contiguous() and b.is_contiguous()
        batch,m,k=a.shape;assert b.shape[0]==batch and b.shape[1]==k
        n=b.shape[2];assert k%4==0 and n%4==0
        out=torch.empty((batch,m,n),device=a.device,dtype=torch.int32)
        handle=torch.cuda.current_blas_handle();one=I(1);zero=I(0)
        assert self.stream(handle,torch.cuda.current_stream().cuda_stream)==0
        assert self.pointer(handle,0)==0
        # Row-major C=A@B -> column-major C^T=B^T@A^T.
        status=self.fn(handle,0,0,n,m,k,C.byref(one),b.data_ptr(),3,n,k*n,
            a.data_ptr(),3,k,m*k,C.byref(zero),out.data_ptr(),10,n,m*n,batch,72,-1)
        if status:raise RuntimeError(f'INT8 batched cuBLAS failed status={status}; no fallback')
        return out


def install(model,mode,factors,group_k=128):
    records=grouped.install(model,mode,factors,group_k)
    engine=BatchedInt8()
    for module in model.modules():
        if not hasattr(module,'qblocks'):continue
        module.stats['batched_launches']=0
        module.stats['backend']='cublasGemmStridedBatchedEx_INT8_INT32'
        def forward(self,x):
            shape=x.shape;n=x.numel()//shape[-1];g=self.qblocks.shape[0]
            xf=x.reshape(n,g,group_k).float().permute(1,0,2).contiguous()
            scales=xf.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
            raw=(xf/scales).round();qa=raw.clamp(-127,127).to(torch.int8)
            pad=(-n)%32
            if pad:qa=F.pad(qa,(0,0,0,pad))
            y=torch.zeros((n,self.qblocks.shape[-1]),device=x.device,dtype=torch.float32)
            largest=torch.zeros((),device=x.device,dtype=torch.int32)
            # Bound the INT32 temporary; long one-shot conditions can use one group.
            batch_groups=max(1,min(8,(128*2**20)//(qa.shape[1]*y.shape[-1]*4)))
            for start in range(0,g,batch_groups):
                end=min(start+batch_groups,g)
                acc=engine.mm(qa[start:end],self.qblocks[start:end])
                largest=torch.maximum(largest,acc.abs().max())
                for offset in range(end-start):
                    j=start+offset
                    # Preserve the reference multiplication and partial-sum order exactly.
                    y.add_(acc[offset,:n].float()*scales[j]*self.wscales[j])
                if self.take_sample and not hasattr(self,'sample'):
                    self.sample={'A':qa[start,:min(2,n)].cpu(),'B':self.qblocks[start,:,:4].cpu(),
                        'accumulator':acc[0,:min(2,n),:4].cpu(),'group':start}
                self.stats['batched_launches']+=1
                del acc
            self.stats['calls']+=1;self.stats['int8_gemm_calls']+=g
            self.stats['max_abs_acc']=max(self.stats['max_abs_acc'],int(largest))
            self.stats['saturation_count']+=int((raw.abs()>127).sum())
            self.stats['activation_scales_logical_bytes']+=n*g*4
            if self.bias is not None:y+=self.bias.float()
            return y.to(x.dtype).reshape(*shape[:-1],-1)
        module.forward=types.MethodType(forward,module)
    for row in records:row['backend']='cublasGemmStridedBatchedEx_INT8_INT32'
    return records
