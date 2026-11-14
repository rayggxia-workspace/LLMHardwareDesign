"""Add a two-window ATT1 mode using one SRAM port and two response owners."""

import argparse
import difflib
import re
from pathlib import Path


def edit(path, replacements):
    before = path.read_text(encoding="utf-8")
    after = before
    for old, new in replacements:
        if after.count(old) != 1:
            raise ValueError(f"{path}: expected one occurrence of {old!r}")
        after = after.replace(old, new, 1)
    path.write_text(after, encoding="utf-8")
    return before, after


def core(path):
    mux = path.read_text().split("    always_comb begin\n        s_req_valid=", 1)[1].split("    wire dot_tag_ok=", 1)[0]
    legacy_mux = "    always_comb begin\n        s_req_valid=" + mux
    return [
        ("parameter bit OVERLAP_REFILL=1'b0", "parameter bit OVERLAP_REFILL=1'b0,\n"
         "    parameter bit HALF_TILE=1'b0, parameter bit OVERLAP_DOT=1'b0"),
        ("N_START,N_WAIT,V_REFILL,V_WAIT,RECOVER,REPORT", "N_START,N_WAIT,V_REFILL,V_WAIT,JOIN_TILE,RECOVER,REPORT"),
        ("    wire [15:0] remaining=count-first;", """    logic current_bank, next_started, next_done, next_failed, dot_failed;
    logic [31:0] expected_dot_tag;
    localparam logic [15:0] K_TILE = HALF_TILE ? 16'd4 : 16'd8;
    localparam logic [15:0] V_TILE = HALF_TILE ? 16'd64 : 16'd128;
    wire [15:0] remaining=count-first;
    wire [15:0] tile_advance=av ? V_TILE : K_TILE;
    wire [15:0] next_first=first+tile_advance;
    wire has_next=remaining>tile_advance;
    wire overlap_state=OVERLAP_DOT&&(state==DOT_WAIT||state==JOIN_TILE)&&has_next;
    wire start_next=overlap_state&&!next_started&&!(state==JOIN_TILE&&dot_failed);
    wire [15:0] refill_first=overlap_state ? next_first : first;
    wire [15:0] refill_remaining=count-refill_first;
    wire refill_bank=overlap_state ? !current_bank : current_bank;
    wire [9:0] refill_work=work_base+{2'd0,refill_bank,7'd0};
    wire [9:0] dot_work=work_base+{2'd0,current_bank,7'd0};
    initial assert((!HALF_TILE || (DDR_RESPONSE_QUEUE&&SELECT_V_BEAT)) && (!OVERLAP_DOT || HALF_TILE));"""),
        ("remaining>=8 ? 4'd8", "remaining>=K_TILE ? K_TILE[3:0]"),
        ("remaining>=128 ? 8'd128", "remaining>=V_TILE ? V_TILE[7:0]"),
        ("wire load_active=state==K_REFILL||state==K_WAIT||state==V_REFILL||state==V_WAIT;",
         """wire initial_load=state==K_REFILL||state==K_WAIT||state==V_REFILL||state==V_WAIT;
    wire load_launch=state==K_REFILL||state==V_REFILL||start_next;
    wire load_take_done=state==K_WAIT||state==V_WAIT||(overlap_state&&next_started&&!next_done);
    wire load_active=initial_load||(overlap_state&&next_started&&!next_done);"""),
        ("wire value_refill=state==V_REFILL||state==V_WAIT;", "wire value_refill=av;"),
        ("wire [15:0] v_position=first+filled;", """wire [15:0] v_position=refill_first+filled;
    wire [7:0] refill_length=refill_remaining>=V_TILE ? V_TILE[7:0] : refill_remaining[7:0];
    wire [3:0] refill_cols=refill_remaining>=K_TILE ? K_TILE[3:0] : refill_remaining[3:0];"""),
        ("k_base+{39'd0,first,9'd0};", "k_base+{39'd0,refill_first,9'd0};"),
        ("wire [9:0] refill_s_base=value_refill ? work_base+{filled[8:0],1'b0} : work_base;",
         "wire [9:0] refill_s_base=refill_work+(value_refill ? {filled[8:0],1'b0} : 10'd0);"),
        (".launch_valid(state==K_REFILL||state==V_REFILL),.launch_ready(load_ready),\n            .launch_base(refill_base),.launch_s_base(refill_s_base),\n            .launch_bursts(value_refill ? av_length : {1'b0,qk_columns,3'b0}),",
         ".launch_valid(load_launch),.launch_ready(load_ready),\n            .launch_base(refill_base),.launch_s_base(refill_s_base),\n            .launch_bursts(value_refill ? refill_length : {1'b0,refill_cols,3'b0}),"),
        (".done_ready(state==K_WAIT||state==V_WAIT),\n            .rd_valid,.rd_ready,.rd_address,.rd_rsp_valid,",
         ".done_ready(load_take_done),\n            .rd_valid,.rd_ready,.rd_address,.rd_rsp_valid,"),
        (".s_valid(load_s_valid),.s_ready(load_active&&s_req_ready),.s_address(load_s_address),\n            .s_data(load_s_data),.s_tag(load_s_tag),.s_rsp_valid(load_active&&s_rsp_valid),\n            .s_rsp_ready(load_s_take),.s_rsp_tag(s_rsp_error ? accepted_s_tag ^ 32'd1 : accepted_s_tag));\n    end else",
         ".s_valid(load_s_valid),.s_ready(load_request_ready),.s_address(load_s_address),\n"
         "            .s_data(load_s_data),.s_tag(load_s_tag),.s_rsp_valid(load_response_valid),\n"
         "            .s_rsp_ready(load_s_take),.s_rsp_tag(s_rsp_error ? accepted_s_tag ^ 32'd1 : accepted_s_tag));\n    end else"),
        (".REFILL_NEXT(1'b1),.CHECKPOINT(1'b1)", ".REFILL_NEXT(1'b1),.CHECKPOINT(1'b1),.AV_WORDS(HALF_TILE ? 128 : 256)"),
        (".cmd_kind(dot_begin ? 2'd0 : 2'd1),.cmd_key(service_done_owner),.cmd_tag(serial),",
         ".cmd_kind(dot_begin ? 2'd0 : 2'd1),.cmd_key(service_done_owner),.cmd_tag(serial),"),
        (".cmd_b_base(work_base)", ".cmd_b_base(dot_work)"),
        (".s_req_ready(dot_active&&s_req_ready),.s_req_write(dot_s_write)", ".s_req_ready(dot_request_ready),.s_req_write(dot_s_write)"),
        (".s_req_wdata(dot_s_data),.s_rsp_valid(dot_active&&s_rsp_valid)", ".s_req_wdata(dot_s_data),.s_rsp_valid(dot_response_valid)"),
        (legacy_mux, """    // The real S port returns its two accepted requests in order.
    logic owner[2], owner_head, owner_tail;
    logic [1:0] owner_count;
    logic hold_owner, held_load, prefer_load;
    wire owner_load=owner[owner_head];
    wire share_port=OVERLAP_DOT&&(load_active||dot_active);
    wire shared_rsp=s_rsp_valid&&owner_count!=0;
    wire load_response_valid=share_port ? shared_rsp&&owner_load : load_active&&s_rsp_valid;
    wire dot_response_valid=share_port ? shared_rsp&&!owner_load : dot_active&&s_rsp_valid;
    wire shared_take=share_port&&shared_rsp&&(owner_load ? load_s_take : dot_s_take);
    wire shared_credit=owner_count<2||shared_take;
    wire load_offer=load_active&&load_s_valid;
    wire dot_offer=dot_active&&dot_s_valid;
    wire select_load=hold_owner ? held_load : load_offer&&(!dot_offer||prefer_load);
    wire load_request_ready=share_port ? shared_credit&&select_load&&s_req_ready : load_active&&s_req_ready;
    wire dot_request_ready=share_port ? shared_credit&&!select_load&&s_req_ready : dot_active&&s_req_ready;
    wire shared_accept=share_port&&s_req_valid&&s_req_ready;
    wire accept_load=load_offer&&load_request_ready;

""" + legacy_mux.replace("        if(load_active) begin", """        if(share_port) begin
            s_req_valid=shared_credit&&(select_load ? load_offer : dot_offer);
            s_req_write=select_load||dot_s_write;
            s_req_address=select_load ? load_s_address : dot_s_address;
            s_req_data=select_load ? load_s_data : dot_s_data;
            s_rsp_ready=owner_count!=0&&(owner_load ? load_s_take : dot_s_take);
        end else if(load_active) begin""")),
        ("wire dot_tag_ok=dot_tag==serial", "wire dot_tag_ok=dot_tag==(OVERLAP_DOT ? expected_dot_tag : serial)"),
        ("    task automatic fault();", """    wire bad_tile=!dot_tag_ok||dot_kind!=1||dot_final!=final_chunk||
        dot_mask!=(final_chunk ? 2'b11 : 2'b00);

    task automatic fault();"""),
        ("            service_done_read_bytes<=0; service_done_write_bytes<=0;\n        end else begin",
         """            service_done_read_bytes<=0; service_done_write_bytes<=0;
            current_bank<=0; next_started<=0; next_done<=0; next_failed<=0; dot_failed<=0;
            expected_dot_tag<=0;
            owner_head<=0; owner_tail<=0; owner_count<=0; hold_owner<=0; held_load<=0; prefer_load<=0;
        end else begin
            if (share_port) begin
                case ({shared_accept,shared_take})
                    2'b10: owner_count<=owner_count+1'b1;
                    2'b01: owner_count<=owner_count-1'b1;
                    default: ;
                endcase
                if(shared_take) owner_head<=!owner_head;
                if(shared_accept) begin
                    owner[owner_tail]<=select_load;
                    owner_tail<=!owner_tail;
                    prefer_load<=!select_load;
                    hold_owner<=0;
                end else if(s_req_valid&&!s_req_ready) begin
                    hold_owner<=1;
                    held_load<=select_load;
                end
            end
            if((state==DOT_BEGIN||state==DOT_STEP)&&dot_ready) expected_dot_tag<=serial;
            if(start_next&&load_ready) next_started<=1;
            if(overlap_state&&next_started&&!next_done&&load_done) begin
                next_done<=1;
                next_failed<=load_error;
            end"""),
        ("if(load_s_valid&&load_active&&s_req_ready)", "if(accept_load)"),
        ("if(load_active&&s_rsp_valid&&load_s_take)", "if(load_response_valid&&load_s_take)"),
        ("if((state==K_REFILL||state==V_REFILL)&&load_ready) refill_serial<=serial;",
         "if(load_launch&&load_ready) refill_serial<=serial;"),
        ("                    state<=valid_descriptor ? K_REFILL : REPORT;",
         "                    current_bank<=0;\n                    state<=valid_descriptor ? K_REFILL : REPORT;"),
        ("                DOT_WAIT: if(dot_done) begin\n                    if(!dot_tag_ok||dot_kind!=1||dot_final!=final_chunk||dot_mask!=(final_chunk ? 2'b11 : 2'b00))",
         """                DOT_WAIT: if(dot_done) begin
                    if(OVERLAP_DOT&&has_next) begin
                        dot_failed<=bad_tile;
                        state<=JOIN_TILE;
                    end else if(bad_tile)"""),
        ("if(remaining<=8) state<=SCALE_READ;", "if(!has_next) state<=SCALE_READ;"),
        ("first<=first+8; state<=K_REFILL;", "first<=next_first; state<=K_REFILL;"),
        ("                SCALE_READ: if(s_req_ready)", """                JOIN_TILE: begin
                    if(dot_failed&&!next_started) fault();
                    else if(next_done) begin
                        next_started<=0; next_done<=0; next_failed<=0; dot_failed<=0;
                        if(dot_failed||next_failed) fault();
                        else begin
                            first<=next_first; current_bank<=!current_bank;
                            state<=av ? DOT_STEP : DOT_BEGIN;
                        end
                    end
                end
                SCALE_READ: if(s_req_ready)"""),
        ("group_index<=group_index+1'b1; first<=0; filled<=0; state<=DOT_BEGIN;",
         "group_index<=group_index+1'b1; first<=0; filled<=0; current_bank<=0; state<=DOT_BEGIN;"),
        ("else begin av<=1; first<=0; filled<=0; state<=DOT_BEGIN; end",
         "else begin av<=1; first<=0; filled<=0; current_bank<=0; state<=DOT_BEGIN; end"),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    rtl = "project/rtl/block_local_native"
    exp = "project/experiments/block_local_native"
    dot = "project/rtl/native_s32_dot/dot_s32_s128.sv"
    scope = f"{rtl}/s128_attention_core_scope.sv"
    runner = f"{exp}/run_native_attention_core_scope.sh"
    project_edits = {
        scope: core(args.root / scope),
        dot: [
            ("parameter bit CHECKPOINT=0", "parameter bit CHECKPOINT=0, parameter integer AV_WORDS=256"),
            ("(layout?13'd256:13'(int'(n)*32))", "(layout?13'(AV_WORDS):13'(int'(n)*32))"),
            ("cmd_chunk_k==0||cmd_chunk_k>128||", "cmd_chunk_k==0||cmd_chunk_k>128||"
             "(layout&&int'(cmd_chunk_k)*2>AV_WORDS)||"),
        ],
        f"{exp}/test_native_attention_core_scope.sv": [
            ("OVERLAP_REFILL=1'b0);", "OVERLAP_REFILL=1'b0, HALF_TILE=1'b0, OVERLAP_DOT=1'b0);"),
            (".OVERLAP_REFILL(OVERLAP_REFILL)) scope(",
             ".OVERLAP_REFILL(OVERLAP_REFILL),.HALF_TILE(HALF_TILE),.OVERLAP_DOT(OVERLAP_DOT)) scope("),
            ("    int unsigned requests,acks,calls,retired;",
             "    int unsigned requests,acks,calls,retired;\n"
             "    int unsigned shared_cycles, shared_load_wait, shared_dot_wait;"),
            ("descriptor_reads<=0;descriptor_callbacks<=0;requests<=0;",
             "descriptor_reads<=0;descriptor_callbacks<=0;shared_cycles<=0;shared_load_wait<=0;shared_dot_wait<=0;requests<=0;"),
            ("            if(engine_req && engine_ready) begin",
             "            if(OVERLAP_DOT && scope.load_active && scope.dot_active) begin\n"
             "                shared_cycles<=shared_cycles+1;\n"
             "                if(scope.load_s_valid&&!scope.load_request_ready) shared_load_wait<=shared_load_wait+1;\n"
             "                if(scope.dot_s_valid&&!scope.dot_request_ready) shared_dot_wait<=shared_dot_wait+1;\n"
             "            end\n"
             "            if(engine_req && engine_ready) begin"),
            ('        $display("DDR bridge peak', '        if(OVERLAP_DOT) assert(shared_cycles!=0);\n'
             '        $display("S overlap cycles=%0d load_wait=%0d dot_wait=%0d",shared_cycles,shared_load_wait,shared_dot_wait);\n'
             '        $display("DDR bridge peak'),
        ],
        runner: [
            ('OVERLAP_REFILL=${OVERLAP_REFILL:-0}"',
             'OVERLAP_REFILL=${OVERLAP_REFILL:-0},HALF_TILE=${HALF_TILE:-0},OVERLAP_DOT=${OVERLAP_DOT:-0}"'),
            ('${OVERLAP_REFILL:-0}" \\\n',
             '${OVERLAP_REFILL:-0}" "-GHALF_TILE=1\'b${HALF_TILE:-0}" "-GOVERLAP_DOT=1\'b${OVERLAP_DOT:-0}" \\\n'),
        ],
    }
    patch = []
    for name, replacements in project_edits.items():
        before, after = edit(args.root / name, replacements)
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                          fromfile=f"a/{name}", tofile=f"b/{name}"))
    args.patch.write_text("".join(patch), encoding="utf-8")


if __name__ == "__main__":
    main()

