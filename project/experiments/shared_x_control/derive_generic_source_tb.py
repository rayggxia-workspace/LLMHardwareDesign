"""Text-only generation: reuse the real-S A/copy oracle for all four sources."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
text = (HERE / "rtl/tb_native_s_a_copy.sv").read_text()
text = text.replace("module tb_native_s_a_copy;", "module tb_native_s_source_copy;")
begin = text.index("  logic host_valid")
end = text.index("  integer cycle", begin)
wiring = r"""
  logic host_valid,host_ready,host_response_valid,host_response_ready,host_mode;
  logic [9:0] host_address;
  logic [127:0] host_data;
  logic allow_responses;
  logic [2:0] cv[4],cw[4],cr[4],rv[4],rr[4];
  logic [1:0] occupied[4];
  logic [29:0] ca[4];
  logic [383:0] cd[4];
  logic [95:0] ct[4],rt[4];
  logic [127:0] rd[4];
  logic [3:0] nv,nw,nready,nrv,nrr;
  logic [9:0] na[4];
  logic [127:0] nd[4],nrd[4];
  logic bind_valid,bind_ready,release_copy_valid,release_copy_ready,bound,router_drained;
  logic [1:0] bind_source,bound_source;
  logic [127:0] bound_key;
  logic [3:0] src_valid,src_ready,src_rsp_valid,src_rsp_ready;
  logic [39:0] src_address;
  logic [127:0] src_tag,src_rsp_tag;
  logic [511:0] src_rsp_data;
  logic [31:0] router_faults;
  early_copy_source_router router(.clk,.reset,.bind_valid,.bind_ready,.bind_source,
    .bind_key(start_key),.release_valid(release_copy_valid),.release_ready(release_copy_ready),
    .release_key(start_key),.bound,.bound_source,.bound_key,.drained(router_drained),
    .u_valid,.u_ready,.u_address,.u_tag,.u_response_valid,.u_response_ready,.u_response_data,
    .u_response_tag,.u_response_error,.source_valid(src_valid),.source_ready(src_ready),
    .source_address(src_address),.source_tag(src_tag),.source_response_valid(src_rsp_valid),
    .source_response_ready(src_rsp_ready),.source_response_data(src_rsp_data),
    .source_response_tag(src_rsp_tag),.source_response_error(4'b0),.fault_cycles(router_faults));
  assign host_ready=cr[source_kind][0];
  assign host_response_valid=rv[source_kind][0];
  assign p_ack_error=0;
  assign response_valid=rv[1][1]&&allow_responses;
  assign response_data=rd[1];
  assign response_tag=rt[1][63:32];
  assign s_ready=cr[1][1];
  for(genvar m=0;m<4;m=m+1) begin: memories
    wire host_selected=host_mode&&(source_kind==m);
    wire dest_valid;
    wire [9:0] dest_address;
    wire [127:0] dest_data;
    wire [31:0] dest_tag;
    wire dest_ready;
    if(m==0) begin: no_destination
      assign dest_valid=0;assign dest_address=0;assign dest_data=0;assign dest_tag=0;assign dest_ready=1;
    end else begin: destination
      assign dest_valid=!host_mode&&p_valid[m-1];
      assign dest_address=p_address[10*(m-1)+:10];
      assign dest_data=p_data[128*(m-1)+:128];
      assign dest_tag=p_tag[32*(m-1)+:32];
      assign dest_ready=p_ack_ready[m-1]&&allow_responses;
      assign p_ready[m-1]=cr[m][0]&&!host_mode;
      assign p_ack_valid[m-1]=rv[m][0]&&!host_mode&&allow_responses;
      assign p_ack_tag[32*(m-1)+:32]=rt[m][31:0];
    end
    assign cv[m]={src_valid[m],(m==1?s_valid:1'b0),(host_selected?host_valid:dest_valid)};
    assign cw[m]=3'b001;
    assign ca[m]={src_address[10*m+:10],(m==1?s_address:10'b0),(host_selected?host_address:dest_address)};
    assign cd[m]={256'b0,(host_selected?host_data:dest_data)};
    assign ct[m]={src_tag[32*m+:32],(m==1?s_tag:32'b0),(host_selected?32'b0:dest_tag)};
    assign rr[m]={src_rsp_ready[m],(m==1?(response_ready&&allow_responses):1'b1),
      (host_selected?host_response_ready:dest_ready)};
    assign src_ready[m]=cr[m][2];
    assign src_rsp_valid[m]=rv[m][2];
    assign src_rsp_tag[32*m+:32]=rt[m][95:64];
    assign src_rsp_data[128*m+:128]=rd[m];
    native_s128_mux3 mux(.clk,.reset,.c_valid(cv[m]),.c_write(cw[m]),.c_address(ca[m]),
      .c_data(cd[m]),.c_tag(ct[m]),.c_ready(cr[m]),.c_response_valid(rv[m]),
      .c_response_ready(rr[m]),.c_response_data(rd[m]),.c_response_tag(rt[m]),
      .req_valid(nv[m]),.req_write(nw[m]),.req_address(na[m]),.req_data(nd[m]),
      .req_ready(nready[m]),.rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]),
      .owners_occupied(occupied[m]));
    local_s_base storage(.clk,.reset,.req_valid(nv[m]),.req_write(nw[m]),.req_addr(na[m]),
      .req_data(nd[m]),.req_ready(nready[m]),.rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]));
  end
"""
text = text[:begin] + wiring + text[end:]
text = text.replace("integer cycle,seed,trace_file,no_overlap,single_first;", "integer cycle,seed,trace_file,no_overlap,single_first,source_kind;")
text = text.replace("index*8+lane-256", "source_kind*1000+index*8+lane-256")
text = text.replace("single_first=0;", "single_first=0;source_kind=0;host_mode=1;bind_valid=0;bind_source=0;release_copy_valid=0;")
text = text.replace('    if($value$plusargs("SEED=%d",seed))', '    if($value$plusargs("SOURCE=%d",source_kind)) begin end\n    assert(source_kind>=0&&source_kind<4);\n    if($value$plusargs("SEED=%d",seed))')
text = text.replace("pause(3);reset=0;pause();initialize_source();trace_active=1;", """pause(3);reset=0;pause();initialize_source();host_mode=0;trace_active=1;
    bind_source=2'(source_kind);bind_valid=1;
    do @(posedge clk);while(!bind_ready);@(negedge clk);bind_valid=0;
    // An unaccepted host selector change must not redirect an active copy.
    bind_source=2'((source_kind+1)%4);
""")
text = text.replace("assert(live_slots==0&&quiescent", """assert(bound&&bound_source==2'(source_kind)&&bound_key==start_key&&router_drained&&router_faults==0)
      else $fatal(1,"copy source ownership changed before destination drain");
    release_copy_valid=1;do @(posedge clk);while(!release_copy_ready);@(negedge clk);release_copy_valid=0;pause();
    assert(!bound) else $fatal(1,"source lease not released");
    assert(live_slots==0&&quiescent""")
text = text.replace("PASS native_s_a_copy seed=%0d", "PASS native_s_source_copy seed=%0d source=%0d")
text = text.replace(",seed,cycle,source_reads", ",seed,source_kind,cycle,source_reads")
(HERE / "rtl/tb_native_s_source_copy.sv").write_text(text)
