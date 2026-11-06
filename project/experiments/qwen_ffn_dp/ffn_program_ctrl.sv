// Scope-limited MC/LC program controller. Service adapters own native
// M/G/S transactions. An event is published only on service_done.
module ffn_program_ctrl (
    input wire clk, reset,
    input wire load, input wire [1:0] load_target, input wire [3:0] load_address,
    input wire [32:0] load_data,
    input wire start,
    output reg finished, failed, reserve_up,
    output wire [1:0] service_valid,
    output wire [65:0] service_word,
    input wire [1:0] service_ready, service_done, service_error
);
    reg [32:0] mother[0:7];
    reg [32:0] local_code[0:1][0:11];
    reg running;
    reg [3:0] mpc;
    reg [3:0] event_mask;
    reg [1:0] active, inflight;
    reg [3:0] pc[0:1];
    wire [32:0] mc=mother[mpc[2:0]];
    wire [9:0] a=mc[29:20], b=mc[19:10];
    wire [32:0] lc[0:1];
    for(genvar i=0;i<2;i++) begin : decode
        assign lc[i]=local_code[i][pc[i]];
        assign service_word[33*i+:33]=lc[i];
        assign service_valid[i]=running && active[i] && !inflight[i] &&
            (lc[i][32:30]==4 || lc[i][32:30]==5 || lc[i][32:30]==6) &&
            (lc[i][32:30]!=5 || reserve_up);
    end

    always @(posedge clk) begin
        if(reset) begin
            running<=0; finished<=0; failed<=0; reserve_up<=0;
            event_mask<=0; active<=0; inflight<=0;
            mpc<=0; pc[0]<=0; pc[1]<=0;
        end else if(!running) begin
            if(load) begin
                if(load_target==0 && load_address<8)
                    mother[load_address[2:0]]<=load_data;
                if((load_target==1 || load_target==2) && load_address<12)
                    local_code[load_target[0] ? 0 : 1][load_address]<=load_data;
            end else if(start) begin
                running<=1; finished<=0; failed<=0; reserve_up<=0;
                event_mask<=0; active<=0; inflight<=0; mpc<=0;
            end
        end else begin
            if(mpc>=8) begin failed<=1; running<=0; end
            else case(mc[32:30])
                0: if(active==0) begin
                    running<=0;
                    if(event_mask[3] && !reserve_up) finished<=1;
                    else failed<=1;
                end
                1: if(a>=2 || b>=3) begin failed<=1; running<=0; end
                   else if(!active[a[0]]) begin
                       active[a[0]]<=1; pc[a[0]]<={b[1:0],2'b00}; mpc<=mpc+1'b1;
                   end
                2: if(a>=4) begin failed<=1; running<=0; end
                   else if(event_mask[a[1:0]]) mpc<=mpc+1'b1;
                3: if(a!=0 || b!=33 || reserve_up) begin failed<=1; running<=0; end
                   else begin reserve_up<=1; mpc<=mpc+1'b1; end
                default: begin failed<=1; running<=0; end
            endcase
            for(integer i=0;i<2;i++) if(active[i]) begin
                if(inflight[i]) begin
                    if(service_done[i]) begin
                        inflight[i]<=0;
                        if(service_error[i] || pc[i][1:0]==3) begin failed<=1; running<=0; end
                        else begin
                            pc[i]<=pc[i]+1'b1;
                            case(lc[i][32:30])
                                4: event_mask[lc[i][1:0]]<=1;
                                5: begin event_mask[2]<=1; reserve_up<=0; end
                                6: event_mask[3]<=1;
                                default: begin failed<=1; running<=0; end
                            endcase
                        end
                    end
                end else if(lc[i][32:30]==0) active[i]<=0;
                else if(service_valid[i] && service_ready[i]) inflight[i]<=1;
                else if(!service_valid[i]) begin failed<=1; running<=0; end
            end
        end
    end
endmodule
