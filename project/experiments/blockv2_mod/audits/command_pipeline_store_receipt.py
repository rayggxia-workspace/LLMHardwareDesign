import sys,json,hashlib
from pathlib import Path
root=Path.cwd();job=sys.argv[1];folder=root/'evidence/command-pipeline'/f'store-{job}'
logs=sorted(folder.glob('run-*.log'))
assert len(logs)==12 and all('PASS store' in p.read_text() and '%Error' not in p.read_text() for p in logs)
sources=[root/p for p in ('rtl/p_services/s128_store_pipeline.sv','rtl/p_services/s128_kv_store_scope.sv','tests/tb_store_pipeline.sv','tests/tb_store_scope.sv')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'passed':True,'evidence_kind':'rtl_behavior','job_id':int(job),'verified_capabilities':{'store_buffer_slots':2,'store_sram_read_credits':2,'store_ddr_write_credits':1},'source_sha256':{str(p):sha(p) for p in sources},'testbench_sources':[str(p) for p in sources if p.name.startswith('tb_')],'evidence':{str(p):sha(p) for p in logs},'scope':'real span writer and actual service wrapper; errors drain, cancellation retains whole-row drain'}
(folder.parent/f'store-{job}.json').write_text(json.dumps(result,indent=2)+'\n')
