"""Connect the bounded return queue to the selected-V native ATT1 fixture."""

import argparse
import difflib
from pathlib import Path

from prepare_att1_selected import change


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    rtl = "project/rtl/block_local_native"
    bench = "project/experiments/block_local_native"
    core = (args.root / rtl / "s128_attention_core_scope.sv").read_text(encoding="utf-8")
    begin = core.index("    s128_ddr_range_load #")
    end = core.index("    assign rd_rsp_ready", begin)
    legacy = core[begin:end]
    queued = """    if (DDR_RESPONSE_QUEUE) begin : response_queue
        wire [31:0] local_return = response_serial - refill_serial;
        assign load_rd_tag = 0;
        s128_ddr_response_load load_span(
            .clk,.reset(datapath_reset),.launch_valid(state==K_REFILL||state==V_REFILL),.launch_ready(load_ready),
            .launch_base(refill_base),.launch_s_base(refill_s_base),
            .launch_bursts(value_refill ? av_length : {1'b0,qk_columns,3'b0}),
            .launch_pair(value_refill),.launch_pair_high(group_index[0]),
            .done_valid(load_done),.done_error(load_error),.done_ready(state==K_WAIT||state==V_WAIT),
            .rd_valid,.rd_ready,.rd_address,.rd_rsp_valid,.rd_rsp_ready(load_rd_take),
            .rd_rsp_tag({!good_rd,31'd0,local_return}),.rd_rsp_data,
            .s_valid(load_s_valid),.s_ready(load_active&&s_req_ready),.s_address(load_s_address),
            .s_data(load_s_data),.s_tag(load_s_tag),.s_rsp_valid(load_active&&s_rsp_valid),
            .s_rsp_ready(load_s_take),.s_rsp_tag(s_rsp_error ? accepted_s_tag ^ 32'd1 : accepted_s_tag));
    end else begin : serialized_loader
""" + "".join("    " + line for line in legacy.splitlines(True)) + "    end\n"
    updates = {
        f"{rtl}/s128_attention_core_scope.sv": [
            ("parameter bit SELECT_V_BEAT=1'b0", "parameter bit SELECT_V_BEAT=1'b0,\n    parameter bit DDR_RESPONSE_QUEUE=1'b0"),
            ("    wire good_rd=rd_rsp_tag==accepted_rd_tag&&!rd_rsp_error;",
             "    logic [31:0] response_serial,refill_serial;\n"
             "    wire _unused_loader_tags = ^{accepted_load_tag,refill_serial};\n"
             "    wire [63:0] expected_rd_tag = DDR_RESPONSE_QUEUE ? {service_done_ticket,response_serial} : accepted_rd_tag;\n"
             "    wire good_rd=rd_rsp_tag==expected_rd_tag&&!rd_rsp_error;\n"
             "    initial assert(!DDR_RESPONSE_QUEUE || (SELECT_V_BEAT && PIPELINE_KV_WRITES));"),
            (legacy, queued),
            ("            accepted_rd_tag<=0; accepted_load_tag<=0;", "            accepted_rd_tag<=0; accepted_load_tag<=0; response_serial<=0; refill_serial<=0;"),
            ("            if(rd_rsp_valid&&rd_rsp_ready&&good_rd) service_done_read_bytes<=service_done_read_bytes+64;",
             "            if((state==K_REFILL||state==V_REFILL)&&load_ready) refill_serial<=serial;\n"
             "            if(rd_rsp_valid&&rd_rsp_ready) begin\n"
             "                response_serial<=response_serial+1'b1;\n"
             "                if(good_rd) service_done_read_bytes<=service_done_read_bytes+64;\n"
             "            end"),
            ("score_word<=0; serial<=0;", "score_word<=0; serial<=0; response_serial<=0;"),
        ],
        f"{bench}/test_native_attention_core_scope.sv": [
            ("parameter bit SELECT_V_BEAT=1'b0", "parameter bit SELECT_V_BEAT=1'b0, DDR_RESPONSE_QUEUE=1'b0"),
            ("    logic pending,ddr_rsp,pending_data;", """    localparam int BRIDGE_DEPTH=DDR_RESPONSE_QUEUE ? 8 : 1;
    logic ddr_rsp;
    logic [63:0] return_tags[8];
    logic [511:0] return_data[8];
    logic return_is_kv[8];
    logic [2:0] take_ptr,put_ptr;
    logic [3:0] outstanding,peak_outstanding;
    wire pending_data=return_is_kv[take_ptr];
    wire enqueue_desc=dr_valid[0]&&dr_ready[0];
    wire enqueue_kv=kv_valid&&kv_ready;
    wire pop_ddr=ddr_rsp&&(pending_data ? kv_take : dr_rsp_ready[0]);"""),
            ("    logic [63:0] base,ret_tag;\n    logic [511:0] ret_data;",
             "    logic [63:0] base;\n    wire [63:0] ret_tag=return_tags[take_ptr];\n"
             "    wire [511:0] ret_data=return_data[take_ptr];"),
            ("assign drained=!pending;", "assign drained=outstanding==0;"),
            ("!reset && !pending &&", "!reset && outstanding<4'(BRIDGE_DEPTH) &&"),
            ("!reset && pending && completed[0]", "!reset && outstanding!=0 && completed[0]"),
            (".SELECT_V_BEAT(SELECT_V_BEAT)) scope(",
             ".SELECT_V_BEAT(SELECT_V_BEAT),.DDR_RESPONSE_QUEUE(DDR_RESPONSE_QUEUE)) scope("),
            ("            pending<=0;pending_data<=0;kv_requests<=0;kv_callbacks<=0;completed<=0;ret_tag<=0;ret_data<=0;cycle<=0;",
             "            take_ptr<=0;put_ptr<=0;outstanding<=0;peak_outstanding<=0;\n"
             "            kv_requests<=0;kv_callbacks<=0;completed<=0;cycle<=0;"),
            ("                ret_tag<={32'd0,dr_tag[31:0]};ret_data<=payload;pending<=1;pending_data<=0;",
             "                return_tags[put_ptr]<={32'd0,dr_tag[31:0]};\n"
             "                return_data[put_ptr]<=payload;return_is_kv[put_ptr]<=0;"),
            ("                ret_tag<=kv_tag;ret_data<=payload;pending<=1;pending_data<=1;",
             "                return_tags[put_ptr]<=kv_tag;return_data[put_ptr]<=payload;return_is_kv[put_ptr]<=1;"),
            ("            if(ddr_rsp && (pending_data ? kv_take : dr_rsp_ready[0])) begin\n"
             "                ddr_read_retire(0,ret_tag);\n                pending<=0;",
             """            if(enqueue_desc||enqueue_kv) put_ptr<=put_ptr+1'b1;
            case ({enqueue_desc||enqueue_kv,pop_ddr})
                2'b10: begin
                    outstanding<=outstanding+1'b1;
                    if(outstanding>=peak_outstanding) peak_outstanding<=outstanding+1'b1;
                end
                2'b01: outstanding<=outstanding-1'b1;
                default: ;
            endcase
            if(pop_ddr) begin
                ddr_read_retire(0,ret_tag);
                take_ptr<=take_ptr+1'b1;
                // The registered completion describes the just-retired front.
                completed<=0;"""),
            ('        $display("PASS typed AttentionCore',
             '        if(DDR_RESPONSE_QUEUE) assert(peak_outstanding==8);\n'
             '        $display("DDR bridge peak outstanding=%0d",peak_outstanding);\n'
             '        $display("PASS typed AttentionCore'),
        ],
        f"{bench}/run_native_attention_core_scope.sh": [
            ("SELECT_V_BEAT=${SELECT_V_BEAT:-0}\"", "SELECT_V_BEAT=${SELECT_V_BEAT:-0},DDR_RESPONSE_QUEUE=${DDR_RESPONSE_QUEUE:-0}\""),
            ("${SELECT_V_BEAT:-0}\" \\\n", "${SELECT_V_BEAT:-0}\" \"-GDDR_RESPONSE_QUEUE=1'b${DDR_RESPONSE_QUEUE:-0}\" \\\n"),
            ("s128_attention_core_scope,s128_ddr_range_load}", "s128_attention_core_scope,s128_ddr_range_load,s128_ddr_response_load}"),
        ],
    }
    patch = []
    for name, replacements in updates.items():
        before, after = change(args.root / name, replacements)
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                          fromfile=f"a/{name}", tofile=f"b/{name}"))
    args.patch.write_text("".join(patch), encoding="utf-8")


if __name__ == "__main__":
    main()

