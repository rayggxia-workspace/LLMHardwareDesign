"""Typed service2 actual quant/Header/COPY/nativeM/S limited numeric joint.

The generator changes only provider admission and descriptor service id. The
original service1 stream fixture and contiguous provider stay intact. CRC fetch
and full MC program are separate later gates, not inferred from this test.
"""
from pathlib import Path
p=Path(__file__).parent
s=(p/'rtl/tb_p_copy_stream.sv').read_text(encoding='utf-8')
s=s.replace('tb_p_copy_stream','tb_p_typed_stream')
s=s.replace(".NATIVE_LOCAL_CONTIG(1'b1)",".NATIVE_STREAM_A16(1'b1)")
s=s.replace('case_id=ci;scope_data=scopes[ci];scope_owner=',"case_id=ci;scope_data=scopes[ci];scope_data[48+:16]=16'd2;scope_owner=")
s=s.replace('PASS p_copy_stream','PASS p_typed_stream')
(p/'rtl/tb_p_typed_stream.sv').write_text(s,encoding='utf-8')
s=(p/'p_copy_stream.sbatch').read_text(encoding='utf-8').replace('p_copy_stream','p_typed_stream').replace('250CPstream','250typed2')
(p/'p_typed_stream.sbatch').write_text(s,encoding='utf-8')
