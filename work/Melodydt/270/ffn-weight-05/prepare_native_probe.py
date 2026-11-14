"""Enable the FFN timing probe in an isolated extracted source archive."""

import argparse
from pathlib import Path


def replace_once(path, old, new):
    source = path.read_bytes()
    old, new = old.encode("ascii"), new.encode("ascii")
    if source.count(old) != 1:
        raise ValueError("unexpected source context in {}".format(path))
    path.write_bytes(source.replace(old, new))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    project = args.source / "project"
    monitor = r"""// Simulation-only record timing. All events are sampled on accepted transfers.
 always @(posedge clk) begin : ffn_weight_probe
  if (!reset && $test$plusargs("FFN_WEIGHT_PROBE")) begin
   if (n_issue_valid && n_issue_ready) begin
    if (n_issue_beat == 0)
     $display("M_WEIGHT %m first_issue %0t %0d %0d %0d %h", $time,
              n_issue_bank, n_issue_generation, n_issue_record, mc_req_address);
    if (n_issue_beat == mc_req_record_beats - 1'b1)
     $display("M_WEIGHT %m last_issue %0t %0d %0d %0d 0", $time,
              n_issue_bank, n_issue_generation, n_issue_record);
   end
   if (n_fill_valid && n_fill_ready &&
       $countones(table_received[n_fill_bank]) + 1 == (table_head[n_fill_bank] ? 18 : 17))
    $display("M_WEIGHT %m full_fill %0t %0d %0d %0d 0", $time,
             n_fill_bank, n_fill_generation, n_fill_record);
   if (n_fill_ack_valid && n_fill_ack_ready && !n_fill_ack_error)
    $display("M_WEIGHT %m ack %0t %0d %0d %0d 0", $time,
             n_fill_ack_bank, n_fill_ack_generation, n_fill_ack_record);
   if (n_exec_valid && n_exec_ready)
    $display("M_WEIGHT %m exec %0t %0d %0d %0d %h", $time,
             n_exec_bank, n_exec_generation, n_exec_record, n_exec_ticket);
   if (n_rsp_valid && n_rsp_ready && n_rsp_kind == 3'd2 && !n_rsp_error)
    $display("M_WEIGHT %m result %0t %0d %0d %0d %h", $time,
             n_rsp_bank, n_rsp_generation, n_rsp_record, n_rsp_ticket);
  end
 end"""
    replace_once(
        project / "rtl/w8a16_v1/m_native_leaf_s32.sv",
        "\nendmodule\n",
        "\n`ifndef SYNTHESIS\n" + monitor + "\n`endif\nendmodule\n",
    )
    replace_once(
        project / "experiments/block_local_native/run_decode638_q_tile_replay.sh",
        '"+verilator+seed+25001"',
        '"+FFN_WEIGHT_PROBE" "+verilator+seed+25001"',
    )


if __name__ == "__main__":
    main()
