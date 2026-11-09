"""Generate an isolated one-N/one-E FIFO-overlap bench; no production edits."""
import hashlib
import json
from pathlib import Path

TB='project/experiments/pu_leaf_base/tb_pu_u_group.sv'
TB_SHA='ac7a3949f79d5b27d984f3b9516de119388a2ca01d7d0ad3d868e35f9585cb3a'

WIRES=r'''
    reg pipeline_mode=0,pipe_start=0,pipe_take=0,consumer_enable=1;
    reg [7:0] pipe_tiles=0,pipe_delay=0;
    wire pipe_ready,pipe_done,pipe_fault,pipe_n_ready,pipe_e_valid;
    wire [127:0] pipe_e_data,pipe_meta;
    wire [1:0] pipe_cmd,pipe_store,pipe_done_ready;
    wire [3:0] pipe_sources;
    wire [59:0] pipe_addresses;
    wire [19:0] pipe_dst;
    wire [7:0] fifo_count,n_issued,n_retired,e_issued,e_retired,pushes,pops,max_inflight;
    u_overlap_control #(.DEPTH(DEPTH)) control (
        .clk,.reset,.start_valid(pipe_start),.start_ready(pipe_ready),
        .tile_count(pipe_tiles),.handoff_delay(pipe_delay),.consumer_enable,
        .stream_done(pipe_done),.stream_take(pipe_take),.fault(pipe_fault),
        .cmd_valid(pipe_cmd),.cmd_store(pipe_store),.done_ready(pipe_done_ready),
        .cmd_meta(pipe_meta),.cmd_sources(pipe_sources),.cmd_addresses(pipe_addresses),.cmd_dst(pipe_dst),
        .cmd_ready,.done_valid,.done_error,
        .n_result_valid(direct_source_valid),.n_result_ready(pipe_n_ready),.n_result_data(direct_source_data),
        .e_a_valid(pipe_e_valid),.e_a_ready(direct_ready),.e_a_data(pipe_e_data),
        .fifo_count,.n_issued,.n_retired,.e_issued,.e_retired,.pushes,.pops,.max_inflight
    );
'''

METRICS=r'''
    integer native_cycles=0,s_reads=0,s_writes=0,n_commands=0,e_commands=0,direct_transfers=0,n_handoffs=0;
    reg held_a=0,held_n=0;
    reg [127:0] held_a_data,held_n_data;
    always @(posedge clk) begin
        native_cycles=native_cycles+1;
        if(!reset) begin
            if(dut.mem_req && dut.mem_ready) begin
                if(dut.mem_write) s_writes=s_writes+1;
                else s_reads=s_reads+1;
            end
            if(service_valid[1] && cmd_ready[1]) n_commands=n_commands+1;
            if(service_valid[0] && cmd_ready[0]) e_commands=e_commands+1;
            if(pipeline_mode ? pipe_e_valid&&direct_ready : direct_source_valid&&direct_connect&&direct_ready)
                direct_transfers=direct_transfers+1;
            if(pipeline_mode && direct_source_valid && pipe_n_ready) begin
                n_handoffs=n_handoffs+1;
                if(direct_source_data!=={8{16'd1024}}) $fatal(1,"FIFO_N_NUMERIC");
            end
            if(pipeline_mode) begin
                if(held_a && (!pipe_e_valid || pipe_e_data!==held_a_data)) $fatal(1,"E_A_STABILITY");
                if(held_n && (!direct_source_valid || direct_source_data!==held_n_data)) $fatal(1,"N_RESULT_STABILITY");
                held_a=pipe_e_valid&&!direct_ready;held_a_data=pipe_e_data;
                held_n=direct_source_valid&&!pipe_n_ready;held_n_data=direct_source_data;
                if(pipe_e_valid && direct_ready && control.fifo_data[135:128]!==pops)
                    $fatal(1,"FIFO_TAG_ORDER");
            end else begin held_a=0;held_n=0;end
        end else begin held_a=0;held_n=0;end
    end
    always @(negedge clk) if(!reset && pipeline_mode) begin
        if(pipe_fault || fifo_count>8'(DEPTH) || pushes-pops!=fifo_count || n_retired>pushes ||
           e_retired>pops || pops>pushes || pushes>n_issued || e_issued>n_issued ||
           max_inflight>8'(DEPTH+2)) $fatal(1,"OWNERSHIP_CONSERVATION");
    end
'''

