// Resident U service. Private-S ownership lasts through the final write response.
module u_indexed_gather (
    input  wire clk, reset,
    input  wire svc_valid,
    output wire svc_ready,
    input  wire [1023:0] descriptor,
    output wire rsp_valid,
    input  wire rsp_ready,
    output reg  [15:0] status,
    output reg  [31:0] read_bytes, write_bytes,

    output wire dma_req_valid,
    input  wire dma_req_ready,
    output wire [63:0] dma_req_address,
    output wire [31:0] dma_req_tag,
    output wire dma_req_channel,
    output wire [4:0] dma_req_record_beats,
    input  wire dma_rsp_valid,
    output wire dma_rsp_ready,
    input  wire [31:0] dma_rsp_tag,
    input  wire [511:0] dma_rsp_data,

    output wire s_req_valid, s_req_write,
    input  wire s_req_ready,
    output wire [9:0] s_req_address,
    output wire [127:0] s_req_data,
    input  wire s_rsp_valid,
    output wire s_rsp_ready,
    input  wire [127:0] s_rsp_data
);
    localparam [2:0] IDLE=0, INDEX=1, INDEX_ACK=2, ISSUE=3, RETURN=4,
                     WRITE=5, WRITE_ACK=6, DONE=7;
    reg [2:0] state;
    reg [9:0] index_word, output_word;
    reg [1:0] index_lane;
    reg [31:0] table_rows;
    reg [47:0] table_base, row_address, prompt_record;
    reg [4:0] prompt_lane;
    reg read_prompt;
    reg [5:0] record_number;
    reg [2:0] word_number;
    reg issue_beat;
    reg [1:0] outstanding, received;
    reg [511:0] return_low, return_high;
    reg bad_response;

    // native0/1 encode the 48-bit table address and 16-bit byte index offset.
    // native2 is the table row count. native3 is the result's SRAM word.
    wire [47:0] d_table = descriptor[512+:48];
    wire [15:0] d_index = descriptor[560+:16];
    wire [31:0] d_rows = descriptor[576+:32];
    wire [31:0] d_output = descriptor[608+:32];
    wire [48:0] table_end = {1'b0,d_table} + {4'b0,d_rows,13'b0};
    wire [47:0] d_prompt_address = descriptor[640+:48];
    wire d_read_prompt = descriptor[688];
    wire valid_descriptor = descriptor[1023:689]==0 &&
        (d_read_prompt ? d_prompt_address[1:0]==0 : d_prompt_address==0) &&
        d_table[6:0]==0 &&
        d_index[1:0]==0 && d_index<16384 && d_rows!=0 &&
        (d_output==0 || d_output==512) && d_index[13]!=d_output[9] &&
        table_end<=49'h1_0000_0000_0000;
    wire [31:0] input_index = read_prompt ?
        (prompt_lane[4] ? return_high[32*prompt_lane[3:0]+:32] :
                          return_low[32*prompt_lane[3:0]+:32]) :
        s_rsp_data[32*index_lane+:32];
    wire [32:0] normalized = {input_index[31],input_index} +
        (input_index[31] ? {1'b0,table_rows} : 33'd0);
    // Clients 3-8 admit two consecutive, aligned 64 B beats per record.
    // Reserve a distinct record tag for the prompt lookup.
    wire [47:0] record_address = read_prompt ? prompt_record :
        row_address + {35'b0,record_number,7'b0};
    wire [31:0] tag_base = {24'b0,read_prompt,record_number,1'b0};
    wire req_fire = dma_req_valid && dma_req_ready;
    wire rsp_fire = dma_rsp_valid && dma_rsp_ready;
    wire [1:0] offer = req_fire ? (issue_beat ? 2'b10 : 2'b01) : 2'b00;
    wire [1:0] return_mask = dma_rsp_tag[0] ? 2'b10 : 2'b01;
    wire valid_return = dma_rsp_tag[31:1]==tag_base[31:1] &&
        ((outstanding|offer) & return_mask)!=0;
    wire [1:0] retire = rsp_fire && valid_return ? return_mask : 2'b00;
    wire [1:0] next_outstanding = (outstanding|offer) & ~retire;

    assign svc_ready = !reset && state==IDLE;
    assign rsp_valid = !reset && state==DONE;
    assign dma_req_valid = !reset && state==ISSUE;
    assign dma_req_address = {16'b0,record_address} + {57'b0,issue_beat,6'b0};
    assign dma_req_tag = tag_base | {31'b0,issue_beat};
    assign dma_req_channel = record_address[11];
    assign dma_req_record_beats = 5'd2;
    // The second return may arrive first. Match both tags before publishing.
    assign dma_rsp_ready = !reset && (state==ISSUE || state==RETURN);
    assign s_req_valid = !reset && (state==INDEX || state==WRITE);
    assign s_req_write = state==WRITE;
    assign s_req_address = state==INDEX ? index_word :
        output_word + {1'b0,record_number,word_number};
    assign s_req_data = word_number[2] ? return_high[word_number[1:0]*128+:128] :
                                           return_low[word_number[1:0]*128+:128];
    assign s_rsp_ready = !reset && (state==INDEX_ACK || state==WRITE_ACK);

    always @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            status<=0; read_bytes<=0; write_bytes<=0;
            index_word<=0; output_word<=0; index_lane<=0;
            table_base<=0; table_rows<=0; row_address<=0;
            prompt_record<=0; prompt_lane<=0; read_prompt<=0;
            record_number<=0; word_number<=0; issue_beat<=0;
            outstanding<=0; received<=0; bad_response<=0;
        end else begin
            outstanding<=next_outstanding;
            if (rsp_fire) begin
                if (!valid_return) bad_response<=1;
                else begin
                    received<=received | return_mask;
                    read_bytes<=read_bytes+64;
                    if (dma_rsp_tag[0]) return_high<=dma_rsp_data;
                    else return_low<=dma_rsp_data;
                end
            end
            case (state)
                IDLE: if (svc_valid) begin
                    status<=valid_descriptor ? 0 : 16'h0220;
                    read_bytes<=0; write_bytes<=0;
                    received<=0; bad_response<=0;
                    record_number<=0; word_number<=0; issue_beat<=0;
                    index_word<=d_index[13:4]; index_lane<=d_index[3:2];
                    output_word<=d_output[9:0]; table_rows<=d_rows; table_base<=d_table;
                    prompt_record<={d_prompt_address[47:7],7'b0};
                    prompt_lane<=d_prompt_address[6:2]; read_prompt<=d_read_prompt;
                    state<=!valid_descriptor ? DONE : d_read_prompt ? ISSUE : INDEX;
                end
                INDEX: if (s_req_ready) state<=INDEX_ACK;
                INDEX_ACK: if (s_rsp_valid) begin
                    read_bytes<=16;
                    if (normalized>={1'b0,table_rows}) begin
                        status<=16'h0222;
                        state<=DONE;
                    end else begin
                        row_address<=table_base + {3'b0,normalized[31:0],13'b0};
                        state<=ISSUE;
                    end
                end
                ISSUE: if (req_fire) begin
                    if (issue_beat) state<=RETURN;
                    else issue_beat<=1;
                end
                RETURN: if (outstanding==0 && received==2'b11) begin
                    if (bad_response || rsp_fire) begin
                        status<=16'h0222;
                        state<=DONE;
                    end else if (read_prompt) begin
                        if (normalized>={1'b0,table_rows}) begin
                            status<=16'h0222;
                            state<=DONE;
                        end else begin
                            read_prompt<=0;
                            row_address<=table_base + {3'b0,normalized[31:0],13'b0};
                            issue_beat<=0;
                            received<=0;
                            state<=ISSUE;
                        end
                    end else state<=WRITE;
                end
                WRITE: if (s_req_ready) state<=WRITE_ACK;
                WRITE_ACK: if (s_rsp_valid) begin
                    write_bytes<=write_bytes+16;
                    if (word_number!=7) begin
                        word_number<=word_number+1'b1;
                        state<=WRITE;
                    end else if (record_number==63) state<=DONE;
                    else begin
                        record_number<=record_number+1'b1;
                        word_number<=0; issue_beat<=0; received<=0;
                        state<=ISSUE;
                    end
                end
                DONE: if (rsp_ready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end
endmodule
