"""Apply the ATT1 selected-beat experiment to isolated PR #260 source copies."""

import argparse
import difflib
from pathlib import Path


def change(source, replacements):
    before = source.read_text(encoding="utf-8")
    after = before
    for old, new in replacements:
        if after.count(old) != 1:
            raise ValueError(f"{source}: expected one occurrence of {old!r}")
        after = after.replace(old, new, 1)
    source.write_text(after, encoding="utf-8")
    return before, after


def rtl():
    module = "project/rtl/block_local_native"
    test = "project/experiments/block_local_native"
    loader = f"{module}/s128_ddr_range_load.sv"
    return {
        loader: [
            ("parameter bit PIPELINE_WRITES = 1'b0", "parameter bit PIPELINE_WRITES = 1'b0,\n    parameter bit STRIDED_PAIR = 1'b0"),
            ("    wire [9:0] ack_address = s_base + (pair ? {9'd0, acknowledged[0]} : {burst, acknowledged[1:0]});",
             "    wire [9:0] pair_offset = STRIDED_PAIR ? {1'b0, burst, 1'b0} : 10'd0;\n"
             "    wire [9:0] ack_address = s_base + (pair ? pair_offset + {9'd0, acknowledged[0]} :\n"
             "                                               {burst, acknowledged[1:0]});"),
            ("    wire [11:0] launch_words = launch_pair ? 12'd2 : {2'b0, launch_bursts, 2'b0};\n"
             "    wire [64:0] launch_end = {1'b0, launch_base} + {51'd0, launch_bursts, 6'd0};",
             "    wire strided_launch = STRIDED_PAIR && launch_pair;\n"
             "    wire [11:0] launch_words = launch_pair ? (STRIDED_PAIR ? {3'b0, launch_bursts, 1'b0} : 12'd2) :\n"
             "                                                {2'b0, launch_bursts, 2'b0};\n"
             "    wire [7:0] last_launch_burst = launch_bursts - 8'd1;\n"
             "    wire [64:0] launch_span = (strided_launch ? {48'd0, last_launch_burst, 9'd0} :\n"
             "                                             {51'd0, last_launch_burst, 6'd0}) + 65'd64;\n"
             "    wire [64:0] launch_end = {1'b0, launch_base} + launch_span;"),
            ("(!launch_pair || launch_bursts == 2)", "(!launch_pair || STRIDED_PAIR || launch_bursts == 2)"),
            ("!pair || burst[0] == pair_beat", "!pair || STRIDED_PAIR || burst[0] == pair_beat"),
            ("assign rd_address = base + {50'd0, burst, 6'd0};", "assign rd_address = base + (STRIDED_PAIR && pair ?\n                                                {47'd0, burst, 9'd0} : {50'd0, burst, 6'd0});"),
            ("pair ? {9'd0, write_word[0]} : {burst, write_word}", "pair ? pair_offset + {9'd0, write_word[0]} : {burst, write_word}"),
        ],
        f"{module}/s128_attention_core_scope.sv": [
            ("parameter bit PIPELINE_KV_WRITES=1'b0", "parameter bit PIPELINE_KV_WRITES=1'b0,\n    parameter bit SELECT_V_BEAT=1'b0"),
            ("v_base+{39'd0,v_position,9'd0}+{55'd0,group_index[3:2],7'd0} : k_base+{39'd0,first,9'd0};",
             "v_base+{39'd0,v_position,9'd0}+{55'd0,group_index[3:2],7'd0}+\n"
             "        (SELECT_V_BEAT && group_index[1] ? 64'd64 : 64'd0) : k_base+{39'd0,first,9'd0};"),
            ("s128_ddr_range_load #(.PIPELINE_WRITES(PIPELINE_KV_WRITES)) load_span(",
             "s128_ddr_range_load #(.PIPELINE_WRITES(PIPELINE_KV_WRITES),.STRIDED_PAIR(SELECT_V_BEAT)) load_span("),
            ("value_refill ? 8'd2 : {1'b0,qk_columns,3'b0}", "value_refill ? (SELECT_V_BEAT ? av_length : 8'd2) : {1'b0,qk_columns,3'b0}"),
            ("service_done_read_bytes!=32'(count)*2560", "service_done_read_bytes!=32'(count)*(SELECT_V_BEAT ? 1536 : 2560)"),
            ("else if(filled+16'd1=={8'd0,av_length})", "else if(SELECT_V_BEAT||filled+16'd1=={8'd0,av_length})"),
        ],
        f"{test}/test_native_attention_core_scope.sv": [
            ("parameter int MOTHER_WORDS=15, CONTEXT=380", "parameter int MOTHER_WORDS=15, CONTEXT=380, parameter bit SELECT_V_BEAT=1'b0"),
            ("localparam int DATA_READS=CONTEXT*40;", "localparam int BEATS_PER_V_ROW=SELECT_V_BEAT ? 1 : 2;\n    localparam int DATA_READS=CONTEXT*(8+16*BEATS_PER_V_ROW);"),
            (".PIPELINE_KV_WRITES(1)) scope(", ".PIPELINE_KV_WRITES(1),.SELECT_V_BEAT(SELECT_V_BEAT)) scope("),
            ("group=index/(2*CONTEXT);\n                    in_group=index%(2*CONTEXT);\n                    assert(kv_address==value_base+64'(in_group/2)*512+\n                           64'(group/4)*128+64'(in_group%2)*64);",
             "group=index/(BEATS_PER_V_ROW*CONTEXT);\n"
             "                    in_group=index%(BEATS_PER_V_ROW*CONTEXT);\n"
             "                    assert(kv_address==value_base+64'(in_group/BEATS_PER_V_ROW)*512+\n"
             "                           64'(group/4)*128+(SELECT_V_BEAT ? {63'd0,group[1]} : {63'd0,in_group[0]})*64);"),
        ],
        f"{test}/run_native_attention_core_scope.sh": [
            ("SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK\"", "SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,SELECT_V_BEAT=${SELECT_V_BEAT:-0}\""),
            ('-GMOTHER_WORDS="$mother_words" -GCONTEXT="$context"', '-GMOTHER_WORDS="$mother_words" -GCONTEXT="$context" \\\n "-GSELECT_V_BEAT=1\'b${SELECT_V_BEAT:-0}"'),
        ],
    }


def tlm():
    return {
        "native_tlm_attention.py": [
            ("row, beat = divmod(i, 2)", "row, beat = i, pick//2"),
            ("prefetch(2*n, plan, tile_ready if refill_only else loaded)",
             "prefetch(n, plan, tile_ready if refill_only else loaded)"),
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("rtl", "tlm"))
    parser.add_argument("root", type=Path)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    files = (rtl if args.mode == "rtl" else tlm)()
    patch = []
    for name, replacements in files.items():
        before, after = change(args.root / name, replacements)
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                          fromfile=f"a/{name}", tofile=f"b/{name}"))
    args.patch.write_text("".join(patch), encoding="utf-8")


if __name__ == "__main__":
    main()