BODY=r'''
    function automatic [127:0] repeated(input integer value);
        repeated={8{16'(value)}};
    endfunction
    task automatic group_reset;
        reset=1;pipeline_mode=0;pipe_start=0;pipe_take=0;consumer_enable=1;
        direct_mode=0;direct_connect=0;pair_req=0;pair_take=0;
        cmd_valid=0;done_ready=0;rx_valid=0;rx_stored_ready=0;tx_req=0;tx_take=0;
        repeat(3) tick();
        if(fifo_count!=0 || pipe_e_valid || pipe_n_ready || pipe_done || pipe_cmd!=0)
            $fatal(1,"RESET_NOT_EMPTY");
        reset=0;repeat(2) tick();
    endtask
    task automatic prepare_data(input integer tiles);
        group_reset();
        write_word(0,{8{16'hdead}});
        write_word(20,{8{16'd1024}});write_word(21,128'd1);
        for(integer t=0;t<tiles;t=t+1) begin
            write_word(10'(128+t),repeated(25+t));write_word(10'(64+t),128'hcafe);
        end
        execute(1,64'h100,1,30'd21,0,0,answer);
        for(integer t=0;t<tiles;t=t+1) execute(1,64'h81,1,30'd20,0,0,answer);
        execute(1,2,0,0,0,0,answer);
    endtask
    task automatic verify_results(input integer tiles);
        for(integer t=0;t<tiles;t=t+1) expect_word(10'(64+t),repeated(1049+t));
    endtask
    task automatic serial_pair(input integer tile,input integer delay_cycles);
        reg [127:0] held;
        direct_mode=1;direct_connect=0;pair_enable=1;pair_descriptor=0;
        pair_descriptor[32+:16]=16'h104;
        pair_descriptor[512+:32]=2;pair_descriptor[544+:20]={10'd20,10'd20};
        pair_descriptor[576+:40]=40'h85;
        pair_descriptor[649+:10]=10'(64+tile);
        pair_descriptor[672+:20]=20'(128+tile);
        pair_req=1;do @(posedge clk);while(!pair_ready);
        @(negedge clk);pair_req=0;
        while(!direct_source_valid || !direct_ready) tick();
        held=direct_source_data;
        if(held!=={8{16'd1024}}) $fatal(1,"SERIAL_N_NUMERIC");
        repeat(delay_cycles) begin
            if(!direct_source_valid || direct_source_data!==held || pair_rsp || done_valid!=0)
                $fatal(1,"SERIAL_HANDOFF_HOLD");
            tick();
        end
        direct_connect=1;tick();direct_connect=0;
        while(!pair_rsp) tick();
        if(pair_status!=0 || pair_reads!=48 || pair_writes!=16 || done_data[127:0]!==repeated(1049+tile))
            $fatal(1,"SERIAL_E_NUMERIC_OR_RECEIPT");
        pair_take=1;tick();pair_take=0;direct_mode=0;
    endtask
    task automatic start_pipeline(input integer tiles,input integer delay_cycles);
        pipeline_mode=1;direct_mode=1;pipe_tiles=8'(tiles);pipe_delay=8'(delay_cycles);
        if(!pipe_ready || fifo_count!=0) $fatal(1,"PIPE_START_OWNERSHIP");
        pipe_start=1;tick();pipe_start=0;
    endtask
    task automatic finish_pipeline(input integer tiles);
        while(!pipe_done) tick();
        if(fifo_count!=0 || pushes!=8'(tiles) || pops!=8'(tiles) || n_issued!=8'(tiles) ||
           n_retired!=8'(tiles) || e_issued!=8'(tiles) || e_retired!=8'(tiles) ||
           direct_source_valid || pipe_e_valid) $fatal(1,"PIPE_NOT_DRAINED");
        pipe_take=1;tick();pipe_take=0;pipeline_mode=0;direct_mode=0;
    endtask
    task automatic measure(input bit overlapped,input integer tiles,input integer delay_cycles);
        integer c,r,w,n,e,d,h,elapsed;
        prepare_data(tiles);
        c=native_cycles;r=s_reads;w=s_writes;n=n_commands;e=e_commands;d=direct_transfers;h=n_handoffs;
        if(overlapped) begin start_pipeline(tiles,delay_cycles);finish_pipeline(tiles);end
        else for(integer t=0;t<tiles;t=t+1) serial_pair(t,delay_cycles);
        elapsed=native_cycles-c;
        if(s_reads-r!=3*tiles || s_writes-w!=tiles || n_commands-n!=tiles || e_commands-e!=tiles ||
           direct_transfers-d!=tiles || (overlapped && n_handoffs-h!=tiles))
            $fatal(1,"MEASURE_TRANSACTION_COUNTS");
        $display("OVERLAP_MEASURE depth=%0d overlap=%0d tiles=%0d delay=%0d cycles=%0d S_reads=%0d S_writes=%0d N_commands=%0d E_commands=%0d E_beats=%0d FIFO_pushes=%0d FIFO_pops=%0d max_inflight=%0d verified_slots=%0d",DEPTH,overlapped,tiles,delay_cycles,elapsed,s_reads-r,s_writes-w,n_commands-n,e_commands-e,direct_transfers-d,overlapped ? int'(pushes) : 0,overlapped ? int'(pops) : 0,overlapped ? int'(max_inflight) : 1,tiles);
        verify_results(tiles);
    endtask
    task automatic full_hold(input bit recover);
        reg [127:0] held;
        integer tiles;
        tiles=DEPTH+3;prepare_data(tiles);consumer_enable=0;start_pipeline(tiles,4);
        while(fifo_count!=8'(DEPTH) || !direct_source_valid || pipe_n_ready) tick();
        held=direct_source_data;
        repeat(8) begin
            if(!direct_source_valid || direct_source_data!==held || pipe_n_ready || fifo_count!=8'(DEPTH) || e_issued!=0)
                $fatal(1,"FIFO_FULL_HOLD");
            tick();
        end
        if(recover) begin
            consumer_enable=1;finish_pipeline(tiles);verify_results(tiles);
            $display("OVERLAP_FULL_PASS depth=%0d held_cycles=8 recovered_tiles=%0d max_inflight=%0d",DEPTH,tiles,max_inflight);
        end else begin
            group_reset();
            if(direct_source_valid || done_valid!=0 || fifo_count!=0 || pushes!=0 || pops!=0)
                $fatal(1,"RESET_STALE_RESULT");
            prepare_data(1);start_pipeline(1,0);finish_pipeline(1);verify_results(1);
            $display("OVERLAP_RESET_PASS depth=%0d held_producer_cancelled=1 empty_after_reset=1 fresh_tile_verified=1",DEPTH);
        end
    endtask
    initial begin
        for(integer route=0;route<2;route=route+1)
            for(integer sz=0;sz<3;sz=sz+1)
                for(integer bp=0;bp<2;bp=bp+1) measure(1'(route),sz==0 ? 1 : (sz==1 ? 16 : 32),bp*4);
        full_hold(1);full_hold(0);
        $display("OVERLAP_PASS depth=%0d routes=2 tile_counts=1,16,32 delays=0,4 one_N_one_E=1",DEPTH);
        $finish;
    end
    initial begin #20000000;$fatal(1,"OVERLAP_TIMEOUT");end
endmodule
'''


