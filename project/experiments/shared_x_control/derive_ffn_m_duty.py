"""Probe one real M per P in the exact full programmed FFN fixture."""

import argparse
import hashlib
import json
from pathlib import Path

from derive_copy_epoch_rearm import edit


EXP = Path("project/experiments/block_local_native")
PROBES = """ reg duty_enabled=0;
 integer duty_ticks[2],ddr_hist[2][5],local_offer_hist[2][4];
 integer no_ddr_local_offer[2],no_ddr_backend_offer[2],no_ddr_with_return[2];
 wire [3:0] backend_fire=actual_shared_dma.d_req&actual_shared_dma.d_req_ready;
 wire [3:0] backend_return=actual_shared_dma.d_rsp&actual_shared_dma.d_rsp_ready;
 always @(posedge clk)begin
  if(reset)begin
   duty_ticks<='{default:0};ddr_hist<='{default:'{default:0}};local_offer_hist<='{default:'{default:0}};
   no_ddr_local_offer<='{default:0};no_ddr_backend_offer<='{default:0};no_ddr_with_return<='{default:0};
  end else if(duty_enabled)begin
   duty_ticks[down_phase]<=duty_ticks[down_phase]+1;
   ddr_hist[down_phase][$countones(backend_fire)]<=ddr_hist[down_phase][$countones(backend_fire)]+1;
   local_offer_hist[down_phase][$countones(mr_valid)]<=local_offer_hist[down_phase][$countones(mr_valid)]+1;
   if(backend_fire==0)begin
    if(mr_valid!=0)no_ddr_local_offer[down_phase]<=no_ddr_local_offer[down_phase]+1;
    if(actual_shared_dma.d_req!=0)no_ddr_backend_offer[down_phase]<=no_ddr_backend_offer[down_phase]+1;
    if(backend_return!=0)no_ddr_with_return[down_phase]<=no_ddr_with_return[down_phase]+1;
   end
  end
 end
 for(genvar p=0;p<3;p++)begin: probe_m
  // Enum positions are from the exact locked early-EXEC provider. This is
  // fixture telemetry and creates no product state or measurement ports.
  localparam [4:0] FILL_WAIT_STATE=5'd8;
  wire [4:0] provider_state=ps[p].node.exec.early_exec.exec.state;
  wire weight_ready=ps[p].node.exec.early_exec.exec.pair_prep_second ?
      ps[p].node.exec.early_exec.exec.saved_fill_seen : ps[p].node.exec.early_exec.exec.fill_seen;
  wire activation_ready=ps[p].node.exec.early_exec.exec.A_loaded[ps[p].node.exec.early_exec.exec.selected_A_slot];
  wire exec_fire=ps[p].node.M.n_exec_valid&&ps[p].node.M.n_exec_ready;
  wire mac_fire=ps[p].node.M.native.operands&&ps[p].node.M.native.raw_in_ready;
  wire feed=ps[p].node.M.native.feeding;
  wire raw_pipe=ps[p].node.M.native.raw.v0||ps[p].node.M.native.raw.v1;
  integer provider_hist[2][32];
  integer mac[2],exec_accept[2],pipe_active[2],feeding[2],feed_no_W[2],feed_no_A[2];
  integer fill_wait_W_only[2],fill_wait_A_only[2],fill_wait_both[2],fill_ready[2];
  always @(posedge clk)begin
   if(reset)begin
    provider_hist<='{default:'{default:0}};
    mac<='{default:0};exec_accept<='{default:0};pipe_active<='{default:0};feeding<='{default:0};
    feed_no_W<='{default:0};feed_no_A<='{default:0};fill_wait_W_only<='{default:0};fill_wait_A_only<='{default:0};
    fill_wait_both<='{default:0};fill_ready<='{default:0};
   end else if(duty_enabled)begin
    provider_hist[down_phase][provider_state]<=provider_hist[down_phase][provider_state]+1;
    if(mac_fire)mac[down_phase]<=mac[down_phase]+1;
    if(exec_fire)exec_accept[down_phase]<=exec_accept[down_phase]+1;
    if(raw_pipe)pipe_active[down_phase]<=pipe_active[down_phase]+1;
    if(feed)begin
     feeding[down_phase]<=feeding[down_phase]+1;
     if(!ps[p].node.M.native.w_valid)feed_no_W[down_phase]<=feed_no_W[down_phase]+1;
     if(!ps[p].node.M.native.a_valid)feed_no_A[down_phase]<=feed_no_A[down_phase]+1;
    end
    if(provider_state==FILL_WAIT_STATE)begin
     case({weight_ready,activation_ready})
      2'b00:fill_wait_both[down_phase]<=fill_wait_both[down_phase]+1;
      2'b01:fill_wait_W_only[down_phase]<=fill_wait_W_only[down_phase]+1;
      2'b10:fill_wait_A_only[down_phase]<=fill_wait_A_only[down_phase]+1;
      2'b11:fill_ready[down_phase]<=fill_ready[down_phase]+1;
     endcase
    end
   end
  end
  task automatic report(input integer phase);
   assert(mac[phase]==8*exec_accept[phase]);
   $display("M_DUTY phase=%0d p=%0d cycles=%0d exec=%0d mac=%0d pipe=%0d feed=%0d feed_no_W=%0d feed_no_A=%0d fill_W=%0d fill_A=%0d fill_both=%0d fill_ready=%0d",
      phase,p,duty_ticks[phase],exec_accept[phase],mac[phase],pipe_active[phase],feeding[phase],feed_no_W[phase],feed_no_A[phase],
      fill_wait_W_only[phase],fill_wait_A_only[phase],fill_wait_both[phase],fill_ready[phase]);
   $display("M_STATE_DUTY phase=%0d p=%0d states=%p",phase,p,provider_hist[phase]);
  endtask
 end
 task automatic report_duty(input integer phase);
  probe_m[0].report(phase);probe_m[1].report(phase);probe_m[2].report(phase);
  $display("DDR_DUTY phase=%0d cycles=%0d accepted_lanes=%p M_offers=%p zero_accept_with_local_offer=%0d zero_accept_with_backend_offer=%0d zero_accept_with_return=%0d",
     phase,duty_ticks[phase],ddr_hist[phase],local_offer_hist[phase],no_ddr_local_offer[phase],
     no_ddr_backend_offer[phase],no_ddr_with_return[phase]);
 endtask
"""


