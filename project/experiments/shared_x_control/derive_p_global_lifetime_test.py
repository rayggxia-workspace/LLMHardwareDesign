"""Exercise real M FENCE against the actual global ownership/purge fabric."""
from pathlib import Path
root = Path(__file__).parent / 'rtl'
s = (root / 'tb_p_program_fabric.sv').read_text().replace('module tb_p_program_fabric;', 'module tb_p_program_global_fence;')
s = s.replace('p_native_record_executor exec(.*);', 'p_native_record_executor #(.SESSION_LIMIT(32),.A_GENERATION_LIMIT(2),.W_GENERATION_LIMIT(1)) exec(.*);')
s = s.replace(' logic backend_fence_live;integer backend_fence_due;', ' logic backend_fence_live,wrong_purge_sent;integer backend_fence_due,wrong_purge_packets,dma_diagnostics;')
s = s.replace(' assign d_fence_done_valid=backend_fence_live&&cycle>=backend_fence_due;', ' wire bad_purge_phase=backend_fence_live&&backend_purges==2&&!wrong_purge_sent;\n assign d_fence_done_valid=backend_fence_live&&(bad_purge_phase||cycle>=backend_fence_due);')
s = s.replace(' assign d_fence_done_generation=backend_fence_generation;', ' assign d_fence_done_generation=backend_fence_generation^(bad_purge_phase?32\'d1:32\'d0);')
s = s.replace('backend_fence_generation<=0;', 'backend_fence_generation<=0;wrong_purge_sent<=0;wrong_purge_packets<=0;dma_diagnostics<=0;')
s = s.replace('if(d_fence_done_valid&&d_fence_done_ready)begin backend_fence_live<=0;', 'if(d_fence_done_valid&&d_fence_done_ready)begin\n    if(bad_purge_phase)begin wrong_purge_sent<=1;wrong_purge_packets<=wrong_purge_packets+1;end\n    else backend_fence_live<=0;')
s = s.replace('   assert(!dma_fault_valid)else $fatal(1,"actual global DMA fault %0d client%0d local%h global%h",dma_fault_kind,dma_fault_client,dma_fault_local_tag,dma_fault_global_tag);', '''   if(dma_fault_valid)begin
    assert(dma_fault_kind==2&&dma_fault_client==15&&dma_fault_local_tag==0&&dma_fault_global_tag=={32'd0,(backend_fence_generation^32'd1)}&&wrong_purge_packets==1)else $fatal(1,"unexpected real DMA ownership fault");
    dma_diagnostics<=dma_diagnostics+1;
   end
   if(backend_fence_live&&backend_purges>1)assert(!record_ready)else $fatal(1,"new record accepted before actual global purge done");''')
s = s.replace('backend_purges==1&&debug_beats==0', "backend_purges==int'(exec.fence_count)+1&&exec.fence_count>=17&&wrong_purge_packets==1&&dma_diagnostics==1&&debug_beats==0")
s = s.replace('PASS p_program_fabric', 'PASS p_program_global_fence')
(root / 'tb_p_program_global_fence.sv').write_text(s)
