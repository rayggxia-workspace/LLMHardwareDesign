// Separate native profile: nine resident groups, sixteen tokens, nine events.
// 64-bit execution ISA; packet version 2 adds generation/topology return identity.
// Program memory, child controllers, packet transport and cohort grant are peers.
`timescale 1ns/1ps
module mc_native_controller #(parameter integer unsigned STALL_LIMIT=1024,
  parameter integer unsigned SERVICE_STALL_LIMIT=STALL_LIMIT,
                           parameter [31:0] NATIVE_ABI_ID=32'h02500002) (
`include "mc_native_ports.svh"
);
  localparam [3:0] RESET_WAIT=0, INVALID=1, LOADING=2, VERIFIED=3,
                   PREPARED=4, READY=5, RUNNING=6, POISONED=8;
  localparam [3:0] IDLE=0, FETCH_REQ=1, FETCH_WAIT=2, DECODE=3,
                   CALL_HOLD=4, RESULT_HOLD=7, BIND_REQ=8, BIND_WAIT=9,
                   BIND_CHECK=10, ERROR_DRAIN=11;
  reg [3:0] life,seq;
  reg authorized,prepared,poisoned,cfg_busy,cfg_mem_wait,cfg_response;
  reg [31:0] generation,cert_epoch,last_release,image_id,topology,abi_id,capacity_id;
  reg [15:0] total,written,readback,cfg_status;
  reg [2:0] cfg_op;
  reg [13:0] cfg_address;
  reg [127:0] cfg_data,cfg_read_data;
  reg [1023:0] header;
  reg pm_offered,pm_outstanding;
  reg [13:0] pm_hold_address;
  reg [1:0] pm_hold_owner;
  reg [31:0] pc,steps,stall_count;
  reg [127:0] ireg;
  reg ireg_valid;
  reg [31:0] registers[0:7];
  reg [127:0] event_cache[0:8];
  reg [3:0] bind_index;
  reg [8:0] binding_consumed;
  reg [31:0] job,epoch,job_sequence,last_start;
  reg [31:0] local_ids[0:8],next_sequence[0:8];
  reg [8:0] enabled,block_active,block_accepted,cancel_sent,terminal_full,ready_full;
  reg [3:0] block_token[0:8];
  reg [511:0] context_packet[0:8];
  reg [31:0] ready_scalar[0:8];
  reg [31:0] protocol_fault_count;
  reg [15:0] live_tokens;
  reg out_valid;
  reg [511:0] out_packet;
  reg aborting,result_valid;
  reg [15:0] error_status;
  reg [31:0] error_pc,child_error_pc,failed_task_sequence;
  reg [7:0] error_source;
  reg [31:0] confirmed_reads,confirmed_writes;
  reg counter_overflow,saturated;
  integer ri,bj;

  wire [31:0] inst_count=header[160+:32],inst_offset=header[192+:32];
  wire [31:0] max_steps=header[416+:32],event_offset=header[608+:32];
  wire [15:0] binding_count=header[576+:16];
  wire [7:0] opcode=ireg[127:120],ia=ireg[111:104],ib=ireg[103:96],ic=ireg[95:88];
  wire [31:0] wait_mask=ireg[63:32];
  `include "native_instruction_fetch.svh"
  wire [63:0] bind_address={32'b0,event_offset}+{56'b0,bind_index,4'b0};
  wire bind_address_ok=bind_address[3:0]==0 && bind_address+64'd16<={48'b0,total};
  reg targets_valid,target_snapshot_ok;
  integer ti;
  always @* begin
    targets_valid=local_enabled_i!=0;target_snapshot_ok=1;
    for(ti=0;ti<9;ti=ti+1) begin
      if(local_enabled_i[ti] && local_image_ids_i[32*ti+:32]==0) targets_valid=0;
      if(life==RUNNING && (enabled[ti]!=local_enabled_i[ti] ||
          enabled[ti] && local_ids[ti]!=local_image_ids_i[32*ti+:32])) target_snapshot_ok=0;
    end
  end
  wire deployed=authorized && prepared && !poisoned && deploy_valid_i && deploy_generation_i==generation &&
       targets_valid && target_snapshot_ok;
  wire cfg_fire=cfg_req_valid_i && cfg_req_ready_o;
  wire pm_fire=pm_req_valid_o && pm_req_ready_i;
  wire pm_done=pm_rsp_valid_i && pm_rsp_ready_o;
  wire start_fire=start_valid_i && start_ready_o;
  wire task_fire=task_valid_o && task_ready_i;
  wire return_accept=return_valid_i && return_ready_o;
  wire return_fire=return_accept && return_validated;
  wire result_fire=result_valid_o && result_ready_i;
  wire [3:0] return_sb=return_packet_i[24+:4];
  wire [7:0] return_kind=return_packet_i[16+:8];
  wire return_terminal=return_kind==2 || return_kind==3;
  wire return_base_ok=return_packet_i[0+:16]==2 && return_packet_i[24+:8]<9 &&
       block_active[return_sb] && block_accepted[return_sb] &&
       return_packet_i[32+:96]==context_packet[return_sb][32+:96] && return_packet_i[352+:32]==generation && return_packet_i[384+:32]==topology && return_packet_i[416+:96]==0;
  reg ready_binding;
  integer rb;
  always @* begin
    ready_binding=0;
    for(rb=0;rb<9;rb=rb+1) if(rb<binding_count && !binding_consumed[rb] &&
        event_cache[rb][8+:8]==return_packet_i[24+:8] &&
        event_cache[rb][0+:8]==return_packet_i[136+:8]) ready_binding=1;
  end
  wire return_READY_ok=return_kind==0 && !ready_full[return_sb] && !terminal_full[return_sb] &&
       ready_binding && return_packet_i[128+:8]==255 && return_packet_i[144+:16]==0 &&
       return_packet_i[192+:96]==0 && return_packet_i[288+:32]==1 && return_packet_i[320+:32]==32'hffffffff;
  wire return_terminal_ok=return_terminal && !terminal_full[return_sb] &&
       return_packet_i[128+:8]=={4'b0,block_token[return_sb]} && return_packet_i[136+:8]==255 &&
       return_packet_i[160+:32]==0 && (return_packet_i[256+:32]&32'hfffffff8)==0 && return_packet_i[288+:32]==0 &&
       (return_kind==2 ? return_packet_i[144+:16]==0 && return_packet_i[320+:32]==32'hffffffff : return_packet_i[144+:16]!=0);
  wire return_validated=(life==RUNNING || life==POISONED) && return_base_ok && (return_READY_ok || return_terminal_ok);
  wire bad_return=return_accept && !return_validated;
  wire incoming_error=return_fire && return_kind==3;
  wire normal_issue=life==RUNNING && deployed && !aborting && !incoming_error && !bad_return;
  reg [15:0] done_tokens;
  reg [8:0] source_events_consumed;
  reg wait_events_clear,event_found,event_available,all_bindings_consumed,bindings_ok;
  reg [3:0] event_slot,event_source;
  integer eb,es,ec;
  always @* begin
    done_tokens=0;source_events_consumed='1;wait_events_clear=1;
    event_found=0;event_slot=0;event_source=0;all_bindings_consumed=1;bindings_ok=1;
    for(eb=0;eb<9;eb=eb+1) begin
      if(terminal_full[eb]) done_tokens=done_tokens|(16'b1<<block_token[eb]);
      if(eb<binding_count) begin
        if(!binding_consumed[eb]) begin
          all_bindings_consumed=0;
          if(event_cache[eb][8+:8]<9) source_events_consumed[event_cache[eb][8+:4]]=0;
        end
        if(event_cache[eb][0+:8]==ib) begin event_found=1;event_slot=4'(eb);event_source=event_cache[eb][8+:4];end
        if(event_cache[eb][0+:8]>=32 || event_cache[eb][8+:8]>=9 || event_cache[eb][16+:112]!=0) bindings_ok=0;
        for(ec=0;ec<9;ec=ec+1) if(ec<eb && (event_cache[ec][0+:8]==event_cache[eb][0+:8] ||
             event_cache[ec][8+:8]==event_cache[eb][8+:8])) bindings_ok=0;
      end
    end
    for(es=0;es<9;es=es+1) if(block_active[es] && wait_mask[{1'b0,block_token[es]}] &&
        (ready_full[es] || !source_events_consumed[es])) wait_events_clear=0;
    event_available=event_found && !binding_consumed[event_slot] && ready_full[event_source];
  end
  wire wait_allocated=wait_mask!=0 && (wait_mask&~{16'b0,live_tokens})==0;
  wire wait_done=(wait_mask&~{16'b0,done_tokens})==0;
  wire movi_fields=ireg[119:112]==0 && ia<8 && ireg[103:64]==0 && ireg[31:0]==0;
  wire event_fields=ireg[119:112]==0 && ia<8 && ib<32 && ireg[95:0]==0;
  wire wait_fields=ireg[119:64]==0 && ireg[31:0]==0;
  wire waiting_on_service=seq==DECODE && ireg_valid && opcode==8'h11 && wait_fields && wait_allocated && !wait_done;
  wire [31:0] active_stall_limit=waiting_on_service ? SERVICE_STALL_LIMIT : STALL_LIMIT;
  wire cfg_meta_ok=cfg_req_generation_i>generation && cfg_req_total_bytes_i>=144 &&
       cfg_req_total_bytes_i<=16384 && cfg_req_total_bytes_i[3:0]==0 && cfg_req_image_id_i!=0 && cfg_req_topology_id_i!=0 &&
       cfg_req_abi_id_i==NATIVE_ABI_ID && cfg_req_capacity_id_i==32'h02590003;
  wire header_ok=header[0+:64]==64'h313041534943424c && instruction_version_ok && header[80+:8]==0 && header[88+:8]==8 &&
       header[96+:32]=={16'b0,total} && header[128+:32]<inst_count && inst_count>0 && inst_count<=2032 && inst_offset==128 &&
       header[224+:64]==0 && header[288+:128]==0 && max_steps>0 && header[448+:32]==0 &&
       header[480+:32]==image_id && header[512+:32]==topology && header[544+:32]==abi_id &&
       binding_count<=9 && header[592+:16]==0 && (binding_count==0 ? event_offset==0 :
         {32'b0,event_offset}==instruction_end) &&
       {48'b0,total}==instruction_end+({48'b0,binding_count}<<4) &&
       header[640+:32]==0 && header[672+:32]==capacity_id && header[704+:320]==0;
  wire addi64_fields=movi_fields&&ia<7&&!ia[0];
  wire [64:0] pointer_sum={1'b0,registers[{ia[2:1],1'b1}],registers[{ia[2:1],1'b0}]}+
      {33'b0,ireg[63:32]};
  wire loop_fields=movi_fields&&ia>=2;
  wire loop_target_ok=ireg[63:32]>=header[128+:32]&&ireg[63:32]<pc&&ireg[63:32]<inst_count;
  wire loop_count_ok=registers[ia[2:0]]!=0&&registers[ia[2:0]]<=32'd65535;
  wire [32:0] read_sum={1'b0,confirmed_reads}+{1'b0,return_packet_i[192+:32]};
  wire [32:0] write_sum={1'b0,confirmed_writes}+{1'b0,return_packet_i[224+:32]};
  reg [511:0] call_word;
  integer ar;
  always @* begin
    call_word=0; call_word[0+:16]=2; call_word[24+:8]=ia;
    call_word[32+:32]=job; call_word[64+:32]=epoch; call_word[96+:32]=next_sequence[ia[3:0]]+1;
    call_word[128+:8]=ic; call_word[136+:8]=ib; call_word[160+:32]=local_ids[ia[3:0]]; call_word[192+:32]=topology; call_word[224+:32]=generation;
    for(ar=0;ar<8;ar=ar+1) call_word[256+ar*32+:32]=registers[ar];
  end

  assign life_o=life; assign seq_o=seq; assign poison_o=poisoned;
  assign image_valid_o=rst_ni && deployed;
  assign release_ready_o=rst_ni && life==RESET_WAIT;
  assign cfg_req_ready_o=rst_ni && authorized && !cfg_busy && !poisoned &&
       (life==INVALID || life==LOADING || life==VERIFIED || life==PREPARED || life==READY);
  assign cfg_rsp_valid_o=rst_ni && cfg_response;
  assign cfg_rsp_status_o=cfg_status; assign cfg_rsp_data_o=cfg_read_data; assign cfg_rsp_generation_o=generation;
  assign start_ready_o=rst_ni && life==READY && deployed && !cfg_busy && start_credit_i && !return_valid_i &&
       (!start_valid_i || start_generation_i==generation && start_epoch_i>=cert_epoch && start_sequence_i>last_start && start_args_i==0) &&
       !(cfg_req_valid_i && cfg_req_ready_o);
  assign pm_req_valid_o=rst_ni && (pm_offered || !poisoned &&
       (cfg_busy && !cfg_response && !cfg_mem_wait && (cfg_op==1 || cfg_op==2) ||
        normal_issue && (seq==BIND_REQ && bind_address_ok || seq==FETCH_REQ && pc<inst_count && steps<max_steps &&
         fetch_address+64'd16<={48'b0,total})));
  assign pm_req_write_o=cfg_busy && cfg_op==1;
  assign pm_req_address_o=pm_offered ? pm_hold_address : cfg_busy ? cfg_address : seq==FETCH_REQ ? fetch_address[13:0] : bind_address[13:0];
  assign pm_req_data_o=cfg_busy && cfg_op==1 ? cfg_data : 0;
  assign trace_pm_owner_o=pm_offered ? pm_hold_owner : cfg_busy ? 0 : seq==FETCH_REQ || seq==FETCH_WAIT ? 1 : 2;
  assign pm_rsp_ready_o=rst_ni && pm_outstanding;
  assign task_valid_o=rst_ni && out_valid;
  assign task_packet_o=out_packet;
  assign task_target_o=out_packet[24+:8];
  assign task_credit_o=rst_ni && out_valid && out_packet[16+:8]==0;
  assign return_ready_o=rst_ni;
  assign protocol_fault_count_o=protocol_fault_count;
  assign recover_ready_o=rst_ni && poisoned && (terminal_full&block_active)==block_active &&
      !out_valid && !pm_outstanding && !pm_offered;
  assign result_valid_o=rst_ni && result_valid;
  assign result_job_o=job; assign result_epoch_o=epoch; assign result_sequence_o=job_sequence;
  assign result_status_o=error_status; assign result_error_pc_o=error_pc; assign result_source_o=error_source;
  assign result_child_error_pc_o=child_error_pc; assign result_failed_task_sequence_o=failed_task_sequence;
  assign result_confirmed_read_bytes_o=confirmed_reads; assign result_confirmed_write_bytes_o=confirmed_writes;
  assign result_counter_overflow_o=counter_overflow; assign result_saturated_o=saturated;
  assign trace_pc_o=pc; assign trace_opcode_o=opcode; assign trace_ireg_valid_o=ireg_valid;
  assign trace_live_tokens_o=live_tokens; assign trace_block_active_o=block_active;
  assign trace_terminal_full_o=terminal_full; assign trace_READY_full_o=ready_full; assign trace_aborting_o=aborting;
  assign trace_retire_o=rst_ni && !poisoned && ireg_valid &&
       (task_fire && out_packet[16+:8]==0 || result_fire && opcode==8'h1f && error_status==0 ||
        normal_issue && seq==DECODE && (opcode==8'h13 && movi_fields ||
          opcode==8'h15 && compact_image && branch_fields_ok && branch_targets_ok || opcode==8'h12 && event_fields && event_available ||
          opcode==8'h11 && wait_fields && wait_allocated && wait_done && wait_events_clear));

  task fault;
    input [15:0] status;
    begin
      if(error_status==0) begin error_status<=status; error_pc<=pc; error_source<=255; child_error_pc<=32'hffffffff; failed_task_sequence<=0; end
      aborting<=1; ireg_valid<=0; seq<=ERROR_DRAIN;
    end
  endtask

  always @(posedge clk_i or negedge rst_ni) begin
    if(!rst_ni) begin
      life<=RESET_WAIT; seq<=IDLE; authorized<=0; prepared<=0; poisoned<=0;
      generation<=0; cert_epoch<=0; last_release<=0; image_id<=0; topology<=0; abi_id<=0; capacity_id<=0;
      total<=0; written<=0; readback<=0; cfg_status<=0; cfg_op<=0; cfg_address<=0; cfg_data<=0;
      cfg_read_data<=0; cfg_busy<=0; cfg_mem_wait<=0; cfg_response<=0; header<=0;
      pm_offered<=0; pm_outstanding<=0; pm_hold_address<=0; pm_hold_owner<=0;
      pc<=0; steps<=0; stall_count<=0; ireg<=0; ireg_valid<=0; bind_index<=0; binding_consumed<=0;
      job<=0; epoch<=0; job_sequence<=0; last_start<=0; enabled<=0; block_active<=0; block_accepted<=0;
      cancel_sent<=0; terminal_full<=0; ready_full<=0; live_tokens<=0; out_valid<=0; out_packet<=0;
      aborting<=0; result_valid<=0; error_status<=0; protocol_fault_count<=0; error_pc<=32'hffffffff; error_source<=255;
      child_error_pc<=32'hffffffff; failed_task_sequence<=0; confirmed_reads<=0; confirmed_writes<=0; counter_overflow<=0; saturated<=0;
      for(ri=0;ri<8;ri=ri+1) registers[ri]<=0;
      for(bj=0;bj<9;bj=bj+1) begin
        event_cache[bj]<=0; local_ids[bj]<=0; next_sequence[bj]<=0; block_token[bj]<=0;
        context_packet[bj]<=0; ready_scalar[bj]<=0;
      end
    end else begin
      pm_offered<=pm_req_valid_o && !pm_req_ready_i;
      if(pm_req_valid_o && !pm_req_ready_i && !pm_offered) begin pm_hold_address<=pm_req_address_o; pm_hold_owner<=trace_pm_owner_o; end
      if(pm_fire) pm_outstanding<=1;
      if(pm_done) pm_outstanding<=0;
      if (release_valid_i && release_ready_o && release_sequence_i>last_release && release_epoch_i>0) begin
        authorized<=1; cert_epoch<=release_epoch_i; last_release<=release_sequence_i; life<=INVALID;
      end
      if (cfg_response && cfg_rsp_ready_i) begin
        cfg_response<=0; cfg_busy<=0;
        if (cfg_op==2 && cfg_status==0) readback<=readback+16;
      end
      if (cfg_fire) begin
        cfg_busy<=1; cfg_op<=cfg_req_op_i; cfg_address<=cfg_req_address_i; cfg_data<=cfg_req_data_i;
        cfg_mem_wait<=0; cfg_response<=1; cfg_status<=0; cfg_read_data<=0;
        if (cfg_req_op_i==0) begin
          if ((life==INVALID || life==READY) && cfg_meta_ok) begin
            generation<=cfg_req_generation_i; total<=cfg_req_total_bytes_i;
            image_id<=cfg_req_image_id_i; topology<=cfg_req_topology_id_i;
            abi_id<=cfg_req_abi_id_i; capacity_id<=cfg_req_capacity_id_i;
            written<=0; readback<=0; header<=0; prepared<=0; life<=LOADING;
          end else cfg_status<=3;
        end else if (cfg_req_generation_i!=generation) begin
          cfg_status<=8;
          if (life==LOADING || life==VERIFIED || life==PREPARED) begin prepared<=0; life<=INVALID; end
        end
        else case (cfg_req_op_i)
          1,2: begin
            if (life==LOADING && cfg_req_address_i[3:0]==0 &&
                {2'b0,cfg_req_address_i}+16'd16<=total &&
                (cfg_req_op_i==1 ? {2'b0,cfg_req_address_i}==written : written==total && {2'b0,cfg_req_address_i}==readback))
              cfg_response<=0;
            else begin
              cfg_status<=6;
              if (life==LOADING || life==VERIFIED || life==PREPARED) begin prepared<=0; life<=INVALID; end
            end
          end
          3: begin
            if (life==LOADING && written==total && readback==total && cfg_req_proof_i && header_ok)
              life<=VERIFIED;
            else begin cfg_status<=3; prepared<=0; life<=INVALID; end
          end
          4: begin
            if (life==VERIFIED) begin prepared<=1; life<=PREPARED; end
            else begin cfg_status<=7; if (life==LOADING || life==PREPARED) begin prepared<=0; life<=INVALID; end end
          end
          5: begin prepared<=0; life<=INVALID; end
          default: begin
            cfg_status<=1;
            if (life==LOADING || life==VERIFIED || life==PREPARED) begin prepared<=0; life<=INVALID; end
          end
        endcase
      end
      if(life==PREPARED && deployed && !cfg_busy) life<=READY;
      if(life==READY && !deployed) begin prepared<=0; life<=INVALID; end
      if(pm_fire) begin
        if(cfg_busy) cfg_mem_wait<=1;
        else if(!aborting && !poisoned) seq<=seq==BIND_REQ ? BIND_WAIT : FETCH_WAIT;
      end
      if(pm_done) begin
        if(cfg_busy) begin
          cfg_mem_wait<=0; cfg_response<=1;
          if(pm_rsp_error_i) begin cfg_status<=10; prepared<=0; life<=INVALID; end
          else if(cfg_op==1) begin written<=written+16; if(cfg_address<128) header[cfg_address*8 +: 128]<=cfg_data; end
          else begin
            cfg_read_data<=pm_rsp_data_i;
            if(bad_instruction_padding) cfg_status<=5;
          end
        end else if(!aborting && !poisoned) begin
          if(pm_rsp_error_i) fault(10);
          else if(seq==BIND_WAIT) begin
            event_cache[bind_index]<=pm_rsp_data_i;
            if({12'b0,bind_index}+16'd1==binding_count) begin bind_index<=0; seq<=BIND_CHECK; end
            else begin bind_index<=bind_index+1'b1; seq<=BIND_REQ; end
          end else if(seq==FETCH_WAIT) begin ireg<=fetch_instruction; ireg_valid<=1; seq<=DECODE; end
        end
      end
      if(start_fire) begin
        life<=RUNNING; seq<=binding_count!=0 ? BIND_REQ : FETCH_REQ; bind_index<=0; binding_consumed<=0;
        pc<=header[128+:32]; steps<=0; stall_count<=0; ireg_valid<=0; job<=start_job_i; epoch<=start_epoch_i;
        job_sequence<=start_sequence_i; last_start<=start_sequence_i; enabled<=local_enabled_i;
        for(bj=0;bj<9;bj=bj+1) local_ids[bj]<=local_image_ids_i[32*bj+:32];
        block_active<=0; block_accepted<=0; terminal_full<=0; ready_full<=0; cancel_sent<=0; live_tokens<=0;
        out_valid<=0; aborting<=0; result_valid<=0; error_status<=0; protocol_fault_count<=0; error_pc<=32'hffffffff; error_source<=255;
        child_error_pc<=32'hffffffff; failed_task_sequence<=0; confirmed_reads<=0; confirmed_writes<=0; counter_overflow<=0; saturated<=0;
        // This first profile declares scalar_parameter_words=0. Future G_PARAM
        // support must read an explicitly declared immutable parameter area.
        for(ri=0;ri<8;ri=ri+1) registers[ri]<=0;
      end
      if(normal_issue) begin
        if(seq==BIND_REQ && !bind_address_ok) fault(6);
        if(seq==BIND_CHECK) begin if(!bindings_ok) fault(5); else seq<=FETCH_REQ; end
        if(seq==FETCH_REQ) begin
          if(steps>=max_steps) fault(12);
          else if(pc>=inst_count || fetch_address+64'd16>{48'b0,total}) fault(6);
        end
        if(seq==DECODE && ireg_valid) case(opcode)
          8'h10: begin
            if(ireg[119:112]!=0 || ia>=9 || ib>=16 || ic!=0 || ireg[87:0]!=0) fault(2);
            else if(!enabled[ia[3:0]]) fault(4);
            else if(block_active[ia[3:0]] || live_tokens[ib[3:0]] || out_valid || next_sequence[ia[3:0]]==32'hffffffff) fault(7);
            else begin
              block_active[ia[3:0]]<=1; block_accepted[ia[3:0]]<=0; terminal_full[ia[3:0]]<=0; ready_full[ia[3:0]]<=0;
              cancel_sent[ia[3:0]]<=0; block_token[ia[3:0]]<=ib[3:0]; context_packet[ia[3:0]]<=call_word;
              for(bj=0;bj<9;bj=bj+1)if(bj<binding_count&&event_cache[bj][8+:8]==ia)
                binding_consumed[bj]<=0;
              next_sequence[ia[3:0]]<=next_sequence[ia[3:0]]+1; live_tokens<=live_tokens|(16'b1<<ib[3:0]);
              out_packet<=call_word; out_valid<=1; seq<=CALL_HOLD;
            end
          end
          8'h11: begin
            if(!wait_fields || !wait_allocated) fault(7);
            else if(wait_done) begin
              if(!wait_events_clear) fault(7);
              else begin
                live_tokens<=live_tokens&~wait_mask[15:0];
                for(bj=0;bj<9;bj=bj+1) if(block_active[bj] && wait_mask[{1'b0,block_token[bj]}]) begin
                  block_active[bj]<=0; block_accepted[bj]<=0; terminal_full[bj]<=0; cancel_sent[bj]<=0;
                end
                ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=FETCH_REQ;
              end
            end
          end
          8'h12: begin
            if(!event_fields) fault(2);
            else if(!event_found) fault(5);
            else if(binding_consumed[event_slot]) fault(7);
            else if(event_available) begin
              registers[ia[2:0]]<=ready_scalar[event_source]; ready_full[event_source]<=0;
              binding_consumed[event_slot]<=1; ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=FETCH_REQ;
            end
          end
          8'h13: begin
            if(!movi_fields) fault(2);
            else begin registers[ia[2:0]]<=ireg[63:32]; ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=FETCH_REQ; end
          end
          8'h15: begin
            if(!compact_image) fault(1);
            else if(!branch_fields_ok) fault(2);
            else if(!branch_targets_ok) fault(6);
            else begin pc<=branch_next_pc; ireg_valid<=0; steps<=steps+1; seq<=FETCH_REQ; end
          end
          8'h16: begin
            if(!addi64_fields||pointer_sum[64]) fault(18);
            else begin
              registers[{ia[2:1],1'b0}]<=pointer_sum[31:0];
              registers[{ia[2:1],1'b1}]<=pointer_sum[63:32];
              ireg_valid<=0;pc<=pc+1;steps<=steps+1;seq<=FETCH_REQ;
            end
          end
          8'h17: begin
            if(!loop_fields||!loop_target_ok||!loop_count_ok) fault(19);
            else begin
              registers[ia[2:0]]<=registers[ia[2:0]]-1'b1;
              pc<=registers[ia[2:0]]>1?ireg[63:32]:pc+1;
              ireg_valid<=0;steps<=steps+1;seq<=FETCH_REQ;
            end
          end
          8'h1f: begin
            if(ireg[119:0]!=0) fault(2);
            else if(live_tokens!=0 || block_active!=0 || terminal_full!=0 || ready_full!=0 || out_valid || !all_bindings_consumed) fault(7);
            else begin result_valid<=1; seq<=RESULT_HOLD; end
          end
          default: fault(1);
        endcase
      end
      if(task_fire) begin
        out_valid<=0;
        if(out_packet[16+:8]==0) begin
          block_accepted[out_packet[24+:4]]<=1;
          if(!poisoned) begin ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=aborting || incoming_error ? ERROR_DRAIN : FETCH_REQ; end
        end else cancel_sent[out_packet[24+:4]]<=1;
      end
      if(return_fire) begin
        if(return_terminal) begin
          terminal_full[return_sb]<=1;
          confirmed_reads<=read_sum[32] ? 32'hffffffff : read_sum[31:0];
          confirmed_writes<=write_sum[32] ? 32'hffffffff : write_sum[31:0];
          counter_overflow<=counter_overflow || read_sum[32] || write_sum[32]; saturated<=saturated || return_packet_i[256];
          if(return_kind==3) begin
            if(error_status==0) begin
              error_status<=return_packet_i[144+:16]; error_pc<=pc; error_source<=return_packet_i[24+:8];
              child_error_pc<=return_packet_i[320+:32]; failed_task_sequence<=return_packet_i[96+:32];
            end
            aborting<=1;
            if(!out_valid || out_packet[16+:8]!=0) begin ireg_valid<=0; seq<=ERROR_DRAIN; end
          end
        end else begin ready_scalar[return_sb]<=return_packet_i[160+:32]; ready_full[return_sb]<=1; end
      end
      if((life==RUNNING || life==POISONED) && aborting) begin
        ready_full<=0;
        if(!out_valid) begin
          // Ascending deterministic cancellation; one held packet at a time.
          for(bj=8;bj>=0;bj=bj-1) if(block_active[bj] && block_accepted[bj] &&
              !terminal_full[bj] && !cancel_sent[bj] &&
              !(return_fire && return_terminal && return_sb==4'(bj))) begin
            out_packet<=context_packet[bj];out_packet[16+:8]<=1;out_packet[256+:256]<=0;out_valid<=1;
          end
        end
        if(!poisoned && (terminal_full&block_active)==block_active && !out_valid && !pm_outstanding && !pm_offered) begin
          live_tokens<=0; block_active<=0; block_accepted<=0; terminal_full<=0; ready_full<=0;
          ireg_valid<=0; result_valid<=1; seq<=RESULT_HOLD;
        end
      end
      if(result_fire) begin
        result_valid<=0; aborting<=0; ireg_valid<=0;
        if(!poisoned) begin life<=READY; seq<=IDLE; if(error_status==0) steps<=steps+1; end
      end
      if(life==RUNNING && !result_valid) begin
        if(pm_fire || pm_done || task_fire || return_fire || trace_retire_o) stall_count<=0;
        else if(active_stall_limit!=0 && stall_count>=active_stall_limit-1) begin
          fault(14); poisoned<=1; prepared<=0; life<=POISONED;
        end
        else if(stall_count!=32'hffffffff) stall_count<=stall_count+1;
      end
      if(bad_return) begin
        if(protocol_fault_count!=32'hffffffff) protocol_fault_count<=protocol_fault_count+1;
        if(life==RUNNING && !result_valid) fault(17);
      end
      if(life==RUNNING && !result_valid && !deployed) begin fault(15);poisoned<=1;prepared<=0;life<=POISONED;end
      if(recover_valid_i && recover_ready_o) begin
        poisoned<=0;prepared<=0;life<=INVALID;seq<=IDLE;aborting<=0;result_valid<=0;
        block_active<=0;block_accepted<=0;terminal_full<=0;ready_full<=0;cancel_sent<=0;live_tokens<=0;ireg_valid<=0;
      end
    end
  end
endmodule
