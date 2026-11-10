"""One real fullK11008 typed2 scope, 86 fixed-window LOADs, no destination86-entry directory."""
from pathlib import Path
p=Path(__file__).parent;s=(p/'rtl/tb_p_typed_stream.sv').read_text(encoding='utf-8').replace('tb_p_typed_stream','tb_p_long_stream')
a=s.index(' a_scale_directory32 directory(');b=s.index(' logic mc_req_valid',a)
s=s[:a]+''' // Current accepted RX metadata is the finite staging shift owner. Each
 // real A LOAD captures its shift before RX release; sourceP dir32 is elsewhere.
 assign directory_ready=1;assign directory_publish_ready=1;assign directory_bad=0;assign directory_pub_bad=0;assign directory_faults=0;
 assign scale_lookup_valid=data_enabled&&meta_key==scale_lookup_key&&meta_k==scale_lookup_kk;
 assign scale_lookup_shift=meta_shift;
'''+s[b:]
s=s.replace('scopes[0:7]','scopes[0:0]').replace('A_memory[0:255],expect_memory[0:31]','A_memory[0:1375],expect_memory[0:1]').replace('DDR_memory[0:1023]','DDR_memory[0:1461]')
s=s.replace('mc_req_address<64\'h102000+64\'(case_id)*64\'h10000',"mc_req_address<64'h100000+64'd1462*64")
s=s.replace('DDR_memory[case_id*128+int\'((mc_req_address-(64\'h100000+64\'(case_id)*64\'h10000))>>6)]',"DDR_memory[int'((mc_req_address-64'h100000)>>6)]")
s=s.replace('ci<8','ci<1')
s=s.replace('load_proofs==12&&poison_writes==192&&stale_prefix_checks==60&&real_copy_ACKs==192&&real_copy_reads==192&&real_headers==24&&real_quantizations==12','load_proofs==86&&poison_writes==1376&&stale_prefix_checks==430&&real_copy_ACKs==1376&&real_copy_reads==1376&&real_headers==172&&real_quantizations==86')
s=s.replace('ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192','ACKs==2&&writes==2&&completed==86&&record_count==86&&A_reads==1376')
s=s.replace('PASS p_typed_stream seed=%0d cases=8','PASS p_long_stream seed=%0d cases=1 fullK11008')
s=s.replace('wire unused_diagnostics=^{','wire unused_diagnostics=^{directory_cfg,directory_publish,publish_k,')
(p/'rtl/tb_p_long_stream.sv').write_text(s,encoding='utf-8')
s=(p/'p_typed_stream.sbatch').read_text(encoding='utf-8').replace('p_typed_stream','p_long_stream').replace('250typed2','250longK')
s=s.replace('make_p_executor_vectors.py --records "${RECORDS}"','make_p_long_stream_vectors.py')
s=s.replace('RECORDS=/public/home/yuzelu/project-circuit/issue250-weight-20261111-33/vectors/records.txt','')
(p/'p_long_stream.sbatch').write_text(s,encoding='utf-8')
