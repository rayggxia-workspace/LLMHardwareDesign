// Issue151 W4 bounded H8/I8 F16, parentfebc042 / native7078786.
// New top only: previous F8/W3 and all original leaves remain unchanged.
// RMS8 variable S16 gamma -> S16 wide-A FFN8 -> original S16 residual.
// Fixed 17-beat frame/layout; no MEM, cross-island ACK or model-quality claim.
module block_w4_f16_top(
 input wire clk,reset,abort,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 output wire input_stored,input wire start_valid,output wire start_ready,
 output wire busy,output wire done_valid,input wire done_ready,
 output wire done_error,done_saturated,
 output wire out_valid,input wire out_ready,
 output wire [127:0] out_data,output wire [9:0] out_index,output wire out_last
);
 localparam [5:0] IDLE=0,INPUT_REQ=1,INPUT_RSP=2,LOCAL_REQ=3,LOCAL_RSP=4,
  M_CMD=5,M_RSP=6,LOAD_CMD=7,LOAD_RSP=8,E_REQ=9,E_RSP=10,
  G_REQ=11,G_RSP=12,T_BEGIN=13,T_WRITE=14,T_COMMIT=15,
  T_DRAIN=16,T_RELEASE=17,DONE=18,N_REQ=19,N_RSP=20;
 localparam [1:0] OWNER_LOCAL=0,OWNER_E=1,OWNER_G=2,OWNER_N=3;
 localparam [2:0] L_SAVE_X=0,L_M_SAVE=1,L_MID_PAD=2,L_FINAL_READ=3,
  L_NORM_READ=5,L_NORM_WRITE=6;
 localparam [2:0] MC_CLEAR=0,MC_SCALE=1,MC_EXEC=2,MC_READ0=3,MC_READ1=4;
 reg [5:0] state;
 reg [1:0] owner,projection,pad_index;
 reg [2:0] local_tag;
 reg [2:0] m_phase;
 reg [4:0] input_index;
 reg frame_active,frame_stored,running,error_latched,saturation_latched;
 reg internal_reset,e_final,local_write;
 reg [9:0] local_addr;
 // Historical observation name retained; x_unpacked now stores all eight
 // original S16 lanes verbatim, without S8 unpack or residual rescaling.
 reg [127:0] held_data,x_unpacked;
 reg [63:0] m_low_half;
 wire leaf_reset;
 wire input_fire,start_fire;
 // Named constants are finite TB fault/stall points, not runtime host fields.
 wire permit_s_req=1'b1,permit_s_rsp=1'b1;
 wire permit_m_cmd=1'b1,permit_m_rsp=1'b1,permit_load=1'b1;
 wire permit_e_req=1'b1,permit_e_rsp=1'b1;
 wire permit_g_req=1'b1,permit_g_rsp=1'b1;
 wire permit_n_req=1'b1,permit_n_rsp=1'b1;
 wire h_req_valid,h_req_ready,h_req_write,h_rsp_valid,h_rsp_ready,h_rsp_error;
 wire [9:0] h_req_addr;
 wire [127:0] h_req_data,h_rsp_data;
 wire local_req_valid,local_rsp_ready;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_s_take;
 wire [9:0] s_addr;
 wire [127:0] s_din,s_dout;
 wire e_req_valid,e_req_ready,e_rsp_valid,e_rsp_ready,e_rsp_error,e_rsp_saturated;
 wire g_req_valid,g_req_ready,g_rsp_valid,g_rsp_ready,g_rsp_error,g_rsp_saturated;
 wire e_mem_req_valid,e_mem_req_ready,e_mem_req_write,e_mem_rsp_valid,e_mem_rsp_ready,e_mem_rsp_error;
 wire [9:0] e_mem_req_addr;
 wire [127:0] e_mem_req_data,e_mem_rsp_data;
 wire g_mem_req_valid,g_mem_req_ready,g_mem_req_write,g_mem_rsp_valid,g_mem_rsp_ready,g_mem_rsp_error;
 wire [9:0] g_mem_req_addr;
 wire [127:0] g_mem_req_data,g_mem_rsp_data;
 wire n_req_valid,n_req_ready,n_rsp_valid,n_rsp_ready,n_rsp_error,n_rsp_saturated,n_ctrl_busy;
 wire n_mem_req_valid,n_mem_req_ready,n_mem_req_write,n_mem_rsp_valid,n_mem_rsp_ready,n_mem_rsp_error;
 wire [9:0] n_mem_req_addr;
 wire [127:0] n_mem_req_data,n_mem_rsp_data;
 wire n_cmd_valid,n_cmd_ready,n_native_rsp_valid,n_native_rsp_ready,n_native_rsp_error,n_native_rsp_saturated,n_busy;
 wire [3:0] n_cmd_op,n_cmd_count;
 wire [31:0] n_cmd_param;
 wire [127:0] n_cmd_data,n_cmd_aux,n_native_rsp_data;
 wire e_in_valid,e_in_ready,e_out_valid,e_out_ready,e_out_error,e_out_saturated;
 wire [3:0] e_in_op;
 wire [4:0] e_in_shift;
 wire [127:0] e_in_a,e_in_b,e_in_c,e_out_data;
 wire g_in_valid,g_in_ready,g_in_gated,g_out_valid,g_out_ready,g_out_error,g_out_saturated;
 wire [2:0] g_in_fn;
 wire [31:0] g_in_x,g_in_gate,g_out_data;
 wire load_valid,load_ready,load_done_valid,load_done_take,load_done_error,loader_busy;
 wire a_valid,a_ready,a_bank,a_wide,b_valid,b_ready,b_bank,b_wide,b_half;
 wire [2:0] a_row;
 wire [1:0] a_tile,b_tile;
 wire [127:0] a_data;
 wire [511:0] b_data;
 wire m_cmd_valid,m_cmd_ready,m_rsp_valid,m_rsp_ready,m_rsp_error,m_rsp_saturated,m_busy;
 wire [3:0] m_cmd_op;
 wire [5:0] m_cmd_index;
 wire [63:0] m_cmd_data;
 wire [127:0] m_rsp_data;
 wire t_begin_ready,t_write_ready,t_commit_ready,t_release_ready,t_read_valid,t_read_last;
 wire [9:0] t_read_index,t_word_count;
 wire [127:0] t_read_data;
 wire t_busy,t_sealed,t_committed,t_protocol_error,t_read_take;
 wire [1:0] t_owner;
 wire [31:0] t_generation;
 wire [2:0] t_state;

 assign leaf_reset=reset||abort||internal_reset;
 assign in_ready=!leaf_reset&&state==IDLE&&!frame_stored&&!running;
 assign input_stored=!reset&&!abort&&frame_stored;
 assign start_ready=!leaf_reset&&state==IDLE&&frame_stored&&!running;
 assign input_fire=in_valid&&in_ready;
 assign start_fire=start_valid&&start_ready;
 assign busy=!reset&&(frame_active||running||state==DONE);
 assign done_valid=!reset&&state==DONE;
 assign done_error=error_latched;
 assign done_saturated=saturation_latched;

 // Beat0 is X/S16, beats1..3 are real zero padding, beats4..15 weights,
 // beat16 gamma/S16. Gamma uses the separate S475 address below.
 function automatic [127:0] canonical_input;
  input [4:0] index;input [127:0] data;
  begin
   if(index==0)canonical_input=data;
   else if(index<4)canonical_input=0;
   else canonical_input=data;
  end
 endfunction
 function automatic [63:0] pack_m_four;
  input [127:0] data;
  begin pack_m_four={data[111:96],data[79:64],data[47:32],data[15:0]};end
 endfunction
 // Exactly one ordinary-S helper. Owner stays selected through an entire
 // E/G/N service, including its destination write ACK and response retirement.
 assign local_req_valid=state==INPUT_REQ||state==LOCAL_REQ;
 assign local_rsp_ready=state==INPUT_RSP||state==LOCAL_RSP;
 assign h_req_valid=!leaf_reset&&permit_s_req&&
  (owner==OWNER_E?e_mem_req_valid:owner==OWNER_G?g_mem_req_valid:owner==OWNER_N?n_mem_req_valid:local_req_valid);
 assign h_req_write=owner==OWNER_E?e_mem_req_write:owner==OWNER_G?g_mem_req_write:owner==OWNER_N?n_mem_req_write:
  (state==INPUT_REQ?1'b1:local_write);
 assign h_req_addr=owner==OWNER_E?e_mem_req_addr:owner==OWNER_G?g_mem_req_addr:owner==OWNER_N?n_mem_req_addr:
  (state==INPUT_REQ ? (input_index==5'd16 ? 10'd475 : 10'd448+{5'd0,input_index}) : local_addr);
 assign h_req_data=owner==OWNER_E?e_mem_req_data:owner==OWNER_G?g_mem_req_data:owner==OWNER_N?n_mem_req_data:held_data;
 assign h_rsp_ready=!leaf_reset&&(owner==OWNER_E?e_mem_rsp_ready:owner==OWNER_G?g_mem_rsp_ready:owner==OWNER_N?n_mem_rsp_ready:local_rsp_ready);
 assign e_mem_req_ready=!leaf_reset&&permit_s_req&&owner==OWNER_E&&h_req_ready;
 assign g_mem_req_ready=!leaf_reset&&permit_s_req&&owner==OWNER_G&&h_req_ready;
 assign n_mem_req_ready=!leaf_reset&&permit_s_req&&owner==OWNER_N&&h_req_ready;
 assign e_mem_rsp_valid=!leaf_reset&&owner==OWNER_E&&h_rsp_valid;
 assign g_mem_rsp_valid=!leaf_reset&&owner==OWNER_G&&h_rsp_valid;
 assign n_mem_rsp_valid=!leaf_reset&&owner==OWNER_N&&h_rsp_valid;
 assign e_mem_rsp_data=h_rsp_data;assign g_mem_rsp_data=h_rsp_data;
 assign e_mem_rsp_error=h_rsp_error;assign g_mem_rsp_error=h_rsp_error;
 assign n_mem_rsp_data=h_rsp_data;assign n_mem_rsp_error=h_rsp_error;
 assign s_take=helper_s_take&&permit_s_rsp;
 block_p2_s_ctrl u_s_ctrl(
  .clk(clk),.resetn(!leaf_reset),.req_valid(h_req_valid),.req_ready(h_req_ready),
  .req_write(h_req_write),.req_addr(h_req_addr),.req_data(h_req_data),
  .rsp_valid(h_rsp_valid),.rsp_ready(h_rsp_ready),.rsp_data(h_rsp_data),.rsp_error(h_rsp_error),
  .s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_ready(s_ready),
  .s_rsp_valid(s_valid&&permit_s_rsp),.s_rsp_ready(helper_s_take),.s_dout(s_dout));

 assign n_req_valid=!leaf_reset&&state==N_REQ&&permit_n_req;
 assign n_rsp_ready=!leaf_reset&&state==N_RSP&&permit_n_rsp;
 block_w4_n_ctrl u_n_ctrl(
  .clk(clk),.reset(leaf_reset),.req_valid(n_req_valid),.req_ready(n_req_ready),
  .req_mode(2'd1),.req_count(16'd8),.req_epsilon(32'd1),
  .req_src_addr(10'd466),.req_gamma_addr(10'd475),.req_exp_addr(10'd0),.req_dst_addr(10'd474),
  .rsp_valid(n_rsp_valid),.rsp_ready(n_rsp_ready),.rsp_error(n_rsp_error),.rsp_saturated(n_rsp_saturated),.busy(n_ctrl_busy),
  .mem_req_valid(n_mem_req_valid),.mem_req_ready(n_mem_req_ready),.mem_req_write(n_mem_req_write),
  .mem_req_addr(n_mem_req_addr),.mem_req_data(n_mem_req_data),.mem_rsp_valid(n_mem_rsp_valid),
  .mem_rsp_ready(n_mem_rsp_ready),.mem_rsp_data(n_mem_rsp_data),.mem_rsp_error(n_mem_rsp_error),
  .n_cmd_valid(n_cmd_valid),.n_cmd_ready(n_cmd_ready),.n_cmd_op(n_cmd_op),.n_cmd_count(n_cmd_count),
  .n_cmd_param(n_cmd_param),.n_cmd_data(n_cmd_data),.n_cmd_aux(n_cmd_aux),
  .n_rsp_valid(n_native_rsp_valid),.n_rsp_ready(n_native_rsp_ready),.n_rsp_data(n_native_rsp_data),
  .n_rsp_error(n_native_rsp_error),.n_rsp_saturated(n_native_rsp_saturated));
 block_v2_n u_n(.clk(clk),.reset(leaf_reset),.cmd_valid(n_cmd_valid),.cmd_ready(n_cmd_ready),
  .cmd_op(n_cmd_op),.cmd_count(n_cmd_count),.cmd_param(n_cmd_param),.cmd_data(n_cmd_data),.cmd_aux(n_cmd_aux),
  .rsp_valid(n_native_rsp_valid),.rsp_ready(n_native_rsp_ready),.rsp_data(n_native_rsp_data),
  .rsp_error(n_native_rsp_error),.rsp_saturated(n_native_rsp_saturated),.busy(n_busy));

 assign e_req_valid=!leaf_reset&&state==E_REQ&&permit_e_req;
 assign e_rsp_ready=!leaf_reset&&state==E_RSP&&permit_e_rsp;
 block_w3_e_ctrl u_e_ctrl(
  .clk(clk),.reset(leaf_reset),.req_valid(e_req_valid),.req_ready(e_req_ready),
  .req_op(e_final?4'd0:4'd7),.req_shift(5'd0),.req_count(4'd8),
  .req_src_a(e_final?10'd472:10'd466),.req_src_b(10'd467),.req_src_c(10'd0),
  .req_dst(e_final?10'd473:10'd467),.rsp_valid(e_rsp_valid),.rsp_ready(e_rsp_ready),
  .rsp_error(e_rsp_error),.rsp_saturated(e_rsp_saturated),
  .mem_req_valid(e_mem_req_valid),.mem_req_ready(e_mem_req_ready),.mem_req_write(e_mem_req_write),
  .mem_req_addr(e_mem_req_addr),.mem_req_data(e_mem_req_data),.mem_rsp_valid(e_mem_rsp_valid),
  .mem_rsp_ready(e_mem_rsp_ready),.mem_rsp_data(e_mem_rsp_data),.mem_rsp_error(e_mem_rsp_error),
  .e_in_valid(e_in_valid),.e_in_ready(e_in_ready),.e_in_op(e_in_op),.e_in_shift(e_in_shift),
  .e_in_a(e_in_a),.e_in_b(e_in_b),.e_in_c(e_in_c),.e_out_valid(e_out_valid),
  .e_out_ready(e_out_ready),.e_out_data(e_out_data),.e_out_error(e_out_error),.e_out_saturated(e_out_saturated));
 block_v2_e u_e(.clk(clk),.reset(leaf_reset),.in_valid(e_in_valid),.in_ready(e_in_ready),
  .in_op(e_in_op),.in_shift(e_in_shift),.in_a(e_in_a),.in_b(e_in_b),.in_c(e_in_c),
  .out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),.out_error(e_out_error),.out_saturated(e_out_saturated));
 assign g_req_valid=!leaf_reset&&state==G_REQ&&permit_g_req;
 assign g_rsp_ready=!leaf_reset&&state==G_RSP&&permit_g_rsp;
 block_w3_g_ctrl u_g_ctrl(
  .clk(clk),.reset(leaf_reset),.req_valid(g_req_valid),.req_ready(g_req_ready),
  .req_fn(3'd0),.req_gated(1'b1),.req_count(4'd8),.req_src_a(10'd464),.req_src_b(10'd465),.req_dst(10'd468),
  .rsp_valid(g_rsp_valid),.rsp_ready(g_rsp_ready),.rsp_error(g_rsp_error),.rsp_saturated(g_rsp_saturated),
  .mem_req_valid(g_mem_req_valid),.mem_req_ready(g_mem_req_ready),.mem_req_write(g_mem_req_write),
  .mem_req_addr(g_mem_req_addr),.mem_req_data(g_mem_req_data),.mem_rsp_valid(g_mem_rsp_valid),
  .mem_rsp_ready(g_mem_rsp_ready),.mem_rsp_data(g_mem_rsp_data),.mem_rsp_error(g_mem_rsp_error),
  .g_in_valid(g_in_valid),.g_in_ready(g_in_ready),.g_in_fn(g_in_fn),.g_in_gated(g_in_gated),
  .g_in_x(g_in_x),.g_in_gate(g_in_gate),.g_out_valid(g_out_valid),.g_out_ready(g_out_ready),
  .g_out_data(g_out_data),.g_out_error(g_out_error),.g_out_saturated(g_out_saturated));
 block_v2_g u_g(.clk(clk),.reset(leaf_reset),.in_valid(g_in_valid),.in_ready(g_in_ready),
  .in_fn(g_in_fn),.in_gated(g_in_gated),.in_x(g_in_x),.in_gate(g_in_gate),
  .out_valid(g_out_valid),.out_ready(g_out_ready),.out_data(g_out_data),.out_error(g_out_error),.out_saturated(g_out_saturated));

 assign load_valid=!leaf_reset&&state==LOAD_CMD&&permit_load;
 assign load_done_take=!leaf_reset&&state==LOAD_RSP;
 block_feed_s_macro u_s(
  .clk(clk),.reset(leaf_reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),
  .ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),
  .load_valid(load_valid),.load_ready(load_ready),.load_bank(1'b0),.load_rows(4'd1),.load_tiles(3'd1),
  .load_a_wide(1'b1),.load_b_wide(1'b0),.load_reuse_b(1'b0),
  .load_a_base(projection==2?10'd468:10'd448),
  .load_b_base(projection==0?10'd452:projection==1?10'd456:10'd460),
  .done_valid(load_done_valid),.done_take(load_done_take),.done_error(load_done_error),.busy(loader_busy),
  .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data));
 assign m_cmd_valid=!leaf_reset&&state==M_CMD&&permit_m_cmd;
 assign m_rsp_ready=!leaf_reset&&state==M_RSP&&permit_m_rsp;
 assign m_cmd_op=m_phase==MC_CLEAR?4'd6:m_phase==MC_SCALE?4'd4:m_phase==MC_EXEC?4'd10:4'd5;
 assign m_cmd_index=m_phase==MC_READ1?6'd1:6'd0;
 assign m_cmd_data=m_phase==MC_SCALE?64'd1:m_phase==MC_EXEC?64'h9885:
  (m_phase==MC_READ0||m_phase==MC_READ1)?64'h107:64'd0;
 block_v2_m u_m(
  .clk(clk),.reset(leaf_reset),.a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data),
  .cmd_valid(m_cmd_valid),.cmd_ready(m_cmd_ready),.cmd_op(m_cmd_op),.cmd_index(m_cmd_index),.cmd_data(m_cmd_data),
  .rsp_valid(m_rsp_valid),.rsp_ready(m_rsp_ready),.rsp_data(m_rsp_data),.rsp_error(m_rsp_error),.rsp_saturated(m_rsp_saturated),.busy(m_busy));

 assign t_read_take=!leaf_reset&&state==T_DRAIN&&out_ready;
 assign out_valid=!leaf_reset&&state==T_DRAIN&&t_read_valid;
 assign out_data=t_read_data;assign out_index=t_read_index;assign out_last=out_valid&&t_read_last;
 transaction6k u_t(
  .clk(clk),.reset(leaf_reset),.begin_valid(!leaf_reset&&state==T_BEGIN),.begin_ready(t_begin_ready),
  .begin_owner(2'd0),.begin_generation(32'd1),.begin_words(10'd1),
  .write_valid(!leaf_reset&&state==T_WRITE),.write_ready(t_write_ready),.write_index(10'd0),.write_data(held_data),
  .commit_valid(!leaf_reset&&state==T_COMMIT),.commit_ready(t_commit_ready),.revoke_valid(1'b0),.revoke_ready(),
  .read_valid(t_read_valid),.read_take(t_read_take),.read_index(t_read_index),.read_data(t_read_data),.read_last(t_read_last),
  .owner(t_owner),.generation(t_generation),.word_count(t_word_count),.release_valid(!leaf_reset&&state==T_RELEASE),.release_ready(t_release_ready),
  .busy(t_busy),.sealed(t_sealed),.committed(t_committed),.protocol_error(t_protocol_error),.debug_state(t_state));

 task automatic empty_frame;
  begin
   state<=IDLE;owner<=OWNER_LOCAL;input_index<=0;frame_active<=0;frame_stored<=0;running<=0;
   error_latched<=0;saturation_latched<=0;
  end
 endtask
 task automatic fail_job;
  begin
   state<=DONE;owner<=OWNER_LOCAL;input_index<=0;frame_active<=0;frame_stored<=0;running<=0;
   error_latched<=1;internal_reset<=1;
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   empty_frame();projection<=0;local_tag<=0;pad_index<=0;m_phase<=MC_CLEAR;
   held_data<=0;x_unpacked<=0;m_low_half<=0;internal_reset<=0;e_final<=0;local_write<=0;local_addr<=0;
  end else begin
   internal_reset<=0;
   if(abort)begin
    // Existing DONE survives abort; ready consumes it exactly once.
    frame_active<=0;frame_stored<=0;input_index<=0;
    if(state==DONE)begin if(done_ready)empty_frame();end
    else if(running)fail_job();
    else empty_frame();
   end else if(running&&t_protocol_error)fail_job();
   else case(state)
    IDLE:if(input_fire)begin
     frame_active<=1;held_data<=canonical_input(input_index,in_data);state<=INPUT_REQ;
     if(input_index==0)x_unpacked<=in_data;
    end else if(start_fire)begin
     running<=1;error_latched<=0;saturation_latched<=0;owner<=OWNER_LOCAL;
     local_tag<=L_SAVE_X;local_write<=1;local_addr<=10'd466;held_data<=x_unpacked;state<=LOCAL_REQ;
    end
    INPUT_REQ:if(h_req_valid&&h_req_ready)state<=INPUT_RSP;
    INPUT_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)begin empty_frame();internal_reset<=1;end
     else begin
      state<=IDLE;
      if(input_index==5'd16)frame_stored<=1;else input_index<=input_index+1'b1;
     end
    end
    LOCAL_REQ:if(h_req_valid&&h_req_ready)state<=LOCAL_RSP;
    LOCAL_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();
     else case(local_tag)
      // Gamma already passed the seventeenth ingress write ACK at S475.
      // Do not replace it with a literal unity-gamma write after start.
      L_SAVE_X:begin owner<=OWNER_N;state<=N_REQ;end
      L_NORM_READ:begin
       held_data<=h_rsp_data;local_tag<=L_NORM_WRITE;local_write<=1;local_addr<=10'd448;state<=LOCAL_REQ;
      end
      L_NORM_WRITE:begin owner<=OWNER_E;e_final<=0;state<=E_REQ;end
      L_M_SAVE:if(projection==0)begin projection<=1;m_phase<=MC_CLEAR;state<=M_CMD;end
       else if(projection==1)begin owner<=OWNER_G;state<=G_REQ;end
       else begin owner<=OWNER_E;e_final<=1;state<=E_REQ;end
      L_MID_PAD:if(pad_index==2)begin projection<=2;m_phase<=MC_CLEAR;state<=M_CMD;end
       else begin pad_index<=pad_index+1'b1;local_addr<=local_addr+1'b1;state<=LOCAL_REQ;end
      L_FINAL_READ:begin held_data<=h_rsp_data;state<=T_BEGIN;end
      default:fail_job();
     endcase
    end
    N_REQ:if(n_req_valid&&n_req_ready)state<=N_RSP;
    N_RSP:if(n_rsp_valid&&n_rsp_ready)begin
     saturation_latched<=saturation_latched||n_rsp_saturated;
     if(n_rsp_error)fail_job();
     else begin owner<=OWNER_LOCAL;local_tag<=L_NORM_READ;local_write<=0;local_addr<=10'd474;state<=LOCAL_REQ;end
    end
    E_REQ:if(e_req_valid&&e_req_ready)state<=E_RSP;
    E_RSP:if(e_rsp_valid&&e_rsp_ready)begin
     saturation_latched<=saturation_latched||e_rsp_saturated;
     if(e_rsp_error)fail_job();
     else begin
      owner<=OWNER_LOCAL;
      if(e_final)begin local_tag<=L_FINAL_READ;local_write<=0;local_addr<=10'd473;state<=LOCAL_REQ;end
      else begin projection<=0;m_phase<=MC_CLEAR;state<=M_CMD;end
     end
    end
    G_REQ:if(g_req_valid&&g_req_ready)state<=G_RSP;
    G_RSP:if(g_rsp_valid&&g_rsp_ready)begin
     saturation_latched<=saturation_latched||g_rsp_saturated;
     if(g_rsp_error)fail_job();
     else begin owner<=OWNER_LOCAL;local_tag<=L_MID_PAD;pad_index<=0;local_write<=1;local_addr<=10'd469;held_data<=0;state<=LOCAL_REQ;end
    end
    M_CMD:if(m_cmd_valid&&m_cmd_ready)state<=M_RSP;
    M_RSP:if(m_rsp_valid&&m_rsp_ready)begin
     saturation_latched<=saturation_latched||m_rsp_saturated;
     if(m_rsp_error||(m_phase==MC_EXEC&&m_rsp_data[7:0]!=0))fail_job();
     else case(m_phase)
      MC_CLEAR:begin m_phase<=MC_SCALE;state<=M_CMD;end
      MC_SCALE:state<=LOAD_CMD;
      MC_EXEC:begin m_phase<=MC_READ0;state<=M_CMD;end
      MC_READ0:begin m_low_half<=pack_m_four(m_rsp_data);m_phase<=MC_READ1;state<=M_CMD;end
      MC_READ1:begin held_data<={pack_m_four(m_rsp_data),m_low_half};local_tag<=L_M_SAVE;local_write<=1;
       local_addr<=projection==0?10'd464:projection==1?10'd465:10'd472;state<=LOCAL_REQ;end
      default:fail_job();
     endcase
    end
    LOAD_CMD:if(load_valid&&load_ready)state<=LOAD_RSP;
    LOAD_RSP:if(load_done_valid&&load_done_take)begin
     if(load_done_error)fail_job();else begin m_phase<=MC_EXEC;state<=M_CMD;end
    end
    T_BEGIN:if(t_begin_ready)state<=T_WRITE;
    T_WRITE:if(t_write_ready)state<=T_COMMIT;
    T_COMMIT:if(t_commit_ready)state<=T_DRAIN;
    T_DRAIN:if(out_valid&&out_ready&&out_last)state<=T_RELEASE;
    T_RELEASE:if(t_release_ready)begin state<=DONE;running<=0;error_latched<=0;end
    DONE:if(done_ready)empty_frame();
    default:if(running)fail_job();else begin empty_frame();internal_reset<=1;end
   endcase
  end
 end
endmodule
