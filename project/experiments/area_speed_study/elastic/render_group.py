"""Prepare a SHA-guarded isolated P-group fork; never edit the repository."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOCK={
    'project/rtl/pu_leaf_base/pj_feed_hold.sv':'ed4ee4b4f4875f88c6108a911b82661b581f7786a556ca83cabeece7b2b51061',
    'project/rtl/pu_leaf_base/pu_p_group.sv':'ab55887ac575cc3715045af4efe07032264413e3ae84ea5666a8f5ccbb9a2982',
    'project/experiments/pu_leaf_base/tb_pu_p_group.sv':'f69c47af18a1ebb45506df31f091f6c430a3bcc90eb66caa6501179d06aa8334',
}


def digest(raw):return hashlib.sha256(raw).hexdigest()


def render(repo,out):
    frozen={}
    for name,value in LOCK.items():
        raw=(repo/name).read_bytes()
        if digest(raw)!=value:raise ValueError('upstream source identity drift '+name)
        frozen[name]=raw
    out.mkdir(parents=True,exist_ok=False)
    (out/'baseline').mkdir();(out/'candidate').mkdir()
    source=frozen['project/rtl/pu_leaf_base/pu_p_group.sv'].decode('utf-8')
    changes=[
        ('wire feed_empty=sa_ready && sb_ready;',
         'wire feed_a_empty,feed_b_empty;\n wire feed_empty=feed_a_empty && feed_b_empty;'),
        ('pj_feed_hold #(.WIDTH(135)) hold_a(',
         'pj_feed_elastic #(.WIDTH(135)) hold_a('),
        ('.dst_valid(a_valid),.dst_ready(a_ready),.dst_data({a_bank,a_row,a_tile,a_wide,a_data}));',
         '.dst_valid(a_valid),.dst_ready(a_ready),.dst_data({a_bank,a_row,a_tile,a_wide,a_data}),.empty(feed_a_empty));'),
        ('pj_feed_hold #(.WIDTH(517)) hold_b(',
         'pj_feed_elastic #(.WIDTH(517)) hold_b('),
        ('.dst_valid(b_valid),.dst_ready(b_ready),.dst_data({b_bank,b_tile,b_wide,b_half,b_data}));',
         '.dst_valid(b_valid),.dst_ready(b_ready),.dst_data({b_bank,b_tile,b_wide,b_half,b_data}),.empty(feed_b_empty));'),
    ]
    for before,after in changes:
        if source.count(before)!=1:raise ValueError('patch anchor not unique '+before)
        source=source.replace(before,after)
    (out/'baseline/pj_feed_hold.sv').write_bytes(frozen['project/rtl/pu_leaf_base/pj_feed_hold.sv'])
    (out/'baseline/pu_p_group.sv').write_bytes(frozen['project/rtl/pu_leaf_base/pu_p_group.sv'])
    (out/'candidate/pu_p_group.sv').write_bytes(source.encode('utf-8'))
    (out/'candidate/pj_feed_elastic.sv').write_bytes((HERE/'pj_feed_elastic.sv').read_bytes())
    (out/'tb_pu_p_group.sv').write_bytes(frozen['project/experiments/pu_leaf_base/tb_pu_p_group.sv'])
    bench=frozen['project/experiments/pu_leaf_base/tb_pu_p_group.sv'].decode('utf-8')
    if bench.count('module tb_pu_p_group;')!=1:raise ValueError('bench header identity drift')
    bench=bench.replace('module tb_pu_p_group;',
        'module tb_pu_p_group;\n integer issue247_cycles=0;\n'
        ' always @(posedge clk) issue247_cycles=issue247_cycles+1;\n'
        ' final $display("P_GROUP_CYCLES %0d",issue247_cycles);',1)
    (out/'tb_pu_p_group_timed.sv').write_bytes(bench.encode('utf-8'))
    report=dict(upstream_sha256=LOCK,generated_files_sha256={
        str(p.relative_to(out)):digest(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()},
        changes='only two feeder links plus explicit-empty completion predicate; original module name retained in separately compiled variants',
        timed_bench='optional cycle counter/final display only; all original checks retained; exact original bench also copied',
        no_changes='SRAM capacity/ports, M arithmetic, external handshake ports, ACK retirement and controller code',
        qualification='candidate only; prepare does not run simulation or grant physical qualification')
    (out/'source.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(render(a.repo.resolve(),a.out.resolve())))


if __name__=='__main__':main()
