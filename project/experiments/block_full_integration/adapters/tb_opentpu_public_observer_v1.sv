// Derived testbench only; original full selected DUT and memory model unchanged.
// Trace samples the public boundary in the active region at each rising edge,
// before DUT/model nonblocking updates. It records invalid payloads too; their
// raw values must not be confused with accepted transactions.
// No mid-flight reset, DRAM latency change, DUT retiming or new hardware is added.
`ifndef BLOCK_INTEGRATION_OPENTPU_TOP
`define BLOCK_INTEGRATION_OPENTPU_TOP otpu_asic_top
`endif
module tb_asic_baseline;
  localparam int D=32, WORDS=65536;
  logic clk=0, sys_rst=1, rst=1, dump=0, ld_start=0;
  logic [7:0][31:0] rinit='0;
  logic [31:0] ld_addr=32'h30000, ld_n;
  logic ld_busy, halted,error,wait_to,a_inval;
  logic [31:0] icount;
  logic a_req,a_we,a_rvalid,b_req,b_tag,b_we,b_par,b_rvalid,b_rtag;
  logic [D/4-1:0] b_wmask;
  logic [D*8-1:0] b_wdata,b_rdata;
  logic [31:0] a_addr,a_wdata,b_addr,sw_addr,sw_wdata;
  logic [255:0] a_rdata;
  logic [3:0] a_be,sw_be;
  logic a_rdy,b_rdy,sw_rdy,sw_req,rd_idle,wr_idle;
  logic ma_req,mb_req,msw_req;
  int stall_mode=0,cyc=0,accepted=0,stalls=0;
  int expect_wait_timeout=0,drain_cycles=0,stable_ticks=0;
  int accepted_write_requests=0;
  logic [7:0] rinit_present='0;
  logic [31:0] stopped_icount;
  int stopped_accepted,stopped_stalls;
  logic prev_a=0,prev_b=0,prev_sw=0;
  logic [68:0] prev_ap, prev_swp;
  logic [298:0] prev_bp;

  // Testbench-only deterministic backpressure. No DUT logic or reset changes.
  bit ready_seed_enabled=0;
  int unsigned ready_seed=0, ready_ticks=0;
  logic [31:0] ready_rng=32'h6d2b79f5;
  longint unsigned trace_cycle=0;
  integer trace_fd=0;
  string trace_path;
  function automatic logic [31:0] ready_next(input logic [31:0] x);
    logic [31:0] t;
    begin
      t=x^(x<<13); t=t^(t>>17); t=t^(t<<5);
      ready_next=t;
    end
  endfunction
  always @(negedge clk) begin
    if(ready_seed_enabled) begin
      ready_rng <= ready_next(ready_rng);
      ready_ticks <= ready_ticks+1;
    end
  end
  always #5 clk=~clk;
  assign a_rdy = ready_seed_enabled ? ((ready_rng[1:0]!=0) || ready_ticks[3:0]==4'hf) : (!stall_mode || (cyc%7 != 1 && cyc%7 != 2));
  assign b_rdy = ready_seed_enabled ? ((ready_rng[3:2]!=0) || ready_ticks[3:0]==4'hf) : (!stall_mode || (cyc%5 != 1 && cyc%5 != 2));
  assign sw_rdy= ready_seed_enabled ? ((ready_rng[5:4]!=0) || ready_ticks[3:0]==4'hf) : (!stall_mode || cyc%3 != 1);
  assign wr_idle=1'b1;
  assign ma_req=a_req && a_rdy;
  assign mb_req=b_req && b_rdy;
  assign msw_req=sw_req && sw_rdy;
  `BLOCK_INTEGRATION_OPENTPU_TOP #(.D(32),.MCOLS(2),.ACT_BLOCKS(32),.ACT_ROWS(2),
    .TMEM_WORDS(16384),.IMEM_WORDS(8192),.FIFO_DEPTH(64),.LANES(4),.WIN(16),
    .MXU_IMPL(2),.MXU_CL(16),.VPU_CL(1),.ULANES(4),.HAS_DSTEP(0),
    .TMEM_IMPL(1),.RPB(1),.WPB(1)) dut(
    .clk,.sys_rst,.rst,.rinit,.ld_start,.ld_addr,.ld_n,.ld_busy,
    .a_rdy,.b_rdy,.sw_rdy,.wr_idle,.rd_idle,
    .a_req,.a_we,.a_addr,.a_wdata,.a_be,.sw_req,.sw_addr,.sw_wdata,.sw_be,
    .a_rvalid,.a_rdata,.b_req,.b_tag,.b_we,.b_wmask,.b_wdata,.b_addr,.b_par,
    .b_rvalid,.b_rtag,.b_rdata,.halted,.error,.wait_to,.a_inval,.icount);
  otpu_dram #(.WORDS(WORDS),.D(D),.LAT(8),.SID(0)) mem(
    .clk,.a_req(ma_req),.a_we,.a_addr,.a_wdata,.a_be,.a_rvalid,.a_rdata,
    .sw_req(msw_req),.sw_addr,.sw_wdata,.sw_be,
    .b_req(mb_req),.b_tag,.b_we,.b_wmask,.b_wdata,.b_addr,.b_rvalid,.b_rtag,.b_rdata,
    .rd_idle,.dump);
  always @(posedge clk) begin
    if (!sys_rst) begin
      if(prev_a && (!a_req || {a_we,a_addr,a_wdata,a_be} !== prev_ap))
        $fatal(1,"A payload changed while stalled");
      if(prev_b && (!b_req || {b_tag,b_we,b_par,b_wmask,b_wdata,b_addr} !== prev_bp))
        $fatal(1,"B payload changed while stalled");
      if(prev_sw && (!sw_req || {1'b0,sw_addr,sw_wdata,sw_be} !== prev_swp))
        $fatal(1,"SW payload changed while stalled");
      prev_a <= a_req && !a_rdy;
      prev_b <= b_req && !b_rdy;
      prev_sw<= sw_req && !sw_rdy;
      prev_ap<= {a_we,a_addr,a_wdata,a_be};
      prev_bp<= {b_tag,b_we,b_par,b_wmask,b_wdata,b_addr};
      prev_swp<= {1'b0,sw_addr,sw_wdata,sw_be};
      accepted <= accepted + int'(ma_req)+int'(mb_req)+int'(msw_req);
      stalls <= stalls + int'(a_req&&!a_rdy)+int'(b_req&&!b_rdy)+int'(sw_req&&!sw_rdy);
    end
  end
  always @(posedge clk)
    if(!sys_rst) accepted_write_requests <= accepted_write_requests
      +int'(ma_req && a_we)+int'(mb_req && b_we)+int'(msw_req);
  always @(posedge clk) begin
    if(trace_fd==0) $fatal(1,"trace file was not opened before first clock");
    if(trace_cycle>=250000) $fatal(1,"trace bound exceeded");
    $fwrite(trace_fd,"%0d\t%0t\t%0b\t%0b\t%0b\t%064h\t%0b\t%08h\t%08h\t%0b\t%0b\t%0b\t%0b\t%0b\t%0b\t%0b\t%0b\t%08h\t%08h\t%01h\t%0b\t%08h\t%08h\t%01h\t%0b\t%064h\t%0b\t%0b\t%0b\t%02h\t%064h\t%08h\t%0b\t%0b\t%0b\t%064h\t%0b\t%0b\t%0b\t%0b\t%08h\n",
      trace_cycle, $time, clk, sys_rst, rst, rinit, ld_start, ld_addr, ld_n, ld_busy, a_rdy, b_rdy, sw_rdy, wr_idle, rd_idle, a_req, a_we, a_addr, a_wdata, a_be, sw_req, sw_addr, sw_wdata, sw_be, a_rvalid, a_rdata, b_req, b_tag, b_we, b_wmask, b_wdata, b_addr, b_par, b_rvalid, b_rtag, b_rdata, halted, error, wait_to, a_inval, icount);
    trace_cycle <= trace_cycle+1;
  end
  initial begin
    if(!$value$plusargs("n=%d",ld_n)) $fatal(1,"missing instruction count");
    void'($value$plusargs("stall=%d",stall_mode));
    ready_seed_enabled=$value$plusargs("ready_seed=%d",ready_seed);
    if(ready_seed_enabled && ready_seed>2) $fatal(1,"ready_seed must be0,1,or2");
    if(ready_seed_enabled && stall_mode!=0) $fatal(1,"ready_seed and legacy stall mode cannot be combined");
    ready_rng=32'h6d2b79f5 ^ ready_seed;
    if(!$value$plusargs("trace_path=%s",trace_path)) trace_path="public_trace.tsv";
    trace_fd=$fopen(trace_path,"w");
    if(trace_fd==0) $fatal(1,"cannot open public trace");
    $fwrite(trace_fd,"cycle\ttime\tclk\tsys_rst\trst\trinit\tld_start\tld_addr\tld_n\tld_busy\ta_rdy\tb_rdy\tsw_rdy\twr_idle\trd_idle\ta_req\ta_we\ta_addr\ta_wdata\ta_be\tsw_req\tsw_addr\tsw_wdata\tsw_be\ta_rvalid\ta_rdata\tb_req\tb_tag\tb_we\tb_wmask\tb_wdata\tb_addr\tb_par\tb_rvalid\tb_rtag\tb_rdata\thalted\terror\twait_to\ta_inval\ticount\n");
    $display("SIM_READY_MODE seeded=%0d seed=%0d legacy_stall=%0d trace=%s",ready_seed_enabled,ready_seed,stall_mode,trace_path);
    void'($value$plusargs("expect_wait_timeout=%d",expect_wait_timeout));
    if(expect_wait_timeout!=0 && expect_wait_timeout!=1)
      $fatal(1,"expect_wait_timeout must be0 or1");
    rinit_present[0]=$value$plusargs("rinit8=%h",rinit[0]);
    rinit_present[1]=$value$plusargs("rinit9=%h",rinit[1]);
    rinit_present[2]=$value$plusargs("rinit10=%h",rinit[2]);
    rinit_present[3]=$value$plusargs("rinit11=%h",rinit[3]);
    rinit_present[4]=$value$plusargs("rinit12=%h",rinit[4]);
    rinit_present[5]=$value$plusargs("rinit13=%h",rinit[5]);
    rinit_present[6]=$value$plusargs("rinit14=%h",rinit[6]);
    rinit_present[7]=$value$plusargs("rinit15=%h",rinit[7]);
    if(rinit_present!='0 && rinit_present!=8'hff)
      $fatal(1,"rinit must provide all8 arguments or none");
    $display("SIM_INIT expected_timeout=%0d rinit_present=%02h rinit8=%08h rinit9=%08h rinit10=%08h rinit11=%08h rinit12=%08h rinit13=%08h rinit14=%08h rinit15=%08h",
      expect_wait_timeout,rinit_present,rinit[0],rinit[1],rinit[2],rinit[3],rinit[4],rinit[5],rinit[6],rinit[7]);
    repeat(5) @(negedge clk);
    sys_rst=0;
    repeat(3) @(negedge clk);
    ld_start=1;
    @(negedge clk); ld_start=0;
    while(ld_busy && cyc<200000) begin @(negedge clk);cyc++;end
    if(ld_busy) $fatal(1,"loader timeout");
    repeat(4) @(negedge clk);
    rst=0;
    while(!halted && !error && cyc<200000) begin @(negedge clk);cyc++;end
    if(expect_wait_timeout) begin
      if(!error || !wait_to)
        $fatal(1,"expected WAIT timeout missing cycles=%0d error=%b wait_to=%b halted=%b",cyc,error,wait_to,halted);
      // Actual slice to_q pipeline and wr_idle must settle before halted.
      // A previous read may finish past the programmed WAIT deadline.
      while((!halted || !rd_idle || a_req || sw_req || b_req) && drain_cycles<100) begin
        @(negedge clk);cyc++;drain_cycles++;
        if(!error || !wait_to) $fatal(1,"timeout status did not remain sticky while draining");
      end
      if(!halted || !rd_idle || a_req || sw_req || b_req)
        $fatal(1,"timeout failed bounded halt/drain");
      stopped_icount=icount;stopped_accepted=accepted;stopped_stalls=stalls;
      repeat(20) begin
        @(negedge clk);stable_ticks++;
        if(!error || !wait_to || !halted || !rd_idle || a_req || sw_req || b_req)
          $fatal(1,"timeout did not remain halted/drained");
        if(icount!==stopped_icount || accepted!=stopped_accepted || stalls!=stopped_stalls)
          $fatal(1,"timeout counter changed after quiescence");
      end
      $display("SIM_EXPECTED_TIMEOUT cycles=%0d icount=%0d accepted=%0d stalls=%0d error=%0b wait_to=%0b halted=%0b rd_idle=%0b drain_cycles=%0d stable_ticks=%0d",
        cyc,icount,accepted,stalls,error,wait_to,halted,rd_idle,drain_cycles,stable_ticks);
    end else begin
      if(error || wait_to || !halted) $fatal(1,"execution failure cycles=%0d error=%b",cyc,error);
      repeat(20) @(negedge clk);
      if(!rd_idle || a_req || sw_req || b_req) $fatal(1,"external interface did not drain");
    end
    dump=1;
    @(negedge clk);dump=0;
    if(!expect_wait_timeout) $display("SIM_COMPLETE cycles=%0d icount=%0d accepted=%0d stalls=%0d",cyc,icount,accepted,stalls);
    $display("SIM_PUBLIC_WRITES count=%0d",accepted_write_requests);
    $finish;
  end
  final begin
    if(trace_fd!=0) begin
      $fflush(trace_fd);
      $fclose(trace_fd);
      $display("SIM_TRACE_CLOSED rows=%0d path=%s",trace_cycle,trace_path);
    end
  end
endmodule
