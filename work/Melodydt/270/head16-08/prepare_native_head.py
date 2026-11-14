"""Profile the sealed native vocabulary fixture and optionally admit HEAD16 to the existing pair policy."""

import argparse
from hashlib import sha256
from pathlib import Path


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise ValueError("unexpected source context in {} for {}".format(path, old))
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


MONITOR = r"""
 integer head_start, head_busy, head_w_wait, head_a_wait, head_both_wait, head_peak;
 integer head_tile, head_projected, head_last_read, head_entries;
 always @(posedge clk) begin : head_profile
  if(reset) begin
   head_start<=0; head_busy<=0; head_w_wait<=0; head_a_wait<=0; head_both_wait<=0; head_peak<=0;
   head_tile<=0; head_projected<=0; head_last_read<=0; head_entries<=0;
  end else begin
   if(launch) begin
    head_start<=int'(cycles); head_busy<=0; head_w_wait<=0; head_a_wait<=0; head_both_wait<=0; head_peak<=0;
    head_tile<=head_tile+1; head_last_read<=0; head_entries<=0;
   end else begin
    if(node.M.n_busy)head_busy<=head_busy+1;
    if(int'($countones(node.M.table_valid))>head_peak)head_peak<=int'($countones(node.M.table_valid));
    if(node.exec.early_exec.exec.state==5'd8) begin
     if(!(node.exec.early_exec.exec.pair_prep_second ?
           node.exec.early_exec.exec.saved_fill_seen : node.exec.early_exec.exec.fill_seen)) begin
      if(node.exec.early_exec.exec.A_loaded[node.exec.early_exec.exec.selected_A_slot])head_w_wait<=head_w_wait+1;
      else head_both_wait<=head_both_wait+1;
     end else if(!node.exec.early_exec.exec.A_loaded[node.exec.early_exec.exec.selected_A_slot])
      head_a_wait<=head_a_wait+1;
    end
   end
   if(done_valid&&window_done&&!window_bad&&producer_done_ready)head_projected<=int'(cycles);
   if(aux_rsp&&arg_take)begin
    head_last_read<=int'(cycles);head_entries<=head_entries+1;
   end
   if(vocabulary_terminal&&service_done_ready[0])begin
    assert(head_entries==32&&head_start<head_projected&&head_projected<head_last_read)
     else $fatal(1,"HEAD16 profile coverage");
    $display("HEAD_TIMING %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
             head_tile,head_start,head_projected,head_last_read,cycles,
             head_busy,head_w_wait,head_a_wait,head_both_wait,head_peak);
   end
  end
 end
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("runner", type=Path)
    parser.add_argument("variant", choices=("baseline", "candidate"))
    parser.add_argument("mode", choices=("0", "1"))
    args = parser.parse_args()
    path = args.source / "project/experiments/shared_x_control/rtl/p_native_weight_overlap_candidate.sv"
    if sha256(path.read_bytes()).hexdigest() != "b54e67cd98b1a3bc1b5fd2fc3ddb6c98962fd3146d91f552763531ff40ef5a36":
        raise ValueError("frozen native controller changed")
    if args.variant == "candidate":
        edit(path, "wire pair_candidate=scope_data[48+:16]==2&&",
             "wire pair_candidate=(scope_data[48+:16]==2||head)&&")

    source = args.runner.read_text(encoding="utf-8")
    start = source.index("sealed=$root/")
    stop = source.index("readarray -t params", start)
    source = source[:start] + '''sealed=$run/assets
mkdir "$generated"
cp "$sealed"/generated/* "$generated/"
python3 -B "$SLURM_SUBMIT_DIR/prepare_native_head.py" "--instrument=$generated/test_native_projection_live.sv"
''' + source[stop:]
    source = source.replace("  modes=(1)", "  modes=(" + args.mode + ")", 1)
    args.runner.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1].startswith("--instrument="):
        path = Path(sys.argv[1].split("=", 1)[1])
        if sha256(path.read_bytes()).hexdigest() != "cd3d8ffac5893b7ad3cfb7da6e8fabce5e607af48dc06f1e6575a997d3e11868":
            raise ValueError("sealed native fixture changed")
        edit(path, "\nendmodule\n", MONITOR + "\nendmodule\n")
        edit(path, "    if(arg_token_valid&&arg_token_ready) begin",
             '    if(arg_token_valid&&arg_token_ready) begin\n     $display("HEAD_ARGMAX %0d",cycles);')
    else:
        main()
