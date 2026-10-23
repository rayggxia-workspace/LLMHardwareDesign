"""Real CUDA capability checks; writes failures without changing drivers."""
import argparse
import importlib.metadata as md
import json
import platform
import subprocess
import sys
from pathlib import Path
import psutil
import torch


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = {'python': sys.version, 'platform': platform.platform(),
              'packages': {x.metadata['Name']: x.version for x in md.distributions()},
              'RAM': dict(psutil.virtual_memory()._asdict()),
              'disk_D': dict(psutil.disk_usage('D:/')._asdict()),
              'nvidia_smi': subprocess.check_output(['nvidia-smi'], text=True),
              'torch_config': torch.__config__.show(), 'cuda_runtime': torch.version.cuda,
              'cuda_available': torch.cuda.is_available(), 'tests': {}}
    if torch.cuda.is_available():
        result.update(device=torch.cuda.get_device_name(), capability=torch.cuda.get_device_capability(),
                      free_total_bytes=torch.cuda.mem_get_info(), bf16_supported=torch.cuda.is_bf16_supported())
        for name, dtype in [('fp16', torch.float16), ('bf16', torch.bfloat16), ('int8_int32', torch.int8)]:
            try:
                x = torch.ones((32, 32), device='cuda', dtype=dtype)
                y = torch._int_mm(x, x) if dtype == torch.int8 else x @ x
                torch.cuda.synchronize()
                result['tests'][name] = {'pass': bool((y == 32).all()), 'output_dtype': str(y.dtype)}
            except Exception as e:
                result['tests'][name] = {'pass': False, 'error': repr(e)}
    a.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['cuda_available', 'cuda_runtime', 'tests']}))


if __name__ == '__main__':
    main()
