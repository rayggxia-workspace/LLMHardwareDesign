// Isolated Issue247 experiment. One unchanged production N and one E are driven
// by this controller. An error stops issue; recovery requires whole-group reset.
module u_overlap_fifo #(parameter integer DEPTH=2, WIDTH=136) (
    input wire clk, reset,
    input wire src_valid, output wire src_ready,
    input wire [WIDTH-1:0] src_data,
    output wire dst_valid, input wire dst_ready,
    output wire [WIDTH-1:0] dst_data,
    output reg [7:0] count
);
    localparam integer PW=DEPTH>1 ? $clog2(DEPTH) : 1;
    localparam [7:0] LIMIT=8'(DEPTH);
    reg [WIDTH-1:0] entries [0:DEPTH-1];
    reg [PW-1:0] rd_ptr, wr_ptr;
    wire push=src_valid && src_ready, pop=dst_valid && dst_ready;
    // No sink-ready to source-ready path. A full FIFO has one recovery bubble.
    assign src_ready=!reset && count<LIMIT;
    assign dst_valid=!reset && count!=0;
    assign dst_data=entries[rd_ptr];
    always @(posedge clk) begin
        if(reset) begin count<=0;rd_ptr<=0;wr_ptr<=0;end
        else begin
            case({push,pop})
                2'b10:count<=count+1'b1;
                2'b01:count<=count-1'b1;
                default:count<=count;
            endcase
            if(push) begin
                entries[wr_ptr]<=src_data;
                wr_ptr<=wr_ptr==PW'(DEPTH-1) ? '0 : wr_ptr+1'b1;
            end
            if(pop) rd_ptr<=rd_ptr==PW'(DEPTH-1) ? '0 : rd_ptr+1'b1;
        end
    end
endmodule

module u_overlap_control #(parameter integer DEPTH=2) (
    input wire clk, reset, start_valid,
    output wire start_ready,
    input wire [7:0] tile_count, handoff_delay,
    input wire consumer_enable,
    output wire stream_done,
    input wire stream_take,
    output reg fault,
    output wire [1:0] cmd_valid, cmd_store, done_ready,
    output wire [127:0] cmd_meta,
    output wire [3:0] cmd_sources,
    output wire [59:0] cmd_addresses,
    output wire [19:0] cmd_dst,
    input wire [1:0] cmd_ready, done_valid, done_error,
    input wire n_result_valid, output wire n_result_ready,
    input wire [127:0] n_result_data,
    output wire e_a_valid, input wire e_a_ready,
    output wire [127:0] e_a_data,
    output wire [7:0] fifo_count,
    output reg [7:0] n_issued, n_retired, e_issued, e_retired,
    output reg [7:0] pushes, pops, max_inflight
);
    reg running,n_pending,n_enqueued,e_taken;
    reg [7:0] target,delay_cfg,n_tag,e_tag,delay_left;
    // E_IDLE -> E_ISSUE keeps an offered command stable until accepted.
    localparam [1:0] E_IDLE=0,E_ISSUE=1,E_WAIT=2;
    reg [1:0] e_state;
    wire fifo_in_ready,fifo_valid,fifo_take;
    wire [135:0] fifo_data;
    wire push=!reset && running && !fault && n_pending && !n_enqueued && n_result_valid && fifo_in_ready;
    wire pop=e_a_valid && e_a_ready;
    wire [7:0] inflight=n_issued-e_retired;
    u_overlap_fifo #(.DEPTH(DEPTH),.WIDTH(136)) result_fifo (
        .clk,.reset,
        .src_valid(running && !fault && n_pending && !n_enqueued && n_result_valid),
        .src_ready(fifo_in_ready),.src_data({n_tag,n_result_data}),
        .dst_valid(fifo_valid),.dst_ready(fifo_take),.dst_data(fifo_data),.count(fifo_count)
    );
    assign start_ready=!reset && !running && !fault;
    assign stream_done=running && !fault && n_retired==target && e_retired==target &&
                       !n_pending && e_state==E_IDLE && !fifo_valid;
    assign cmd_valid={!reset && running && !fault && !n_pending && n_issued<target,
                      !reset && running && !fault && e_state==E_ISSUE};
    assign cmd_store=2'b01; // N intermediate never stored; E final result stored.
    assign cmd_meta={24'b0,40'h85,64'b0}; // RMS replay -> signed16 ADD shift0.
    assign cmd_sources={2'd2,2'd2};
    assign cmd_addresses={10'b0,10'd20,10'd20,10'b0,(10'd128+{2'b0,e_tag}),10'b0};
    assign cmd_dst={10'b0,(10'd64+{2'b0,e_tag})};
    // N may retire only after FIFO owns its data. Next N can then be issued.
    assign n_result_ready=!reset && running && !fault && n_pending && !n_enqueued && fifo_in_ready;
    assign done_ready={!reset && running && n_pending && (n_enqueued || done_error[1]),
                       !reset && running && e_state==E_WAIT && (e_taken || done_error[0])};
    assign e_a_valid=!reset && running && !fault && e_state==E_WAIT && !e_taken &&
                     fifo_valid && fifo_data[135:128]==e_tag && delay_left==0;
    assign e_a_data=fifo_data[127:0];
    assign fifo_take=e_a_valid && e_a_ready;
    always @(posedge clk) begin
        if(reset) begin
            running<=0;fault<=0;n_pending<=0;n_enqueued<=0;e_taken<=0;e_state<=E_IDLE;
            target<=0;delay_cfg<=0;n_tag<=0;e_tag<=0;delay_left<=0;
            n_issued<=0;n_retired<=0;e_issued<=0;e_retired<=0;
            pushes<=0;pops<=0;max_inflight<=0;
        end else begin
            if(start_valid && start_ready) begin
                running<=1;target<=tile_count;delay_cfg<=handoff_delay;
                n_issued<=0;n_retired<=0;e_issued<=0;e_retired<=0;
                pushes<=0;pops<=0;max_inflight<=0;
            end
            if(inflight>max_inflight) max_inflight<=inflight;
            if(cmd_valid[1] && cmd_ready[1]) begin
                n_pending<=1;n_enqueued<=0;n_tag<=n_issued;n_issued<=n_issued+1'b1;
            end
            if(push) begin n_enqueued<=1;pushes<=pushes+1'b1;end
            if(done_valid[1] && done_ready[1]) begin
                n_pending<=0;n_enqueued<=0;n_retired<=n_retired+1'b1;
                if(done_error[1]) fault<=1;
            end
            if(running && !fault && e_state==E_IDLE && fifo_valid && consumer_enable) begin
                e_tag<=fifo_data[135:128];e_state<=E_ISSUE;
            end
            if(cmd_valid[0] && cmd_ready[0]) begin
                e_state<=E_WAIT;e_taken<=0;delay_left<=delay_cfg;e_issued<=e_issued+1'b1;
            end
            if(e_state==E_WAIT && !e_taken && e_a_ready && delay_left!=0)
                delay_left<=delay_left-1'b1;
            if(pop) begin e_taken<=1;pops<=pops+1'b1;end
            // Production E done follows its S write response; never free on A pop.
            if(done_valid[0] && done_ready[0]) begin
                e_state<=E_IDLE;e_taken<=0;e_retired<=e_retired+1'b1;
                if(done_error[0]) fault<=1;
            end
            if(stream_done && stream_take) running<=0;
        end
    end
endmodule
