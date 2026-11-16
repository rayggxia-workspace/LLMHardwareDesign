"""Add guarded lookahead to the qualified combined near-wrap test."""

import argparse
import hashlib
import json
from pathlib import Path

from derive_copy_epoch_rearm import edit
from derive_guarded_copy_lookahead import core, epoch


def locked(path, digest):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"combined COPY lookahead input does not match lock: {path}")
    return raw.decode("utf-8")


def test_top(text):
    return edit(text, [
        (" integer first_purges;", " integer first_purges;\n reg held_prefetched_u_response;"),
        (" early_copy_epoch_3p_rearm xcopy(.namespace_rearm,",
         " early_copy_epoch_3p_rearm_lookahead xcopy(.namespace_rearm,.start_source_independent(!down_phase),"),
        ("   fence_count<=0;blocked_ack_cycles<=0;", "   fence_count<=0;blocked_ack_cycles<=0;held_prefetched_u_response<=0;"),
        ("    blocked_ack_cycles<=blocked_ack_cycles+1;", """    blocked_ack_cycles<=blocked_ack_cycles+1;
    if(xcopy_u_rsp_valid&&!xcopy_u_rsp_ready)held_prefetched_u_response<=1;"""),
        ("  first_purges=int'(dma_purge_count);", "  assert(held_prefetched_u_response)else $fatal(1,\"test did not hold a real prefetched U response\");\n  first_purges=int'(dma_purge_count);"),
        ("  $display(\"PASS ffn_copy_combined", "  $display(\"COPY_NEAR_WRAP held_prefetched_U=1 and_old_P_ACK=1\");\n  $display(\"PASS ffn_copy_combined"),
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(args.source_lock.read_text(encoding="utf-8"))
    top = args.test / "test_ffn_copy_combined.sv"
    text = locked(top, "43a8a444f98a67b193236ca9a37a6cfc480fa5116d4f937d7d893951eb4417ed")
    top.write_bytes(test_top(text).encode("utf-8"))
    for stem, convert in (("early_copy_3p_rearm", core), ("early_copy_epoch_3p_rearm", epoch)):
        name = stem + ".sv"
        text = locked(args.generated / name, lock["rearm_sha256"][name])
        (args.test / (stem + "_lookahead.sv")).write_bytes(convert(text).encode("utf-8"))


if __name__ == "__main__":
    main()