def render(repo,out):
    source=repo/TB
    if hashlib.sha256(source.read_bytes()).hexdigest()!=TB_SHA:
        raise ValueError('frozen production U testbench identity changed')
    text=source.read_text(encoding='utf-8')
    if text.count('    task automatic run_pair(')!=1:raise ValueError('testbench anchor drift')
    prefix=text.split('    task automatic run_pair(',1)[0]
    prefix=prefix.replace('module tb_pu_u_group;','module tb_overlap_native #(parameter integer DEPTH=2);',1)
    anchor='    pu_u_direct_pair pair_driver ('
    if prefix.count(anchor)!=1:raise ValueError('pair anchor drift')
    prefix=prefix.replace(anchor,WIRES+anchor)
    for name in ('cmd','store','done_ready','meta','sources','addresses','dst'):
        old='direct_mode ? pair_'+name+' : '
        new='pipeline_mode ? pipe_'+name+' : direct_mode ? pair_'+name+' : '
        if prefix.count(old)!=1:raise ValueError('service mux anchor '+name)
        prefix=prefix.replace(old,new)
    replacements={
        '.n_to_e_ready(direct_connect && direct_ready)':'.n_to_e_ready(pipeline_mode ? pipe_n_ready : direct_connect && direct_ready)',
        '.e_direct_a_valid(direct_connect && direct_source_valid)':'.e_direct_a_valid(pipeline_mode ? pipe_e_valid : direct_connect && direct_source_valid)',
        '.e_direct_a_data(direct_source_data)':'.e_direct_a_data(pipeline_mode ? pipe_e_data : direct_source_data)',
    }
    for old,new in replacements.items():
        if prefix.count(old)!=1:raise ValueError('direct endpoint anchor '+old)
        prefix=prefix.replace(old,new)
    out.mkdir(parents=True,exist_ok=False)
    bench=out/'bench_overlap.sv';bench.write_bytes((prefix+METRICS+BODY).encode())
    result=dict(source=TB,source_sha256=TB_SHA,bench_sha256=hashlib.sha256(bench.read_bytes()).hexdigest(),
                scope='same original U wiring and helpers; added isolated finite FIFO/controller; one unchanged N/E/S')
    (out/'bench-overlap-source.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(render(a.repo.resolve(),a.out.resolve()),indent=2))
