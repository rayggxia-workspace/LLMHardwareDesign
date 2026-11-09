"""Prepare a fair stored/direct U benchmark from frozen production wiring."""
import hashlib
import json
from pathlib import Path

TB='project/experiments/pu_leaf_base/tb_pu_u_group.sv'
TB_SHA='ac7a3949f79d5b27d984f3b9516de119388a2ca01d7d0ad3d868e35f9585cb3a'

METRICS=r'''
    integer native_cycles=0,s_reads=0,s_writes=0,n_commands=0,e_commands=0,direct_transfers=0,e_input_beats=0;
    always @(posedge clk) begin
        native_cycles=native_cycles+1;
        if(!reset) begin
            if(dut.mem_req && dut.mem_ready) begin
                if(dut.mem_write) s_writes=s_writes+1;
                else s_reads=s_reads+1;
            end
            if(service_valid[1] && cmd_ready[1]) n_commands=n_commands+1;
            if(service_valid[0] && cmd_ready[0]) e_commands=e_commands+1;
            if(direct_source_valid && direct_connect && direct_ready) direct_transfers=direct_transfers+1;
            if(dut.e_valid && dut.e_ready) e_input_beats=e_input_beats+1;
        end
    end
'''

BODY=r'''
    task automatic group_reset;
        reset=1;direct_mode=0;direct_connect=0;
        cmd_valid=0;done_ready=0;pair_req=0;pair_take=0;
        rx_valid=0;rx_stored_ready=0;tx_req=0;tx_take=0;
        repeat(3) tick();reset=0;repeat(2) tick();
    endtask
    task automatic prepare_data(input integer tiles);
        group_reset();
        write_word(0,{8{16'hdead}}); // Direct A must ignore the dummy replay slot.
        write_word(6,{8{16'd25}});
        write_word(20,{8{16'd1024}});
        write_word(21,128'd1);
        write_word(30,128'hcafe);
        write_word(40,128'hcafe);
        // Identical RMS context for each compared route. Input and gamma are
        // the same word; per-tile normalized result is eight signed16 1024s.
        execute(1,64'h100,1,30'd21,0,0,answer);
        for(integer tile=0;tile<tiles;tile=tile+1)
            execute(1,64'h81,1,30'd20,0,0,answer);
        execute(1,2,0,0,0,0,answer);
    endtask
    task automatic stored_pair(input integer delay_cycles);
        direct_mode=0;direct_connect=0;
        execute(1,64'h85,2,{10'd0,10'd20,10'd20},1,30,answer);
        if(answer!=={8{16'd1024}}) $fatal(1,"STORED_N_NUMERIC");
        repeat(delay_cycles) tick();
        execute(0,0,2,{10'd0,10'd6,10'd30},1,40,answer);
        if(answer!=={8{16'd1049}}) $fatal(1,"STORED_E_NUMERIC");
    endtask
    task automatic direct_pair(input integer delay_cycles,input [39:0] nmeta,
                               input bit enable,input [15:0] expected_status);
        reg [127:0] held;
        direct_mode=1;direct_connect=0;pair_enable=enable;
        pair_descriptor=0;
        pair_descriptor[32+:16]=16'h104;
        pair_descriptor[512+:32]=2;
        pair_descriptor[544+:20]={10'd20,10'd20};
        pair_descriptor[576+:40]=nmeta;
        pair_descriptor[640+:32]=(32'd40<<9); // E ADD, shift0, destination40.
        pair_descriptor[672+:20]=20'd6; // B=6; direct A occupies the dummy slot.
        pair_req=1;
        do @(posedge clk);while(!pair_ready);
        @(negedge clk);pair_req=0;
        if(expected_status==0) begin
            while(!direct_source_valid || !direct_ready) tick();
            held=direct_source_data;
            if(held!=={8{16'd1024}}) $fatal(1,"DIRECT_N_NUMERIC");
            repeat(delay_cycles) begin
                if(!direct_source_valid || direct_source_data!==held || done_valid!=0 || pair_rsp)
                    $fatal(1,"DIRECT_HANDOFF_BACKPRESSURE");
                tick();
            end
            direct_connect=1;tick();direct_connect=0;
            if(direct_source_valid) $fatal(1,"DIRECT_BEAT_NOT_RETIRED");
        end
        while(!pair_rsp) tick();
        if(pair_status!=expected_status || pair_writes!=(expected_status==0 ? 16 : 0))
            $fatal(1,"DIRECT_STATUS status=%0d expected=%0d writes=%0d",pair_status,expected_status,pair_writes);
        if(expected_status==0 && (pair_reads!=48 || done_data[127:0]!=={8{16'd1049}}))
            $fatal(1,"DIRECT_E_NUMERIC_OR_BYTE_RECEIPT");
        pair_take=1;tick();pair_take=0;direct_mode=0;
    endtask
    task automatic measure(input bit direct_route,input integer tiles,input integer delay_cycles);
        integer start_cycle,start_reads,start_writes,start_n,start_e,start_direct;
        integer elapsed,reads,writes;
        prepare_data(tiles);
        start_cycle=native_cycles;start_reads=s_reads;start_writes=s_writes;
        start_n=n_commands;start_e=e_commands;start_direct=direct_transfers;
        for(integer tile=0;tile<tiles;tile=tile+1) begin
            if(direct_route) direct_pair(delay_cycles,40'h85,1,0);
            else stored_pair(delay_cycles);
        end
        elapsed=native_cycles-start_cycle;reads=s_reads-start_reads;writes=s_writes-start_writes;
        if(reads!=(direct_route ? 3 : 4)*tiles || writes!=(direct_route ? 1 : 2)*tiles ||
           n_commands-start_n!=tiles || e_commands-start_e!=tiles ||
           direct_transfers-start_direct!=(direct_route ? tiles : 0))
            $fatal(1,"NATIVE_TRANSACTION_CONSERVATION direct=%0d tiles=%0d reads=%0d writes=%0d",direct_route,tiles,reads,writes);
        // Readback is deliberately outside both the cycle and S-transaction interval.
        expect_word(40,{8{16'd1049}});
        expect_word(30,direct_route ? 128'hcafe : {8{16'd1024}});
        $display("NATIVE_FUSION_MEASURE direct=%0d tiles=%0d delay=%0d cycles=%0d S_reads=%0d S_writes=%0d N_commands=%0d E_commands=%0d direct_beats=%0d result=1049",direct_route,tiles,delay_cycles,elapsed,reads,writes,n_commands-start_n,e_commands-start_e,direct_transfers-start_direct);
    endtask
    task automatic cancellation_checks;
        integer before_writes,before_direct,before_e_beats;
        prepare_data(1);
        before_writes=s_writes;before_direct=direct_transfers;before_e_beats=e_input_beats;
        direct_pair(0,40'hf,1,16'd9); // Illegal N operation must abort waiting E.
        if(s_writes!=before_writes || direct_transfers!=before_direct || e_input_beats!=before_e_beats)
            $fatal(1,"N_ERROR_DID_NOT_CANCEL_E");
        expect_word(40,128'hcafe);
        before_writes=s_writes;before_direct=direct_transfers;
        direct_pair(0,40'h85,0,16'd5);
        if(s_writes!=before_writes || direct_transfers!=before_direct) $fatal(1,"DISABLED_DIRECT_EXECUTED");
        expect_word(40,128'hcafe);
        $display("NATIVE_FUSION_CANCEL_PASS N_error_status=9 disabled_status=5 output_unchanged=1");
    endtask
    task automatic reset_held_check;
        prepare_data(1);
        direct_mode=1;direct_connect=0;pair_enable=1;pair_descriptor=0;
        pair_descriptor[32+:16]=16'h104;pair_descriptor[512+:32]=2;
        pair_descriptor[544+:20]={10'd20,10'd20};pair_descriptor[576+:40]=40'h85;
        pair_descriptor[640+:32]=(32'd40<<9);pair_descriptor[672+:20]=20'd6;
        pair_req=1;do @(posedge clk);while(!pair_ready);
        @(negedge clk);pair_req=0;
        while(!direct_source_valid || !direct_ready) tick();
        reset=1;repeat(3) tick();reset=0;repeat(4) tick();
        if(direct_source_valid || done_valid!=0 || pair_rsp || tx_valid || rx_stored)
            $fatal(1,"RESET_EXPOSED_STALE_DIRECT_DATA");
        direct_mode=0;expect_word(40,128'hcafe);
        $display("NATIVE_FUSION_RESET_PASS held_producer_cancelled=1 no_stale_output=1");
    endtask
    initial begin
        repeat(2) tick();
        measure(0,1,0);measure(1,1,0);
        measure(0,16,0);measure(1,16,0);
        measure(0,1,4);measure(1,1,4);
        measure(0,16,4);measure(1,16,4);
        cancellation_checks();reset_held_check();
        $display("NATIVE_FUSION_PASS routes=2 tile_counts=1,16 handoff_delays=0,4 no_engine_replication=1");
        $finish;
    end
    initial begin
        repeat(200000) @(posedge clk);
        $fatal(1,"NATIVE_FUSION_WATCHDOG");
    end
endmodule
'''


def render(repo,out):
    raw=(repo/TB).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=TB_SHA:raise ValueError('frozen U benchmark identity drift')
    text=raw.decode('utf-8')
    anchor='    task automatic run_pair('
    if text.count(anchor)!=1:raise ValueError('nonunique U benchmark boundary')
    text=text[:text.index(anchor)]+BODY
    if text.count('module tb_pu_u_group;')!=1:raise ValueError('nonunique U benchmark module')
    text=text.replace('module tb_pu_u_group;','module tb_fusion_native;\n'+METRICS,1)
    out.mkdir(parents=True,exist_ok=False)
    (out/'bench.sv').write_bytes(text.encode())
    manifest=dict(upstream_bench=TB,upstream_sha256=TB_SHA,
        generated_bench_sha256=hashlib.sha256(text.encode()).hexdigest(),
        change='reuse frozen production U wiring and original helper tasks; replace test program with matched RMS->ADD routes and passive counters',
        scope='S16 production RTL finite pair latency and serialized repeated-tile program; not native S32 model or multi-pair inflight pipeline')
    (out/'bench-source.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
    return manifest
