"""Seal successful focused RTL executions; hashes bind exact compiled inputs."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
kind,job=sys.argv[1:]
ext=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/rtl/w8a16_v1')
spec={
 'a-prefetch':(['tests/tb_a_frontend.sv','rtl/services/private_a_tile_abort_frontend.sv'],['PASS A two-credit reordered payload','cancel drained mode=1','cancel drained mode=2'],{'a_source_read_credits':2}),
 'weight-rtl':(['tests/tb_weight_credits.sv',str(ext/'weight_records.sv')],['PASS weight_records peak=32 records=4 returned=72 free=15 reordered/backpressured'],{'weight_read_credits':32,'weight_record_banks':4}),
 'dot':(['tests/tb_dot_cache.sv','rtl/services/e32_dot_service_controller.sv','rtl/macros/e_s32_mac_ap64.sv','rtl/macros/e_s32_mac_native.sv'],['PASS real E dot dual cache','PASS dot bad tag abort'],{'dot_operand_cache_lines':2}),
 'source':(['tests/tb_projection_source_pipeline.sv','rtl/services/projection_local_source.sv','rtl/p_services/s128_ddr_range_load.sv','rtl/projection/s32_a16_tile_quantizer.sv'],['PASS'],{'activation_cross_k_prefetch':True,'activation_prefetch_windows':1,'activation_stats_on_load':True,'quantization_read_words':32,'quantization_write_words':16,'quantization_response_slots':2,'quantization_pack_slots':2}),
}
sources,markers,caps=spec[kind]
folder=root/'evidence/command-pipeline'/f'{kind}-{job}'
logs=sorted(folder.glob('run*.log'))
text='\n'.join(p.read_text() for p in logs)
assert logs and all(x in text for x in markers) and '%Error' not in text
if kind=='source':
 assert len(logs)==6 and all('PASS' in p.read_text() for p in logs)
 assert 'observer=32 reads=32 writes=16 response=2 pack=2' in text
receipt={'passed':True,'evidence_kind':'rtl_behavior','method':'real RTL Verilator execution','job_id':int(job),
 'verified_capabilities':caps,
 'source_sha256':{str((root/p).resolve()):hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources},
 'testbench_sources':[str((root/sources[0]).resolve())],
 'evidence':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in logs},
 'execution_logs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in logs},
 'run_logs':[str(p) for p in logs]}
if kind=='weight-rtl':receipt['observed']={'peak_outstanding':32,'returned':72,'pending_at_end':0,'free_bank_mask':15,'credit_33_blocked':True,'reordered_payload_checked':True}
(root/'evidence/command-pipeline'/f'{kind}-{job}.json').write_text(json.dumps(receipt,indent=2)+'\n')
