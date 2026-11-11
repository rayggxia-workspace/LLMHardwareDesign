"""Emit rearmable RTL from the locked baseline without changing its ABI."""

import argparse
import hashlib
import json
from pathlib import Path


NATIVE = Path("project/rtl/block_local_native")
SHARED = Path("project/experiments/shared_x_control/rtl")


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"expected one source marker: {old!r}")
    return text.replace(old, new)


def edit(text, changes):
    for old, new in changes:
        text = replace_once(text, old, new)
    return text


def clear_when_idle(signal, idle, clear):
    return f"""   if(namespace_rearm)begin
`ifndef SYNTHESIS
    assert({idle})else $fatal(1,"{signal} namespace rearm before drain");
`endif
{clear}
   end
"""


def variant(stem, raw):
    text = raw.decode("utf-8")
    text = replace_once(text, f"module {stem}", f"module {stem}_rearm")
    ports = {"early_copy_3p": "  input logic clk,reset,halt,",
             "s32_a16_tile_quantizer": " input wire clk, reset,"}
    port = ports.get(stem, " input wire clk,reset")
    text = replace_once(text, port, " input wire namespace_rearm,\n" + port)
    if stem == "early_copy_3p":
        return edit(text, [
            ("assign start_ready=!reset&&!halt", "assign start_ready=!reset&&!namespace_rearm&&!halt"),
            ("      if(bad_start||bad_u||bad_ack)", clear_when_idle(
                "COPY", "quiescent&&!u_response_valid&&p_ack_valid==0",
                "    last_generation<=0;\n    for(integer i=0;i<3;i=i+1)committed[i]<=0;")
             + "      if(bad_start||bad_u||bad_ack)"),
        ])
    if stem == "early_copy_epoch_3p":
        return edit(text, [
            ("early_copy_3p #(", "early_copy_3p_rearm #("),
            ("   if(done_valid&&done_error)copy_identity_valid<=0;", "   if(done_valid&&done_error)copy_identity_valid<=0;\n"
             + clear_when_idle("tile identity", "quiescent&&!u_response_valid&&p_ack_valid==0",
                "    last_generation<=0;copy_identity_valid<=0;\n"
                "    copy_generation<=0;copy_kk<=0;copy_session<=0;copy_ticket<=0;")),
        ])
    if stem == "copy_scale_header_tx":
        return edit(text, [
            ("assign start_ready=!reset&&!halt", "assign start_ready=!reset&&!namespace_rearm&&!halt"),
            ("   if(done_valid&&done_ready)", clear_when_idle("header TX", "quiescent&&ack_valid==0",
                "    last_generation<=0;") + "   if(done_valid&&done_ready)"),
        ])
    if stem == "copy_scale_header_rx":
        return edit(text, [
            ("assign lease_ready=!reset&&!bound", "assign lease_ready=!reset&&!namespace_rearm&&!bound"),
            ("   if(ack_valid&&ack_ready)", clear_when_idle("header RX", "quiescent&&!frame_valid",
                "    last_generation<=0;") + "   if(ack_valid&&ack_ready)"),
        ])
    if stem == "s32_a16_tile_quantizer":
        return edit(text, [
            (" input wire namespace_rearm,", " input wire namespace_rearm,output wire namespace_idle,"),
            (" assign cmd_ready=!reset && !busy && !done_valid;", """ assign namespace_idle=!busy&&!done_valid&&count==0&&!stalled&&!rsp_valid;
 assign cmd_ready=!reset && !namespace_rearm && !busy && !done_valid;"""),
            ("   if(done_valid && done_ready)", clear_when_idle("quantizer", "namespace_idle",
                "    last_generation<=0;") + "   if(done_valid && done_ready)"),
        ])
    if stem == "s32_stripe_copy":
        return edit(text, [
            ("early_copy_3p #(", "early_copy_3p_rearm #("),
            ("core(.clk,.reset,.halt,", "core(.namespace_rearm,.clk,.reset,.halt,"),
        ])
    if stem == "ffn_stripe_commit":
        return edit(text, [
            (" input wire namespace_rearm,", " input wire namespace_rearm,output wire namespace_idle,"),
            (" assign stripe_ready=!reset&&phase==IDLE;", """ assign namespace_idle=phase==IDLE&&!copy_done_valid&&project_done_valid==0;
 assign stripe_ready=!reset&&!namespace_rearm&&phase==IDLE;"""),
            ("   rejected_terminals<=rejected_terminals", clear_when_idle(
                "scatter coordinator", "namespace_idle",
                "    epoch<=0;") + "   rejected_terminals<=rejected_terminals"),
        ])
    if stem == "ffn_gate_up_mid":
        return edit(text, [
            (" input wire namespace_rearm,", " input wire namespace_rearm,output wire namespace_idle,"),
            (" wire mid_result_ready;", " wire mid_result_ready,ring_start_ready;\n"
             " assign start_ready=ring_start_ready&&!namespace_rearm;"),
            ("  .start_valid,.start_ready,.start_owner,", "  .start_valid(start_valid&&!namespace_rearm),.start_ready(ring_start_ready),.start_owner,"),
            (" s32_a16_tile_quantizer quant(.clk,.reset,", " wire q_namespace_idle;\n"
             " s32_a16_tile_quantizer_rearm quant(.namespace_rearm,.namespace_idle(q_namespace_idle),.clk,.reset,"),
            (" always @(posedge clk)begin", """ assign namespace_idle=ring_start_ready&&!g_active&&qr_drained&&q_namespace_idle&&s_valid==0&&s_rsp_valid==0;
 always @(posedge clk)begin"""),
            ("   if(mid_cmd&&mid_cmd_ready&&!quant_exhausted)quant_epoch<=quant_epoch+16'd1;",
             "   if(mid_cmd&&mid_cmd_ready&&!quant_exhausted)quant_epoch<=quant_epoch+16'd1;\n"
             + clear_when_idle("Mid", "namespace_idle", "    quant_epoch<=0;")),
        ])
    raise ValueError(stem)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(args.source_lock.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=False)
    generated = {}
    for stem, directory in (("early_copy_3p", SHARED), ("early_copy_epoch_3p", NATIVE),
                            ("copy_scale_header_tx", NATIVE), ("copy_scale_header_rx", NATIVE),
                            ("s32_a16_tile_quantizer", NATIVE), ("s32_stripe_copy", NATIVE),
                            ("ffn_stripe_commit", NATIVE), ("ffn_gate_up_mid", NATIVE)):
        source = directory / (stem + ".sv")
        raw = (args.root / source).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != lock["source_sha256"][source.as_posix()]:
            raise ValueError(f"baseline source does not match lock: {source}")
        result = variant(stem, raw).encode("utf-8")
        out = args.out / (stem + "_rearm.sv")
        out.write_bytes(result)
        generated[out.name] = hashlib.sha256(result).hexdigest()
    (args.out / "generated.json").write_text(json.dumps(generated, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
