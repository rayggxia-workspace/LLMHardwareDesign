"""Replay all generated MC pages on actual controller RTL with timed peer fixtures."""
import json,sys
from pathlib import Path
package,out,fixture=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=False)
manifest=json.loads((package/'manifest.json').read_text())
deployment=json.loads((package/'deployment.json').read_text())
calls=json.loads((package/'calls.json').read_text())
(out/'targets.hex').write_text(''.join(f"{c['target']:02x}\n" for c in calls))
body=['initial begin : scenario','`include "tb_native_init.svh"',
      f'expected_calls={len(calls)}; check_ptr=1; check_targets=1; ptr_start=64\'d{manifest["descriptor_base"]};',
      f'$readmemh("{out.resolve()}/targets.hex",oracle_targets,0,expected_calls-1);',
      'repeat(2) @(negedge clk_i); rst_ni=1;',
      '@(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;',
      '@(negedge clk_i); release_valid_i=0; start_credit_i=1;']
targets=sorted({c['target'] for c in calls})
for i,page in enumerate(manifest['mother_pages']):
    raw=(package/page['file']).read_bytes();path=out/f'page-{i}.hex'
    path.write_text(''.join(raw[j:j+16][::-1].hex()+'\n' for j in range(0,len(raw),16)))
    contract=deployment['pages'][i]
    assert contract['file']==page['file'] and contract['generation']==i+1
    body += [f'ji={i}; config_generation={i+1}; words={len(raw)//16};',
             'runtime_active=0; deploy_valid_i=0; repeat(3) @(negedge clk_i);',
             f'$readmemh("{path.resolve()}",input_image,0,words-1);',
             'expected_image=input_image[3][96+:32]; expected_topology=input_image[4][0+:32];',
             'config_command(0,0,0,0);',
             'for(n=0;n<words;n=n+1) config_command(1,n*16,input_image[n],0);',
             'for(n=0;n<words;n=n+1) config_command(2,n*16,0,0);',
             'config_command(3,0,0,0);config_command(4,0,0,0);',
             f'local_enabled_i=9\'d{sum(1<<t for t in targets)};',
             *[f'local_image_ids_i[{32*t}+:32]=32\'d{deployment["local_program_image_id"]};' for t in targets],
             f'deploy_valid_i=1;deploy_generation_i={i+1};',
             'while(life_o!=5) @(negedge clk_i);runtime_active=1;',
             f'start_job_i=1;start_epoch_i=1;start_sequence_i={i+1};start_generation_i={i+1};start_args_i=0;',
             'start_valid_i=1; @(posedge clk_i);while(!start_ready_o) @(posedge clk_i);',
             '@(negedge clk_i);start_valid_i=0;',
             'while(!result_valid_o) @(negedge clk_i);repeat(5) @(negedge clk_i);',
             'result_ready_i=1;@(negedge clk_i);result_ready_i=0;',
             f'while(returns!={i+1}) @(negedge clk_i);',
             'assert(trace_live_tokens_o==0&&trace_block_active_o==0&&child_busy==0);']
body += [f'assert(calls=={len(calls)}&&returns=={len(manifest["mother_pages"])}&&cancels==0);',
         '$display("PASS whole-package MC pages=%0d calls=%0d faults=%0d",returns,calls,protocol_fault_count_o);',
         '$finish;end']
text=(fixture/'tb_mc_native.sv').read_text()
start=text.index('  initial begin : scenario');end=text.index('`ifdef MC_TRANSPORT128\n  wire timing_PM_req',start)
text=text[:start]+'\n'.join(body)+'\n'+text[end:]
text=text.replace('oracle_targets[0:4095]','oracle_targets[0:199999]')
text=text.replace('cfg_req_generation_i=1;','cfg_req_generation_i=config_generation;')
text=text.replace('integer cycle=0,','integer config_generation=0; integer cycle=0,')
text=text.replace('#5000000;','#2000000000;')
(out/'tb_mc_native.sv').write_text(text)
print(out)
