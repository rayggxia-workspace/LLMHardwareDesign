#!/usr/bin/env python3
"""从本任务独立目录收集小型回执/哈希，不下载检查点或干预作业。"""
import pathlib,subprocess
ROOT='/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153'
out=pathlib.Path(__file__).resolve().parents[1]/'results';out.mkdir(exist_ok=True)
def copy(source,name):subprocess.run(['scp','yuzelu@10.129.166.172:'+ROOT+'/'+source,str(out/name)],check=True)
for model in ('qwen3','qwen25','granite'):
    for mode in ('','-fused'):
        name=model+'-r6'+mode;remote='run-'+name
        for f in ('validation.json','systemc_receipt.json','run-inputs.sha256'):copy(remote+'/'+f,name+'-'+f)
    cp=model+('-r2' if model!='granite' else '-r1')
    for f in ('export_receipt.json','metadata.txt','weights.index'):copy(cp+'/'+f,model+'-'+f)
for f in ('validation.json','export_receipt.json','run-inputs.sha256'):copy('gdn-boundary-r2/'+f,'gdn-r2-'+f)
copy('gdn-boundary/validation.json','gdn-r1-failed-validation.json')
copy('diagnostic-r2/diagnostic.json','qwen3-first-layer-diagnostic.json')
copy('logs/six-94241.out','six-94241.out.txt');copy('logs/gdn-94242.out','gdn-94242.out.txt')
copy('bench_audit.json','bench_audit.json')
for model in ('qwen3','qwen25','granite'):
    name=model+'-r7-fused';remote='run-'+name
    for f in ('validation.json','systemc_receipt.json','run-inputs.sha256'):copy(remote+'/'+f,name+'-'+f)
copy('logs/compare-94243.out','compare-94243.out.txt')