def full_top(text):
    return edit(text, [
        ("  start_cycle=cycle;", "  start_cycle=cycle;duty_enabled=1;"),
        ("  $display(\"FFN_PROFILE", "  duty_enabled=0;report_duty(0);\n  $display(\"FFN_PROFILE"),
        ("   down_phase=1;down_start=cycle;", "   duty_enabled=1;down_phase=1;down_start=cycle;"),
        ("   $display(\"DOWN_PROFILE", "   duty_enabled=0;report_duty(1);\n   $display(\"DOWN_PROFILE"),
        ("endmodule\n", PROBES + "endmodule\n"),
    ])


def runner(text):
    return edit(text, [
        ('"$EXP"/{test_ffn_native_p_node,test_ffn_three_p_native}.sv',
         '"$EXP/test_ffn_native_p_node.sv" "$root/duty/test_ffn_three_p_native.sv"'),
        ('for initial in 0 1 2; do', 'for initial in 0; do'),
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    locked = json.loads(args.source_lock.read_text(encoding="utf-8"))["source_sha256"]
    for name, convert in (("test_ffn_three_p_native.sv", full_top), ("job_ffn_native.sh", runner)):
        path = EXP / name
        raw = (args.root / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != locked[path.as_posix()]:
            raise ValueError(f"M duty source does not match lock: {path}")
        (args.out / name).write_bytes(convert(raw.decode("utf-8")).encode("utf-8"))


if __name__ == "__main__":
    main()
