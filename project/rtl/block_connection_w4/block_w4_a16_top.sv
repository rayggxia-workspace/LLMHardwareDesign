// Issue151 W4 A16, parentf665230 / native7078786.
// H8, two-token causal prefill, one head: RMS/QKV/RoPE/Softmax/PV/Wo/residual.
// New fixed local sequencing and real K/V layout staging; no leaf changes.
// Fixed27-beat frame, two output words; no MEM/cross-island/quality/PPA claim.
module block_w4_a16_top(
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
  T_BEGIN=13,T_WRITE=14,T_COMMIT=15,
  T_DRAIN=16,T_RELEASE=17,DONE=18,N_REQ=19,N_RSP=20;
 localparam [1:0] OWNER_LOCAL=0,OWNER_E=1,OWNER_N=3;
 localparam [3:0] L_INIT_PAD=0,L_M_SAVE=1,L_K_READ0=2,L_K_WRITE0=3,
  L_K_READ1=4,L_K_WRITE1=5,L_K_ZERO=6,L_V_READ0=7,L_V_READ1=8,
  L_V_WRITE=9,L_FINAL_READ0=10,L_FINAL_READ1=11;
 localparam [2:0] MC_CLEAR=0,MC_SCALE=1,MC_EXEC=2,MC_READ0=3,
  MC_READ1=4,MC_READ2=5,MC_READ3=6;
 reg [5:0] state;
 reg [1:0] owner,n_stage;
 reg [2:0] projection,pad_index,e_stage,v_column_index,m_phase;
 reg [3:0] local_tag;
 reg [4:0] input_index;
 reg frame_active,frame_stored,running,error_latched,saturation_latched;
 reg internal_reset,local_write,t_write_slot;
 reg [9:0] local_addr;
 reg [127:0] held_data,v_hold0,v_hold1,final0;
 reg [63:0] m_low_half;
 wire [9:0] m_save_base;
 wire leaf_reset;
 wire input_fire,start_fire;
 // Named constants are finite TB fault/stall points, not runtime host fields.
 wire permit_s_req=1'b1,permit_s_rsp=1'b1;
 wire permit_m_cmd=1'b1,permit_m_rsp=1'b1,permit_load=1'b1;
 wire permit_e_req=1'b1,permit_e_rsp=1'b1;
 wire permit_n_req=1'b1,permit_n_rsp=1'b1;
 wire h_req_valid,h_req_ready,h_req_write,h_rsp_valid,h_rsp_ready,h_rsp_error;
 wire [9:0] h_req_addr;
 wire [127:0] h_req_data,h_rsp_data;
 wire local_req_valid,local_rsp_ready;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_s_take;
 wire [9:0] s_addr;
 wire [127:0] s_din,s_dout;
 wire e_req_valid,e_req_ready,e_rsp_valid,e_rsp_ready,e_rsp_error,e_rsp_saturated;
 wire e_mem_req_valid,e_mem_req_ready,e_mem_req_write,e_mem_rsp_valid,e_mem_rsp_ready,e_mem_rsp_error;
 wire [9:0] e_mem_req_addr;
 wire [127:0] e_mem_req_data,e_mem_rsp_data;
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

 // X0/1 are full S16 words at beats0/4; six intervening words are
 // hardware canonical zero. All weights/gamma/RoPE inputs remain variable.
 function automatic [127:0] canonical_input;
  input [4:0] index;input [127:0] data;
  begin canonical_input=(index<5'd8 && index[1:0]!=0) ? 128'd0 : data;end
 endfunction
 function automatic [63:0] pack_m_four;
  input [127:0] data;
  begin pack_m_four={data[111:96],data[79:64],data[47:32],data[15:0]};end
 endfunction
 function automatic [9:0] padding_addr;
  input [2:0] index;
  begin case(index)
   0:padding_addr=10'd482;1:padding_addr=10'd483;
   2:padding_addr=10'd518;3:padding_addr=10'd519;
   4:padding_addr=10'd522;default:padding_addr=10'd523;
  endcase end
 endfunction
 // Real finite transpose selector, not a compiler-only promise or M11 logic.
 // Column h stores [V0[h],V1[h],0,0,0,0,0,0], in S16 lane order.
 function automatic [127:0] transpose_v_column;
  input [127:0] row0,row1;input [2:0] column;
  begin
   transpose_v_column=128'd0;
   transpose_v_column[15:0]=row0[16*column+:16];
   transpose_v_column[31:16]=row1[16*column+:16];
  end
 endfunction
 // Exactly one ordinary-S helper. Owner stays selected through an entire
 // E/N service, including its destination write ACK and response retirement.
 assign local_req_valid=state==INPUT_REQ||state==LOCAL_REQ;
 assign local_rsp_ready=state==INPUT_RSP||state==LOCAL_RSP;
 assign h_req_valid=!leaf_reset&&permit_s_req&&
  (owner==OWNER_E ? e_mem_req_valid : owner==OWNER_N ? n_mem_req_valid : local_req_valid);
 assign h_req_write=owner==OWNER_E ? e_mem_req_write : owner==OWNER_N ? n_mem_req_write :
  (state==INPUT_REQ?1'b1:local_write);
 assign h_req_addr=owner==OWNER_E ? e_mem_req_addr : owner==OWNER_N ? n_mem_req_addr :
  (state==INPUT_REQ ? 10'd448+{5'd0,input_index} : local_addr);
 assign h_req_data=owner==OWNER_E ? e_mem_req_data : owner==OWNER_N ? n_mem_req_data : held_data;
 assign h_rsp_ready=!leaf_reset&&(owner==OWNER_E ? e_mem_rsp_ready : owner==OWNER_N ? n_mem_rsp_ready : local_rsp_ready);
 assign e_mem_req_ready=!leaf_reset&&permit_s_req&&owner==OWNER_E&&h_req_ready;
 assign n_mem_req_ready=!leaf_reset&&permit_s_req&&owner==OWNER_N&&h_req_ready;
 assign e_mem_rsp_valid=!leaf_reset&&owner==OWNER_E&&h_rsp_valid;
 assign n_mem_rsp_valid=!leaf_reset&&owner==OWNER_N&&h_rsp_valid;
 assign e_mem_rsp_data=h_rsp_data;
 assign e_mem_rsp_error=h_rsp_error;
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
  .req_mode(n_stage<2 ? 2'd1 : 2'd0),
  .req_count(n_stage<2 ? 16'd8 : n_stage==2 ? 16'd1 : 16'd2),.req_epsilon(32'd1),
  .req_src_addr(n_stage==0 ? 10'd448 : n_stage==1 ? 10'd452 : n_stage==2 ? 10'd512 : 10'd513),
  .req_gamma_addr(10'd472),.req_exp_addr(n_stage==3 ? 10'd515 : 10'd514),
  .req_dst_addr(n_stage==0 ? 10'd480 : n_stage==1 ? 10'd481 : n_stage==2 ? 10'd516 : 10'd517),
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
  .req_op(e_stage<4 ? 4'd9 : 4'd0),.req_shift(e_stage<4 ? 5'd14 : 5'd0),.req_count(4'd8),
  .req_src_a(e_stage<4 ? 10'd488+{7'd0,e_stage} : 10'd524+{9'd0,e_stage[0]}),
  .req_src_b(e_stage<4 ? 10'd473+{9'd0,e_stage[0]} : e_stage==4 ? 10'd448 : 10'd452),.req_src_c(10'd0),
  .req_dst(e_stage<4 ? 10'd488+{7'd0,e_stage} : 10'd528+{9'd0,e_stage[0]}),
  .rsp_valid(e_rsp_valid),.rsp_ready(e_rsp_ready),
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
 assign load_valid=!leaf_reset&&state==LOAD_CMD&&permit_load;
 assign load_done_take=!leaf_reset&&state==LOAD_RSP;
 block_feed_s_macro u_s(
  .clk(clk),.reset(leaf_reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),
  .ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),
  .load_valid(load_valid),.load_ready(load_ready),.load_bank(1'b0),.load_rows(4'd2),.load_tiles(3'd1),
  .load_a_wide(1'b1),.load_b_wide(projection==3||projection==4),.load_reuse_b(1'b0),
  .load_a_base(projection<3 ? 10'd480 : projection==3 ? 10'd488 : projection==4 ? 10'd516 : 10'd520),
  .load_b_base(projection==0 ? 10'd456 : projection==1 ? 10'd460 : projection==2 ? 10'd464 :
               projection==3 ? 10'd496 : projection==4 ? 10'd504 : 10'd468),
  .done_valid(load_done_valid),.done_take(load_done_take),.done_error(load_done_error),.busy(loader_busy),
  .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data));
 assign m_cmd_valid=!leaf_reset&&state==M_CMD&&permit_m_cmd;
 assign m_rsp_ready=!leaf_reset&&state==M_RSP&&permit_m_rsp;
 assign m_cmd_op=m_phase==MC_CLEAR ? 4'd6 : m_phase==MC_SCALE ? 4'd4 : m_phase==MC_EXEC ? 4'd10 : 4'd5;
 assign m_cmd_index=m_phase==MC_READ1 ? 6'd1 : m_phase==MC_READ2 ? 6'd8 : m_phase==MC_READ3 ? 6'd9 : 6'd0;
 assign m_cmd_data=m_phase==MC_SCALE ? (projection==3 ? 64'd11585 : 64'd1) :
  m_phase==MC_EXEC ? (projection==3||projection==4 ? 64'h11887 : 64'h11885) :
  m_phase>=MC_READ0 ? (projection==3 ? 64'h119 : projection==4 ? 64'h10e : 64'h107) : 64'd0;
 assign m_save_base=projection==0 ? 10'd488 : projection==1 ? 10'd490 : projection==2 ? 10'd492 :
  projection==3 ? 10'd512 : projection==4 ? 10'd520 : 10'd524;
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
  .begin_owner(2'd0),.begin_generation(32'd1),.begin_words(10'd2),
  .write_valid(!leaf_reset&&state==T_WRITE),.write_ready(t_write_ready),.write_index({9'd0,t_write_slot}),.write_data(t_write_slot ? held_data : final0),
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
   held_data<=0;v_hold0<=0;v_hold1<=0;final0<=0;m_low_half<=0;
   internal_reset<=0;e_stage<=0;n_stage<=0;v_column_index<=0;t_write_slot<=0;local_write<=0;local_addr<=0;
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
    end else if(start_fire)begin
     running<=1;error_latched<=0;saturation_latched<=0;owner<=OWNER_LOCAL;
     projection<=0;m_phase<=MC_CLEAR;e_stage<=0;n_stage<=0;v_column_index<=0;t_write_slot<=0;
     local_tag<=L_INIT_PAD;pad_index<=0;local_write<=1;local_addr<=10'd482;held_data<=0;state<=LOCAL_REQ;
    end
    INPUT_REQ:if(h_req_valid&&h_req_ready)state<=INPUT_RSP;
    INPUT_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)begin empty_frame();internal_reset<=1;end
     else begin state<=IDLE;
      if(input_index==5'd26)frame_stored<=1;else input_index<=input_index+1'b1;
     end
    end
    LOCAL_REQ:if(h_req_valid&&h_req_ready)state<=LOCAL_RSP;
    LOCAL_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();
     else case(local_tag)
      L_INIT_PAD:if(pad_index==5)begin owner<=OWNER_N;n_stage<=0;state<=N_REQ;end
       else begin pad_index<=pad_index+1'b1;local_addr<=padding_addr(pad_index+3'd1);state<=LOCAL_REQ;end
      L_M_SAVE:begin
       if(m_phase==MC_READ1)begin m_phase<=MC_READ2;state<=M_CMD;end
       else if(projection<2)begin projection<=projection+1'b1;m_phase<=MC_CLEAR;state<=M_CMD;end
       else if(projection==2)begin owner<=OWNER_E;e_stage<=0;state<=E_REQ;end
       else if(projection==3)begin owner<=OWNER_N;n_stage<=2;state<=N_REQ;end
       else if(projection==4)begin projection<=5;m_phase<=MC_CLEAR;state<=M_CMD;end
       else begin owner<=OWNER_E;e_stage<=4;state<=E_REQ;end
      end
      L_K_READ0:begin held_data<=h_rsp_data;local_tag<=L_K_WRITE0;local_write<=1;local_addr<=10'd496;state<=LOCAL_REQ;end
      L_K_WRITE0:begin local_tag<=L_K_READ1;local_write<=0;local_addr<=10'd491;state<=LOCAL_REQ;end
      L_K_READ1:begin held_data<=h_rsp_data;local_tag<=L_K_WRITE1;local_write<=1;local_addr<=10'd497;state<=LOCAL_REQ;end
      L_K_WRITE1:begin held_data<=0;local_tag<=L_K_ZERO;local_write<=1;local_addr<=10'd498;pad_index<=0;state<=LOCAL_REQ;end
      L_K_ZERO:if(pad_index==5)begin local_tag<=L_V_READ0;local_write<=0;local_addr<=10'd492;state<=LOCAL_REQ;end
       else begin pad_index<=pad_index+1'b1;local_addr<=local_addr+1'b1;state<=LOCAL_REQ;end
      L_V_READ0:begin v_hold0<=h_rsp_data;local_tag<=L_V_READ1;local_addr<=10'd493;state<=LOCAL_REQ;end
      L_V_READ1:begin
       v_hold1<=h_rsp_data;held_data<=transpose_v_column(v_hold0,h_rsp_data,3'd0);
       local_tag<=L_V_WRITE;local_write<=1;local_addr<=10'd504;v_column_index<=0;state<=LOCAL_REQ;
      end
      L_V_WRITE:if(v_column_index==7)begin projection<=3;m_phase<=MC_CLEAR;state<=M_CMD;end
       else begin
        v_column_index<=v_column_index+1'b1;local_addr<=local_addr+1'b1;
        held_data<=transpose_v_column(v_hold0,v_hold1,v_column_index+3'd1);state<=LOCAL_REQ;
       end
      L_FINAL_READ0:begin final0<=h_rsp_data;local_tag<=L_FINAL_READ1;local_addr<=10'd529;state<=LOCAL_REQ;end
      L_FINAL_READ1:begin held_data<=h_rsp_data;t_write_slot<=0;state<=T_BEGIN;end
      default:fail_job();
     endcase
    end
    N_REQ:if(n_req_valid&&n_req_ready)state<=N_RSP;
    N_RSP:if(n_rsp_valid&&n_rsp_ready)begin
     saturation_latched<=saturation_latched||n_rsp_saturated;
     if(n_rsp_error)fail_job();
     else if(n_stage==0||n_stage==2)begin n_stage<=n_stage+1'b1;state<=N_REQ;end
     else begin owner<=OWNER_LOCAL;projection<=n_stage==1 ? 3'd0 : 3'd4;m_phase<=MC_CLEAR;state<=M_CMD;end
    end
    E_REQ:if(e_req_valid&&e_req_ready)state<=E_RSP;
    E_RSP:if(e_rsp_valid&&e_rsp_ready)begin
     saturation_latched<=saturation_latched||e_rsp_saturated;
     if(e_rsp_error)fail_job();
     else if(e_stage<3||e_stage==4)begin e_stage<=e_stage+1'b1;state<=E_REQ;end
     else begin owner<=OWNER_LOCAL;local_write<=0;state<=LOCAL_REQ;
      if(e_stage==3)begin local_tag<=L_K_READ0;local_addr<=10'd490;end
      else begin local_tag<=L_FINAL_READ0;local_addr<=10'd528;end
     end
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
      MC_READ2:begin m_low_half<=pack_m_four(m_rsp_data);m_phase<=MC_READ3;state<=M_CMD;end
      MC_READ1,MC_READ3:begin
       held_data<={pack_m_four(m_rsp_data),m_low_half};local_tag<=L_M_SAVE;local_write<=1;
       local_addr<=m_save_base+(m_phase==MC_READ3 ? 10'd1 : 10'd0);state<=LOCAL_REQ;
      end
      default:fail_job();
     endcase
    end
    LOAD_CMD:if(load_valid&&load_ready)state<=LOAD_RSP;
    LOAD_RSP:if(load_done_valid&&load_done_take)begin
     if(load_done_error)fail_job();else begin m_phase<=MC_EXEC;state<=M_CMD;end
    end
    T_BEGIN:if(t_begin_ready)begin t_write_slot<=0;state<=T_WRITE;end
    T_WRITE:if(t_write_ready)begin if(t_write_slot)state<=T_COMMIT;else t_write_slot<=1;end
    T_COMMIT:if(t_commit_ready)state<=T_DRAIN;
    T_DRAIN:if(out_valid&&out_ready&&out_last)state<=T_RELEASE;
    T_RELEASE:if(t_release_ready)begin state<=DONE;running<=0;error_latched<=0;end
    DONE:if(done_ready)empty_frame();
    default:if(running)fail_job();else begin empty_frame();internal_reset<=1;end
   endcase
  end
 end
endmodule
