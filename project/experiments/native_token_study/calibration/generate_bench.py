"""Generate a narrow actual-P timing probe; no production RTL is modified."""
from pathlib import Path


def generate(repo, out):
    original = (Path(repo) / 'project/experiments/p_native_opt/tb_popt_group.sv').read_text()
    prefix = original.split(' integer cycle=0,')[0]
    prefix = prefix.replace('module tb_popt_group #(parameter integer OPT=1, BANK_RW=0, SEGMENTS=2);', 'module tb_token_timing #(parameter integer BANK_RW=0, POLICY=0);')
    prefix = prefix.replace('logic [3:0] load_rows=1;', 'logic [3:0] load_rows=3; logic [2:0] load_tiles=1; logic load_aw=1,load_bw=0;')
    prefix = prefix.replace('.S_CONSUMER_PRIORITY(OPT)', '.S_CONSUMER_PRIORITY(POLICY)').replace('.M_CONTEXTS(OPT?8:0)', '.M_CONTEXTS(8)')
    prefix = prefix.replace(".load_tiles(3'd1)", '.load_tiles').replace(".load_a_wide(1'b0),.load_b_wide(1'b0)", '.load_a_wide(load_aw),.load_b_wide(load_bw)')
    assert 'OPT' not in prefix and '.load_tiles,' in prefix
    Path(out).write_text(prefix + (Path(__file__).with_name('timing_body.sv.inc')).read_text())


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--repo', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); generate(a.repo, a.out)
