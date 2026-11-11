"""Create a default-compatible U NExp candidate without changing production."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
UPSTREAM_COMMIT='189e43c77a6277955c1be54281b0d6b0b0d55c1f'
BASE_U_SHA='f2136115a15aa34260f598770b5576970dfadea407879d897e5571630989bd59'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('U source anchor drift '+old[:90])
    return text.replace(old,new,1)


def candidate(source):
    source=once(source,'module pu_u_group (','module pu_u_group #(parameter integer NEXP_BATCH=0) (')
    source=once(source,'    wire n_complete;','''    wire n_complete,n_service_ready;
    wire [127:0] n_service_data;
    wire n_service_error,n_service_saturated;
    reg n_rejected;
    wire n_is_batch=NEXP_BATCH!=0&&n_cmd_meta[3:0]==15;
    wire n_is_32=n_cmd_meta[39:8]==32'h4e583332;
    wire n_batch_bad=n_is_batch&&(
        (n_cmd_meta[39:8]!=32'h4e455850&&!n_is_32)||n_cmd_meta[7:4]==0||
        n_cmd_meta[7:4]>(n_is_32?4:8)||n_cmd_sources!=1||n_cmd_src[19:10]!=0||n_cmd_direct);
    assign n_cmd_ready=n_service_ready&&!n_rejected;
    assign n_done_data=n_rejected?128'd0:n_service_data;
    assign n_done_error=n_rejected||n_service_error;
    assign n_done_saturated=!n_rejected&&n_service_saturated;
    always @(posedge clk)begin
        if(reset)n_rejected<=0;
        else begin
            if(n_rejected&&n_done_ready)n_rejected<=0;
            if(n_cmd_valid&&n_cmd_ready&&n_batch_bad)n_rejected<=1;
        end
    end''')
    source=once(source,'assign n_done_valid = n_complete && (!n_direct || n_done_error || n_sent);',
        'assign n_done_valid = !reset && (n_rejected || (n_complete && (!n_direct || n_done_error || n_sent)));')
    source=once(source,'.cmd_valid(n_cmd_valid), .cmd_ready(n_cmd_ready),',
        '.cmd_valid(n_cmd_valid&&!n_rejected&&!n_batch_bad), .cmd_ready(n_service_ready),')
    source=once(source,'.done_data(n_done_data),\n        .done_error(n_done_error), .done_saturated(n_done_saturated),',
        '.done_data(n_service_data),\n        .done_error(n_service_error), .done_saturated(n_service_saturated),')
    begin=source.index('    block_v2_n normalize(')
    end=source.index('\n    wire e_valid',begin)
    source=source[:begin]+'''    wire core_valid,core_ready,core_result_valid,core_result_ready,core_error,core_saturated;
    wire [63:0] core_meta;
    wire [127:0] core_a,core_b,core_result;
    generate if(NEXP_BATCH!=0)begin: batch_route
        pu_nexp_shared dispatch(
            .clk,.reset,.exec_valid(n_valid),.exec_ready(n_ready),.exec_meta(n_meta),.exec_a(na),.exec_b(nb),
            .result_valid(nr_valid),.result_ready(nr_ready),.result_data(nr),.result_error(nr_error),.result_saturated(nr_sat),
            .n_valid(core_valid),.n_ready(core_ready),.n_meta(core_meta),.n_a(core_a),.n_b(core_b),
            .n_result_valid(core_result_valid),.n_result_ready(core_result_ready),.n_result(core_result),
            .n_error(core_error),.n_saturated(core_saturated)
        );
    end else begin: legacy_route
        assign core_valid=n_valid;assign n_ready=core_ready;assign core_meta=n_meta;assign core_a=na;assign core_b=nb;
        assign nr_valid=core_result_valid;assign core_result_ready=nr_ready;assign nr=core_result;
        assign nr_error=core_error;assign nr_sat=core_saturated;
    end endgenerate
    // Exactly one native N, unchanged source and arithmetic resources.
    block_v2_n normalize(
        .clk, .reset, .cmd_valid(core_valid), .cmd_ready(core_ready),
        .cmd_op(core_meta[3:0]), .cmd_count(core_meta[7:4]), .cmd_param(core_meta[39:8]),
        .cmd_data(core_a), .cmd_aux(core_b), .rsp_valid(core_result_valid), .rsp_ready(core_result_ready),
        .rsp_data(core_result), .rsp_error(core_error), .rsp_saturated(core_saturated), .busy()
    );
''' + source[end:]
    return source


def generate(repo,out,integrated=True):
    repo,out=Path(repo).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    group=repo/'project/rtl/pu_leaf_base/pu_u_group.sv';baseline=HERE/'pu_u_group_upstream.sv'
    if sha(baseline)!=BASE_U_SHA:raise ValueError('frozen original U source changed')
    text=candidate(baseline.read_text(encoding='utf-8'))
    if sha(group) not in (BASE_U_SHA,hashlib.sha256(text.encode()).hexdigest()):raise ValueError('formal U source not original or exact candidate')
    if integrated and sha(group)!=hashlib.sha256(text.encode()).hexdigest():raise ValueError('production U candidate is not integrated')
    (out/'pu_u_group_baseline.sv').write_bytes(baseline.read_bytes())
    assert text.count('block_v2_n normalize(')==1
    (out/'pu_u_group.sv').write_bytes(text.encode())
    for name in ('pu_nexp_shared.sv','nexp_batch_adapter.sv','tb_nexp_compute.sv','tb_nexp_u.sv'):
        (out/name).write_bytes((HERE/name).read_bytes())
        if integrated and name in ('pu_nexp_shared.sv','nexp_batch_adapter.sv'):
            if sha(repo/'project/rtl/pu_leaf_base'/name)!=sha(HERE/name):raise ValueError('production shared adapter differs from candidate '+name)
    # Reuse the original complete U program twice, without changing its tasks.
    original=(repo/'project/experiments/pu_leaf_base/tb_pu_u_group.sv').read_text(encoding='utf-8')
    monitor='''
    integer compat_cycle=0;
    always @(posedge clk)begin
        compat_cycle<=compat_cycle+1;
        if(!reset)begin
            for(integer c=0;c<2;c=c+1)begin
                if(service_valid[c]&&cmd_ready[c])$display("COMPAT CMD c=%0d lane=%0d meta=%h sources=%h addresses=%h dst=%h store=%b",compat_cycle,c,service_meta[64*c+:64],service_sources[2*c+:2],service_addresses[30*c+:30],service_dst[10*c+:10],service_store[c]);
                if(done_valid[c]&&service_take[c])$display("COMPAT DONE c=%0d lane=%0d error=%b sat=%b data=%h",compat_cycle,c,done_error[c],done_saturated[c],done_data[128*c+:128]);
            end
            if(rx_valid&&rx_ready)$display("COMPAT WRITE c=%0d addr=%h data=%h",compat_cycle,rx_addr,rx_data);
            if(tx_valid&&tx_take)$display("COMPAT READ c=%0d addr=%h data=%h",compat_cycle,tx_addr,tx_data);
        end
    end
'''
    original=once(original,'endmodule',monitor+'endmodule')
    (out/'tb_legacy.sv').write_bytes(original.encode())
    enabled=once(original,'pu_u_group dut (','pu_u_group #(.NEXP_BATCH(1)) dut (')
    (out/'tb_enabled_legacy.sv').write_bytes(enabled.encode())
    result=dict(upstream_commit=UPSTREAM_COMMIT,
        source_sha256={group.relative_to(repo).as_posix():sha(group)},baseline_U_sha256=BASE_U_SHA,
        generated_sha256={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
        native_N_instances=1,integrated_production=integrated,SRAM_expansion=False,physical_qualified=False)
    (out/'generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--prepare',action='store_true',help='generation only; permit original production U before integration')
    a=p.parse_args();print(json.dumps(generate(a.repo,a.out,not a.prepare)))
