 reg clk=0,reset=1;always #5 clk=~clk;
 integer ticks=0;always @(posedge clk)ticks=ticks+1;
 wire nv,nready,ndone,nerror,nsat,ntake;wire [39:0] nmeta;wire [19:0] nsrc;wire [9:0] ndst;wire [127:0] nresult;
 reg ev=0,estore=0,edirect=0,etake=0;reg [1:0] esources=0;reg [3:0] eop=0;reg [4:0] eshift=0;
 reg [29:0] esrc=0;reg [9:0] edst=0;wire eready,edone,eerror,esat;wire [127:0] edata;
 reg direct_valid=0,direct_abort=0;reg [127:0] direct_data=0;wire direct_ready;
 reg [1:0] io_v=0,io_w=0,io_take=0;reg [19:0] io_addr=0;reg [255:0] io_data=0;
 wire [1:0] io_ready,io_rsp;wire [255:0] io_result;
 pu_u_group #(.NEXP_BATCH(1),.NEXP_DIRECT(1),.NEXP_DIRECT_LANES(4),.NEXP_S16(1),.E_PIPELINE(PIPE),.E_QUEUE_DEPTH(DEPTH)) dut(
  .clk,.reset,.n_cmd_valid(nv),.n_cmd_store(1'b1),.n_cmd_direct(1'b0),.n_done_ready(ntake),.n_cmd_ready(nready),
  .n_done_valid(ndone),.n_done_error(nerror),.n_done_saturated(nsat),.n_cmd_meta(nmeta),.n_cmd_sources(2'd1),.n_cmd_src(nsrc),.n_cmd_dst(ndst),.n_done_data(nresult),
  .n_to_e_valid(),.n_to_e_ready(1'b1),.n_to_e_data(),
  .e_cmd_valid(ev),.e_cmd_store(estore),.e_cmd_direct_a(edirect),.e_done_ready(etake),.e_cmd_ready(eready),.e_done_valid(edone),.e_done_error(eerror),.e_done_saturated(esat),
  .e_cmd_sources(esources),.e_cmd_op(eop),.e_cmd_shift(eshift),.e_cmd_src(esrc),.e_cmd_dst(edst),.e_done_data(edata),
  .e_direct_a_valid(direct_valid),.e_direct_a_abort(direct_abort),.e_direct_a_ready(direct_ready),.e_direct_a_data(direct_data),
  .io_req_valid(io_v),.io_req_write(io_w),.io_rsp_ready(io_take),.io_req_addr(io_addr),.io_req_data(io_data),
  .io_req_ready(io_ready),.io_rsp_valid(io_rsp),.io_rsp_data(io_result));
 task automatic access(input integer port,input bit wr,input [9:0] address,input [127:0] data,input integer stall,output [127:0] got);
  integer guard;
  begin
   @(negedge clk);io_v[port]=1;io_w[port]=wr;io_addr[10*port+:10]=address;io_data[128*port+:128]=data;io_take[port]=0;guard=0;
   do begin @(posedge clk);guard++;if(guard>4096)$fatal(1,"IO request timeout");end while(!io_ready[port]);
   @(negedge clk);io_v[port]=0;repeat(stall)@(negedge clk);io_take[port]=1;guard=0;
   do begin @(posedge clk);guard++;if(guard>4096)$fatal(1,"IO response timeout");end while(!io_rsp[port]);
   got=io_result[128*port+:128];@(negedge clk);io_take[port]=0;
  end
 endtask
 initial begin repeat(3000000)@(posedge clk);$fatal(1,"global test timeout");end
