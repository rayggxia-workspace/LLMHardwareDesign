"""Allow the next valid return slot to offer S128 writes before the previous slot retires."""

import argparse
import difflib
from pathlib import Path

from prepare_att1_selected import change


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    module = "project/rtl/block_local_native"
    exp = "project/experiments/block_local_native"
    edits = {
        f"{module}/s128_ddr_response_load.sv": [
            ("module s128_ddr_response_load (", "module s128_ddr_response_load #(parameter bit OVERLAP = 1'b0) ("),
            ("logic [2:0] sent, acknowledged;", """logic [2:0] sent, acknowledged;
    logic [7:0] offered;
    logic [1:0] pending_writes;
    wire [7:0] write_slot = OVERLAP ? offered : committed;
    wire offer_has_data = write_slot != returned;
    wire skip_offer = OVERLAP && offer_has_data && poisoned[write_slot[3:0]];
    wire take_offer = s_valid && s_ready;"""),
            ("wire [1:0] lane = ", """wire [9:0] offer_base = s_base + (pair ? {1'b0, write_slot, 1'b0} : {write_slot, 2'b0});
    wire [1:0] lane = """),
            ("""assign s_rsp_ready = !reset && state == ACTIVE && acknowledged < sent;
    assign s_valid = !reset && state == ACTIVE && have_data && !drop &&
        sent < writes && (sent - acknowledged < 3'd2 || take_s);
    assign s_address = word_base + {7'd0, sent};
    assign s_data = payload[committed[3:0]][{lane, 7'd0}+:128];""", """assign s_rsp_ready = !reset && state == ACTIVE &&
        (OVERLAP ? pending_writes != 0 && !drop : acknowledged < sent);
    assign s_valid = !reset && state == ACTIVE && offer_has_data && !poisoned[write_slot[3:0]] &&
        (OVERLAP ? pending_writes < 2 || take_s : sent < writes && (sent - acknowledged < 3'd2 || take_s));
    assign s_address = offer_base + {7'd0, sent};
    assign s_data = payload[write_slot[3:0]][{lane, 7'd0}+:128];"""),
            ("            sent <= 0;", "            offered <= 0;\n            pending_writes <= 0;\n            sent <= 0;"),
            ("                    sent <= 0;\n                    acknowledged <= 0;",
             "                    offered <= 0;\n                    pending_writes <= 0;\n"
             "                    sent <= 0;\n                    acknowledged <= 0;"),
            ("                    if (commit_burst) begin", """                    if (OVERLAP) begin
                        case ({take_offer,take_s})
                            2'b10: pending_writes <= pending_writes + 1'b1;
                            2'b01: pending_writes <= pending_writes - 1'b1;
                            default: ;
                        endcase
                        if (skip_offer || (take_offer && sent + 1'b1 == writes)) begin
                            offered <= offered + 1'b1;
                            sent <= 0;
                        end else if (take_offer) sent <= sent + 1'b1;
                    end
                    if (commit_burst) begin"""),
            ("                        sent <= 0;\n                        acknowledged <= 0;",
             "                        if (!OVERLAP) sent <= 0;\n                        acknowledged <= 0;"),
            ("                        if (s_valid && s_ready) sent <= sent + 1'b1;",
             "                        if (!OVERLAP && take_offer) sent <= sent + 1'b1;"),
        ],
        f"{module}/s128_attention_core_scope.sv": [
            ("parameter bit DDR_RESPONSE_QUEUE=1'b0", "parameter bit DDR_RESPONSE_QUEUE=1'b0,\n    parameter bit OVERLAP_REFILL=1'b0"),
            ("s128_ddr_response_load load_span(", "s128_ddr_response_load #(.OVERLAP(OVERLAP_REFILL)) load_span("),
        ],
        f"{exp}/test_native_attention_core_scope.sv": [
            ("DDR_RESPONSE_QUEUE=1'b0);", "DDR_RESPONSE_QUEUE=1'b0, OVERLAP_REFILL=1'b0);"),
            (".DDR_RESPONSE_QUEUE(DDR_RESPONSE_QUEUE)) scope(",
             ".DDR_RESPONSE_QUEUE(DDR_RESPONSE_QUEUE),.OVERLAP_REFILL(OVERLAP_REFILL)) scope("),
        ],
        f"{exp}/run_native_attention_core_scope.sh": [
            ('DDR_RESPONSE_QUEUE=${DDR_RESPONSE_QUEUE:-0}"', 'DDR_RESPONSE_QUEUE=${DDR_RESPONSE_QUEUE:-0},OVERLAP_REFILL=${OVERLAP_REFILL:-0}"'),
            ('${DDR_RESPONSE_QUEUE:-0}" \\\n', '${DDR_RESPONSE_QUEUE:-0}" "-GOVERLAP_REFILL=1\'b${OVERLAP_REFILL:-0}" \\\n'),
        ],
    }
    # Anchor exactly one full line even when the suffix also matches an indented line.
    repl = edits[f"{module}/s128_ddr_response_load.sv"]
    old, new = repl[4]
    repl[4] = ("\n" + old + "\n", "\n" + new + "\n")
    patch = []
    for name, replacements in edits.items():
        before, after = change(args.root / name, replacements)
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                          fromfile=f"a/{name}", tofile=f"b/{name}"))
    args.patch.write_text("".join(patch), encoding="utf-8")


if __name__ == "__main__":
    main()

