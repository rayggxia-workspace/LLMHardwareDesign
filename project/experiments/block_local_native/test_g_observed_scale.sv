`timescale 1ns/1ps
module test_g_observed_scale;
    reg [127:0] cmd_key=128'h123450,done_key;
    reg [15:0] cmd_kk=16'd256,done_kk;
    wire [5:0] done_a_shift;
    reg clk=0;
    always #10 clk=!clk;
    reg reset=1, cmd_valid=0, done_take=0, host=1;
    reg [9:0] cmd_gate_base=0, cmd_up_base=64, cmd_mid_base=128;
    reg [5:0] cmd_words=32;
    reg cmd_gated=1;
    wire cmd_ready, done_valid, done_error;
    wire [5:0] done_words;
    wire s_req_valid,s_req_write,s_req_ready,s_rsp_valid,s_rsp_ready;
    wire [9:0] s_req_addr;
    wire [127:0] s_req_data,s_rsp_data;
    wire g_in_valid,g_in_ready,g_in_gated,g_out_valid,g_out_ready,g_out_error;
    wire [63:0] g_in_gate,g_in_up,g_out_data;
    wire [1:0] g_in_mask,g_out_mask;
    g_s128_observed_scale dut(.*);
    g_s32 kernel(.clk,.reset,.in_valid(g_in_valid),.in_ready(g_in_ready),
        .in_gate(g_in_gate),.in_up(g_in_up),.in_gated(g_in_gated),.in_mask(g_in_mask),
        .out_valid(g_out_valid),.out_ready(g_out_ready),.out_data(g_out_data),
        .out_mask(g_out_mask),.out_error(g_out_error));
    reg h_req=0,h_write=0,h_take=0;
    reg [9:0] h_addr=0;
    reg [127:0] h_data=0;
    wire mem_ready,mem_valid;
    wire [127:0] mem_data;
    wire unused_load_ready,unused_done_valid,unused_done_error;
    wire [127:0] unused_a_data;
    wire [511:0] unused_b_data;
    integer cycle=0,mode=0;
    wire request_enable=(mode!=1 && mode!=4) || cycle%7!=2;
    wire response_enable=(mode!=1 && mode!=4) || cycle%11>=4;
    assign s_req_ready=!host && mem_ready && request_enable;
    assign s_rsp_valid=!host && mem_valid && response_enable;
    assign s_rsp_data=mem_data;
    local_s_p storage(.clk,.reset,.req_valid(host?h_req:s_req_valid&&request_enable),
        .req_write(host?h_write:s_req_write),.req_addr(host?h_addr:s_req_addr),
        .req_data(host?h_data:s_req_data),.req_ready(mem_ready),.rsp_valid(mem_valid),
        .rsp_ready(host?h_take:s_rsp_ready&&response_enable),.rsp_data(mem_data),
        .load_valid(1'b0),.load_ready(unused_load_ready),.load_bank(1'b0),.load_rows(4'd1),
        .load_tiles(3'd1),.load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b1),
        .load_a_base(10'd0),.load_b_base(10'd0),.done_valid(unused_done_valid),
        .done_take(1'b1),.done_error(unused_done_error),.a_valid(),.a_ready(1'b1),
        .a_bank(),.a_row(),.a_tile(),.a_wide(),.a_data(unused_a_data),
        .b_valid(),.b_ready(1'b1),.b_bank(),.b_tile(),.b_wide(),.b_half(),.b_data(unused_b_data));

    reg [63:0] gates[0:63],ups[0:63],expected[0:63];
    reg [63:0] file_gate,file_up,file_result;
    reg [1:0] file_mask;
    integer fd,scan,count,file_gated,file_error;
    string vector_file;
    reg measure=0, expect_fault=0;
    integer fault_word=0;
    integer first_request=-1,last_ack=-1,requests=0,writes=0,acks=0,inputs=0,outputs=0;
    reg tags[0:1];
    integer th=0,tt=0,tc=0;
    reg held_req=0,held_input=0;
    reg [138:0] held_req_bits;
    reg [130:0] held_input_bits;

    task automatic access(input bit write_en,input integer address,input reg [127:0] data,
                          output reg [127:0] result);
        @(negedge clk); h_req=1;h_write=write_en;h_addr=10'(address);h_data=data;
        do @(posedge clk);while(!mem_ready);
        @(negedge clk);h_req=0;
        while(!mem_valid)@(negedge clk);
        result=mem_data;h_take=1;
        @(negedge clk);h_take=0;
    endtask

    task automatic start_frame;
        @(negedge clk);host=0;measure=1;cmd_valid=1;
        first_request=-1;last_ack=-1;requests=0;writes=0;acks=0;inputs=0;outputs=0;th=0;tt=0;tc=0;
        do @(posedge clk);while(!cmd_ready);
        @(negedge clk);cmd_valid=0;
    endtask

    task automatic finish_frame;
        while(!done_valid)begin
            @(negedge clk);
            if(cycle>10000)$fatal(1,"frontend progress watchdog");
        end
        if(done_key!==cmd_key || done_kk!==cmd_kk)$fatal(1,"scale identity lost");
        if(expect_fault && done_a_shift!==0)$fatal(1,"fault published scale");
        if(!expect_fault)begin
            reference_maximum=0;
            for(integer packet_index=0;packet_index<2*int'(cmd_words);packet_index=packet_index+1)begin
                for(integer lane=0;lane<2;lane=lane+1)begin
                    reference_sample=64'($signed(expected[packet_index][32*lane+:32]));
                    if(reference_sample<0)reference_sample=-reference_sample;
                    if(reference_sample>reference_maximum)reference_maximum=reference_sample;
                end
            end
            reference_shift=0;
            while((64'd32767<<reference_shift)<reference_maximum)reference_shift=reference_shift+1;
            if(done_a_shift!==6'(reference_shift))$fatal(1,"observed G scale mismatch");
        end
        if(done_error!==expect_fault)$fatal(1,"frontend unexpected error=%b",done_error);
        if(!expect_fault && (done_words!==cmd_words || requests!=3*int'(cmd_words) ||
            writes!=int'(cmd_words) || acks!=int'(cmd_words) || inputs!=2*int'(cmd_words) ||
            outputs!=2*int'(cmd_words)))$fatal(1,"frontend service counts %0d %0d %0d %0d %0d %0d",done_words,requests,writes,acks,inputs,outputs);
        if(expect_fault && (writes>fault_word || done_words!==6'(acks) || writes!=acks))
            $fatal(1,"fault corrupted/failed to drain committed prefix");
        if(mode==4 && cmd_words!=0 && writes==0)$fatal(1,"late fault did not exercise committed prefix");
        if(mode==0 && cmd_words==32 && !expect_fault && last_ack-first_request+1!=107)
            $fatal(1,"continuous service changed: first=%0d lastACK=%0d inclusive=%0d",first_request,last_ack,last_ack-first_request+1);
        $display("G_S128_FRAME mode=%0d words=%0d first_request=%0d last_ack=%0d occupied_cycles=%0d requests=%0d writes=%0d ACK=%0d G_in=%0d G_out=%0d fault=%0d",mode,cmd_words,first_request,last_ack,last_ack<0?0:last_ack-first_request+1,requests,writes,acks,inputs,outputs,expect_fault);
        $display("G_S128_DONE_ASSERT cycle=%0d valid_after_ack_delta=%0d earliest_clocked_take=%0d",cycle,last_ack<0?-1:cycle-last_ack,cycle+1);
        repeat(5)begin
            @(negedge clk);
            if(!done_valid || done_error!==expect_fault || cmd_ready || s_req_valid)
                $fatal(1,"completion ownership lost before take");
        end
        done_take=1;
        @(negedge clk);done_take=0;measure=0;host=1;
    endtask

    reg signed [63:0] reference_maximum,reference_sample;
    integer reference_shift;
    reg [127:0] scratch;
    initial begin
        if(!$value$plusargs("mode=%d",mode))mode=0;
        if(!$value$plusargs("vectors=%s",vector_file))$fatal(1,"vectors missing");
        fd=$fopen(vector_file,"r");if(fd==0)$fatal(1,"vectors open failed");
        scan=$fscanf(fd,"%d\n",count);if(scan!=1 || count!=8048)$fatal(1,"actual model vector count changed");
        for(integer i=0;i<count;i=i+1)begin
            scan=$fscanf(fd,"%h %h %d %h %h %d\n",file_gate,file_up,file_gated,file_mask,file_result,file_error);
            if(scan!=6)$fatal(1,"bad oracle row");
            if(i>=count-2048 && i<count-2048+64)begin
                if(file_gated!=1 || file_mask!=3 || file_error!=0)$fatal(1,"bad actual tensor packet");
                gates[i-(count-2048)]=file_gate;ups[i-(count-2048)]=file_up;expected[i-(count-2048)]=file_result;
            end
        end
        $fclose(fd);
        repeat(4)@(negedge clk);reset=0;
        for(integer i=0;i<32;i=i+1)begin
            access(1,i,{gates[2*i+1],gates[2*i]},scratch);
            access(1,64+i,{ups[2*i+1],ups[2*i]},scratch);
            access(1,128+i,128'h1234,scratch);
        end
        if(mode==3 || mode==4)begin
            fault_word=mode==3?0:3;
            access(1,fault_word,128'h7fffffff7fffffff7fffffff7fffffff,scratch);
            access(1,64+fault_word,128'h7fffffff7fffffff7fffffff7fffffff,scratch);
            expect_fault=1;
        end
        start_frame();
        if(mode==2)begin
            repeat(20)@(negedge clk);
            reset=1;cmd_valid=0;measure=0;
            repeat(3)@(negedge clk);
            reset=0;
            start_frame();
        end
        finish_frame();
        if(mode!=3 && mode!=4)begin
            for(integer i=0;i<32;i=i+1)begin
                access(0,128+i,0,scratch);
                if(scratch!=={expected[2*i+1],expected[2*i]})$fatal(1,"actual SRAM Mid mismatch %0d",i);
            end
            cmd_words=1;start_frame();finish_frame();
            access(0,128,0,scratch);
            if(scratch!=={expected[1],expected[0]})$fatal(1,"single word SRAM mismatch");
            cmd_words=7;start_frame();finish_frame();
            for(integer i=0;i<7;i=i+1)begin
                access(0,128+i,0,scratch);
                if(scratch!=={expected[2*i+1],expected[2*i]})$fatal(1,"odd word count SRAM mismatch");
            end
        end
        // An invalid command must finish with no request, then retain done.
        expect_fault=1;fault_word=0;cmd_words=0;start_frame();finish_frame();
        $display("G_SCALE_PASS mode=%0d payload_hold_bytes=96 added_SRAM_bytes=0 actual_model_values=128",mode);
        $finish;
    end

    always @(posedge clk)begin
        cycle=cycle+1;
        if(reset)begin held_req=0;held_input=0;th=0;tt=0;tc=0;end
        else if(measure)begin
            if(held_req && (!s_req_valid || {s_req_write,s_req_addr,s_req_data}!==held_req_bits))
                $fatal(1,"S request changed while stalled");
            held_req=s_req_valid&&!s_req_ready;
            if(held_req)held_req_bits={s_req_write,s_req_addr,s_req_data};
            if(held_input && (!g_in_valid || {g_in_gate,g_in_up,g_in_gated,g_in_mask}!==held_input_bits))
                $fatal(1,"G input changed while stalled");
            held_input=g_in_valid&&!g_in_ready;
            if(held_input)held_input_bits={g_in_gate,g_in_up,g_in_gated,g_in_mask};
            if(s_rsp_valid&&s_rsp_ready)begin
                if(tc==0)$fatal(1,"unowned S response");
                if(tags[th])begin
                    if(s_rsp_data!==0)$fatal(1,"write ACK payload must be zero");
                    acks=acks+1;last_ack=cycle;
                    $display("FRONTEND_ACK,%0d,%0d",cycle,acks);
                end
                th=1-th;tc=tc-1;
            end
            if(s_req_valid&&s_req_ready)begin
                if(first_request<0)first_request=cycle;
                if(s_req_write)begin
                    if((expect_fault && writes>=fault_word) || s_req_addr!==10'(128+writes) || s_req_data!=={expected[2*writes+1],expected[2*writes]})
                        $fatal(1,"wrong/premature SRAM write %0d",writes);
                    writes=writes+1;
                end
                tags[tt]=s_req_write;tt=1-tt;tc=tc+1;requests=requests+1;
                if(tc>2)$fatal(1,"more than two owned S transactions");
                $display("FRONTEND_SREQ,%0d,%0d,%0d",cycle,s_req_write,s_req_addr);
            end
            if(g_in_valid&&g_in_ready)begin
                if(!expect_fault && (g_in_gate!==gates[inputs] || g_in_up!==ups[inputs] || !g_in_gated || g_in_mask!==3))
                    $fatal(1,"wrong SRAM/G input order %0d",inputs);
                inputs=inputs+1;
            end
            if(g_out_valid&&g_out_ready)begin
                if(!expect_fault && (g_out_error || g_out_mask!==3 || g_out_data!==expected[outputs]))
                    $fatal(1,"wrong actual tensor G output %0d",outputs);
                outputs=outputs+1;
            end
        end
    end
endmodule
