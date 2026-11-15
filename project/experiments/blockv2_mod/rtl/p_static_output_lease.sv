`timescale 1ns/1ps
// Keep a committed ordinary P projection window reserved until its consumer
// has accepted the tile metadata and acknowledged all SRAM reads.
module p_static_output_lease (
    input logic clk, reset,
    output logic launch_ready,
    input logic launch_valid,
    input logic [127:0] launch_owner,
    input logic [31:0] launch_first, launch_version,
    input logic [7:0] launch_count,
    input logic [9:0] launch_s_base,
    input logic commit_valid,
    input logic [127:0] commit_owner,
    input logic [15:0] commit_status,
    output logic tile_valid,
    input logic tile_ready,
    output logic [127:0] tile_owner,
    output logic [31:0] tile_first, tile_tag,
    output logic [7:0] tile_count,
    output logic [9:0] tile_s_base,
    input logic release_valid,
    output logic release_ready,
    input logic [127:0] release_owner,
    input logic [31:0] release_first,
    output logic fault
);
    typedef enum logic [2:0] {IDLE, P_LIVE, OFFER, CONSUMER_LIVE, FAULT} state_t;
    state_t state;
    wire [10:0] s_end={1'b0,launch_s_base}+({3'd0,launch_count}>>2);
    wire launch_shape_ok=launch_count!=0 && launch_count<=8'd128 &&
                         launch_count[2:0]==0 && launch_first[2:0]==0 && s_end<=1024;
    wire release_match=release_owner==tile_owner && release_first==tile_first;
    assign launch_ready=!reset && state==IDLE;
    assign tile_valid=!reset && state==OFFER;
    assign release_ready=!reset && state==CONSUMER_LIVE && release_match;
    assign fault=!reset && state==FAULT;

    always_ff @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            tile_owner<=0;
            tile_first<=0;
            tile_tag<=0;
            tile_count<=0;
            tile_s_base<=0;
        end else if (commit_valid && (state!=P_LIVE || commit_owner!=tile_owner)) begin
            state<=FAULT;
        end else if (release_valid && !release_ready) begin
            state<=FAULT;
        end else begin
            case (state)
                IDLE: if (launch_valid && launch_ready) begin
                    tile_owner<=launch_owner;
                    tile_first<=launch_first;
                    tile_tag<=launch_version;
                    tile_count<=launch_count;
                    tile_s_base<=launch_s_base;
                    state<=launch_shape_ok ? P_LIVE : FAULT;
                end
                P_LIVE: if (commit_valid) state<=commit_status==0 ? OFFER : IDLE;
                OFFER: if (tile_valid && tile_ready) state<=CONSUMER_LIVE;
                CONSUMER_LIVE: if (release_valid && release_ready) state<=IDLE;
                FAULT: state<=FAULT;
                default: state<=FAULT;
            endcase
        end
    end
endmodule
