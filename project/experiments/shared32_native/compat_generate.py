"""Render legacy benches without changing the frozen bench or RTL sources."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = HERE / 'compat_baseline'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text, anchor, replacement):
    if text.count(anchor) != 1:
        raise ValueError('compatibility anchor count: ' + repr(anchor))
    return text.replace(anchor, replacement)


GROUP_TIES = '''
  .s_cold_reset(1'b0),
  .wide_write_req(1'b0),.wide_write_addr(8'd0),.wide_write_data(512'd0),.wide_write_mask(4'd0),
  .wide_write_ready(),.wide_write_valid(),.wide_write_take(1'b1),
  .load_a_shared(1'b0),.load_pool_base(11'd0),.load_pool_epoch(8'd0),
  .pool_load_valid(),.pool_load_ready(1'b0),.pool_load_base(),.pool_load_epoch(),
  .pool_load_bank(),.pool_load_wide(),.pool_load_rows(),.pool_load_tiles(),
  .pool_done_valid(1'b0),.pool_done_error(1'b0),.pool_done_take(),
  .pool_a_valid(1'b0),.pool_a_ready(),.pool_a_bank(1'b0),.pool_a_wide(1'b0),
  .pool_a_row(3'd0),.pool_a_tile(2'd0),.pool_a_data(128'd0),
'''
LOCAL_TIES = '''
  .cold_reset(1'b0),.load_skip_a(1'b0),
  .wide_write_req(1'b0),.wide_write_addr(8'd0),.wide_write_data(512'd0),.wide_write_mask(4'd0),
  .wide_write_ready(),.wide_write_valid(),.wide_write_take(1'b1),
'''
GROUP_OBSERVER = r'''
 // Added read-only observer; identical in original and new-source builds.
 integer compat_cycle=0;
 always @(posedge clk)begin
  compat_cycle<=compat_cycle+1;
  if(!reset)begin
   for(integer port=0;port<2;port=port+1)begin
    if(dut.io_req_valid[port]&&dut.io_req_ready[port])
     $display("COMPAT_EVENT c=%0d IO_REQ p=%0d wr=%b a=%h d=%h",compat_cycle,port,dut.io_req_write[port],dut.io_req_addr[port*10+:10],dut.io_req_data[port*128+:128]);
    if(dut.io_rsp_valid[port]&&dut.io_rsp_ready[port])
     $display("COMPAT_EVENT c=%0d IO_RSP p=%0d d=%h",compat_cycle,port,dut.io_rsp_data[port*128+:128]);
   end
   if(dut.load_valid&&dut.load_ready)
    $display("COMPAT_EVENT c=%0d LOAD b=%b r=%d t=%d aw=%b bw=%b rb=%b a=%h w=%h",compat_cycle,dut.load_bank,dut.load_rows,dut.load_tiles,dut.load_a_wide,dut.load_b_wide,dut.load_reuse_b,dut.load_a_base,dut.load_b_base);
   if(dut.load_done&&dut.load_take)$display("COMPAT_EVENT c=%0d LOAD_DONE e=%b",compat_cycle,dut.load_error);
   if(dut.a_valid&&dut.a_ready)$display("COMPAT_EVENT c=%0d A b=%b r=%d t=%d w=%b d=%h",compat_cycle,dut.a_bank,dut.a_row,dut.a_tile,dut.a_wide,dut.a_data);
   if(dut.b_valid&&dut.b_ready)$display("COMPAT_EVENT c=%0d B b=%b t=%d w=%b h=%b d=%h",compat_cycle,dut.b_bank,dut.b_tile,dut.b_wide,dut.b_half,dut.b_data);
   if(dut.cmd_valid&&dut.cmd_ready)$display("COMPAT_EVENT c=%0d CMD op=%h idx=%h d=%h st=%b dst=%h route=%b pack=%b",compat_cycle,dut.cmd_op,dut.cmd_index,dut.cmd_data,dut.cmd_store,dut.cmd_dst,dut.cmd_route,dut.cmd_pack16);
   if(dut.cmd_done&&dut.cmd_take)$display("COMPAT_EVENT c=%0d CMD_DONE e=%b sat=%b d=%h",compat_cycle,dut.cmd_error,dut.cmd_saturated,dut.cmd_result);
   if(dut.gate_valid&&dut.gate_ready)$display("COMPAT_EVENT c=%0d GATE a=%h b=%h dst=%h route=%b",compat_cycle,dut.gate_a,dut.gate_b,dut.gate_dst,dut.gate_route);
   if(dut.gate_done&&dut.gate_take)$display("COMPAT_EVENT c=%0d GATE_DONE e=%b sat=%b",compat_cycle,dut.gate_error,dut.gate_saturated);
  end
 end
'''
LOCAL_OBSERVER = r'''
 integer compat_cycle=0;
 always @(posedge clk)begin
  compat_cycle<=compat_cycle+1;
  if(!reset)begin
   if(req_valid&&req_ready)$display("COMPAT_EVENT c=%0d REQ wr=%b a=%h d=%h",compat_cycle,req_write,req_addr,req_data);
   if(rsp_valid&&rsp_ready)$display("COMPAT_EVENT c=%0d RSP d=%h",compat_cycle,rsp_data);
   if(load_valid&&load_ready)$display("COMPAT_EVENT c=%0d LOAD b=%b r=%d t=%d aw=%b bw=%b rb=%b a=%h w=%h",compat_cycle,load_bank,load_rows,load_tiles,load_a_wide,load_b_wide,load_reuse_b,load_a_base,load_b_base);
   if(a_valid&&a_ready)$display("COMPAT_EVENT c=%0d A b=%b r=%d t=%d w=%b d=%h",compat_cycle,a_bank,a_row,a_tile,a_wide,a_data);
   if(b_valid&&b_ready)$display("COMPAT_EVENT c=%0d B b=%b t=%d w=%b h=%b d=%h",compat_cycle,b_bank,b_tile,b_wide,b_half,b_data);
   if(done_valid&&done_take)$display("COMPAT_EVENT c=%0d DONE e=%b",compat_cycle,done_error);
  end
 end
'''

BENCHES = {
    'group': 'project/experiments/p_native_opt/tb_popt_group.sv',
    'program': 'project/experiments/pu_leaf_base/tb_pu_p_group.sv',
    'local': 'project/experiments/p_native_opt/tb_popt_local.sv',
}


def render(text, kind, candidate):
    if candidate:
        if kind in ('group', 'program'):
            text = once(text, ' dut(\n', ' dut(\n' + GROUP_TIES)
        else:
            text = once(text, 'dut(.*);', 'dut(\n' + LOCAL_TIES + '  .*);')
    observer = LOCAL_OBSERVER if kind == 'local' else GROUP_OBSERVER
    return once(text, 'endmodule', observer + '\nendmodule')


def generate(repo, out):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError('compat generation directory must be fresh')
    lock = json.loads((BASELINE/'source.json').read_text(encoding='utf8'))
    for name, entry in lock['files'].items():
        if sha(BASELINE/entry['snapshot']) != entry['sha256']:
            raise ValueError('original RTL snapshot drift: ' + name)
    out.mkdir(parents=True)
    result = dict(baseline=lock, unchanged_bench_sha256={}, generated_sha256={})
    for kind, source in BENCHES.items():
        path = repo/source
        result['unchanged_bench_sha256'][source] = sha(path)
        text = path.read_text(encoding='utf8')
        for variant in ('original', 'candidate'):
            target = out/(kind+'-'+variant+'.sv')
            target.write_bytes(render(text, kind, variant == 'candidate').encode())
            result['generated_sha256'][target.name] = sha(target)
    (out/'generation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(generate(args.repo, args.out), indent=2))
