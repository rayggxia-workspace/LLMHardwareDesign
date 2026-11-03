// Issue151 L4-A-FULL: H1024, Sq2, KV8/Q16, D128, Wo K2048 and residual.
// One real M/N/E/S/T and shared controllers. No G/R, private vector array or MEM.
// Fin10 / weight Fin7; fixed program, not trained-model quality acceptance.
module block_w4_afull_top(
 input wire clk,reset,abort,
 input wire job_valid,output wire job_ready,input wire [31:0] job_generation,
 input wire [15:0] weights_version,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 input wire [31:0] in_generation,input wire [8:0] in_index,input wire in_last,
 output wire input_stored,input wire start_valid,output wire start_ready,output wire busy,
 output wire done_valid,input wire done_ready,output wire done_error,done_saturated,done_partial,
 output wire [8:0] done_words,output wire [31:0] done_generation,
 output wire out_valid,input wire out_ready,output wire [127:0] out_data,
 output wire [9:0] out_index,output wire out_last,output wire [31:0] out_generation,
 output wire wreq_valid,input wire wreq_ready,
 output wire [31:0] wreq_job,output wire [15:0] wreq_seq,wreq_version,
 output wire [1:0] wreq_matrix,output wire [3:0] wreq_head,
 output wire [6:0] wreq_group,output wire [5:0] wreq_chunk,
 input wire w_valid,output wire w_ready,input wire [31:0] w_job,
 input wire [15:0] w_seq,w_version,input wire [3:0] w_index,
 input wire w_last,w_error,input wire [127:0] w_data
);
 localparam [5:0] WAIT_JOB=0,INPUT=1,INPUT_REQ=2,INPUT_RSP=3,STORED=4,
  LOCAL_REQ=5,LOCAL_RSP=6,N_REQ=7,N_RSP=8,E_REQ=9,E_RSP=10,
  M_CMD=11,M_RSP=12,LOAD_CMD=13,LOAD_RSP=14,WEIGHT_REQ=15,WEIGHT_RX=16,
  OUTPUT_HOLD=17,DONE=18,RAW_BEGIN=19,RAW_READ_REQ=20,RAW_READ_RSP=21,
  RAW_WRITE=22,RAW_COMMIT=23,RAW_SAVED=24,RAW_CAPTURE=25,RAW_SAVE_REQ=26,
  RAW_SAVE_RSP=27,RAW_RELEASE=28,OUT_BEGIN=29,OUT_READ_REQ=30,OUT_READ_RSP=31,
  OUT_WRITE=32,OUT_COMMIT=33,OUT_DRAIN=34,OUT_RELEASE=35,CONTEXT_READY=36;
 localparam [3:0] IN_NORM=0,PARAM_MOVE=1,PROJECTION=2,HEAD_NORM=3,ROPE=4,
  QK=5,SOFTMAX=6,PV=7,WO=8,RESIDUAL=9,OUTPUT=10,PAD_A=11;
 localparam [1:0] OWNER_LOCAL=0,OWNER_E=1,OWNER_N=3;
 localparam [4:0] L_PARAM_R=0,L_PARAM_W=1,L_A_R0=2,L_A_W0=3,L_A_R1=4,L_A_W1=5,
  L_A_Z2=6,L_A_Z3=7,L_WEIGHT_W=8,L_K_R0=9,L_K_W0=10,L_K_R1=11,L_K_W1=12,
  L_K_ZERO=13,L_V_R0=14,L_V_R1=15,L_V_COL=16,L_M_SAVE=17,
  L_ROPE_R0=18,L_ROPE_R1=19,L_ROPE_W=20,L_OUTPUT_R=21,L_PAD_A=22;
 localparam [1:0] MC_CLEAR=0,MC_SCALE=1,MC_EXEC=2,MC_READ=3;
 reg [5:0] state;
 reg [4:0] local_tag;
 reg [3:0] stage,rope_group,weight_index,q_head;
 reg [6:0] group_index;
 reg [1:0] owner,matrix,tile_index,m_phase,read_slot;
 reg [5:0] chunk_index;
 reg [5:0] copy_index;
 reg [8:0] output_index;
 reg [7:0] raw_index;
 reg [9:0] context_words;
 reg [2:0] kv_head,pad_index;
 reg [2:0] column_index;
 reg [8:0] input_index,output_count;
 reg token_index,row_index,frame_active,frame_stored,running,raw_saved,padding_live;
 reg error_latched,saturation_latched,internal_reset,local_write;
 reg [9:0] local_addr;
 reg [31:0] job_generation_hold;
 reg [15:0] version_hold,request_seq;
 reg [127:0] held_data,v_hold0,v_hold1;
 reg [63:0] m_low_half;
 reg [1:0] n_mode_hold;
 reg [15:0] n_count_hold;
 reg [9:0] n_src_hold,n_gamma_hold,n_exp_hold,n_dst_hold;
 wire leaf_reset,input_fire,start_fire,input_meta_ok,weight_meta_ok;
 wire permit_s_req=1'b1,permit_s_rsp=1'b1,permit_m_cmd=1'b1,permit_m_rsp=1'b1;
 wire permit_load=1'b1,permit_e_req=1'b1,permit_e_rsp=1'b1;
 wire permit_n_req=1'b1,permit_n_rsp=1'b1,permit_wreq=1'b1,permit_wrx=1'b1;
 wire permit_output=1'b1,permit_context_to_wo=1'b1;
 wire permit_t_begin=1'b1,permit_t_write=1'b1,permit_t_commit=1'b1;
 wire permit_t_read=1'b1,permit_t_release=1'b1;
 wire h_req_valid,h_req_ready,h_req_write,h_rsp_valid,h_rsp_ready,h_rsp_error;
 wire [9:0] h_req_addr;
 wire [127:0] h_req_data,h_rsp_data;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_s_take;
 wire [9:0] s_addr;
 wire [127:0] s_din,s_dout;
 wire local_req_valid,local_rsp_ready;
 wire e_req_valid,e_req_ready,e_rsp_valid,e_rsp_ready,e_rsp_error,e_rsp_saturated;
 wire e_mem_req_valid,e_mem_req_ready,e_mem_req_write,e_mem_rsp_valid,e_mem_rsp_ready;
 wire [9:0] e_mem_req_addr;
 wire [127:0] e_mem_req_data;
 wire e_in_valid,e_in_ready,e_out_valid,e_out_ready,e_out_error,e_out_saturated;
 wire [3:0] e_in_op;
 wire [4:0] e_in_shift;
 wire [127:0] e_in_a,e_in_b,e_in_c,e_out_data;
 wire n_req_valid,n_req_ready,n_rsp_valid,n_rsp_ready,n_rsp_error,n_rsp_saturated,n_ctrl_busy;
 wire n_mem_req_valid,n_mem_req_ready,n_mem_req_write,n_mem_rsp_valid,n_mem_rsp_ready;
 wire [9:0] n_mem_req_addr;
 wire [127:0] n_mem_req_data;
 wire n_cmd_valid,n_cmd_ready,n_native_rsp_valid,n_native_rsp_ready,n_native_rsp_error,n_native_rsp_saturated,n_busy;
 wire [3:0] n_cmd_op,n_cmd_count;
 wire [31:0] n_cmd_param;
 wire [127:0] n_cmd_data,n_cmd_aux,n_native_rsp_data;
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
 wire [9:0] head_src_base,projection_save_base,e_dst;
 wire linear_stage,selected_req_valid,padding_address,padding_violation,context_complete;
 wire t_begin_valid,t_begin_ready,t_write_valid,t_write_ready,t_commit_valid,t_commit_ready;
 wire t_release_valid,t_release_ready,t_read_valid,t_read_take,t_read_last;
 wire [9:0] t_write_index,t_read_index,t_word_count;
 wire [127:0] t_read_data;
 wire [1:0] t_owner;
 wire [31:0] t_generation;
 wire [2:0] t_state;
 wire t_busy,t_sealed,t_committed,t_protocol_error,raw_meta_ok,out_meta_ok,head_t_violation;

 assign leaf_reset=reset||abort||internal_reset;
 assign job_ready=!leaf_reset&&state==WAIT_JOB;
 assign in_ready=!leaf_reset&&state==INPUT&&input_index<9'd448;
 assign input_fire=in_valid&&in_ready;
 assign input_meta_ok=in_generation==job_generation_hold&&in_index==input_index&&in_last==(input_index==9'd447);
 assign input_stored=!reset&&!abort&&frame_stored;
 assign start_ready=!leaf_reset&&state==STORED&&frame_stored;
 assign start_fire=start_valid&&start_ready;
 assign busy=!reset&&(frame_active||state==DONE);
 assign done_valid=!reset&&state==DONE;
 assign done_error=error_latched;assign done_saturated=saturation_latched;
 assign done_partial=error_latched&&output_count!=0;
 assign done_words=output_count;assign done_generation=job_generation_hold;
 assign out_valid=!leaf_reset&&state==OUT_DRAIN&&permit_output&&permit_t_read&&
  t_read_valid&&out_meta_ok&&!t_protocol_error;
 assign out_data=t_read_data;assign out_index=t_read_index;
 assign out_last=out_valid&&t_read_last;assign out_generation=job_generation_hold;
 assign linear_stage=stage==PROJECTION||stage==WO;
 assign context_complete=context_words==10'd512;
 assign wreq_valid=!leaf_reset&&state==WEIGHT_REQ&&permit_wreq;
 assign wreq_job=job_generation_hold;assign wreq_seq=request_seq;assign wreq_version=version_hold;
 assign wreq_matrix=matrix;assign wreq_group=group_index;assign wreq_chunk=chunk_index;
 assign wreq_head=matrix<2 ? {1'd0,kv_head} : matrix==2 ? q_head : 4'd0;
 // One request is outstanding. Any accepted bad/old/future tag fails the job;
 // no unbounded late-stream drain and no write on a metadata error.
 assign w_ready=!leaf_reset&&state==WEIGHT_RX&&permit_wrx;
 assign weight_meta_ok=w_job==job_generation_hold&&w_seq==request_seq&&w_version==version_hold&&
  w_index==weight_index&&w_last==(weight_index==4'd15)&&!w_error;
 assign head_src_base=matrix==0 ? 10'd192 : 10'd256;
 assign projection_save_base=matrix==0 ? 10'd192 : matrix==1 ? 10'd224 : 10'd256;
 assign e_dst=stage==RESIDUAL ?
  (row_index ? 10'd384+{3'd0,group_index} : {3'd0,group_index}) :
  head_src_base+{5'd0,token_index,4'd0}+{6'd0,rope_group};

 function automatic [9:0] a_source;
  input [1:0] tile;input row;
  begin
   if(stage==PROJECTION)a_source=(row ? 10'd0 : 10'd384)+{2'd0,chunk_index,2'd0}+{8'd0,tile};
   else if(stage==WO)a_source=(row ? 10'd768 : 10'd512)+{2'd0,chunk_index,2'd0}+{8'd0,tile};
   else if(stage==QK)a_source=10'd256+{5'd0,row,4'd0}+{2'd0,chunk_index,2'd0}+{8'd0,tile};
   else a_source=10'd372+{9'd0,row};
  end
 endfunction
 function automatic [9:0] padding_addr;
  input [2:0] index;
  begin padding_addr=10'd322+{6'd0,index[2:1],2'd0}+{9'd0,index[0]};end
 endfunction
 function automatic [9:0] a_stage;
  input [1:0] tile;input [1:0] slot;
  begin a_stage=10'd320+{6'd0,tile,2'd0}+{8'd0,slot};end
 endfunction
 function automatic [9:0] result_addr;
  input row;
  begin
   if(stage==PROJECTION)result_addr=projection_save_base+{5'd0,row,4'd0}+{3'd0,group_index};
   else if(stage==WO)result_addr=10'd256+{9'd0,row};
   else if(stage==QK)result_addr=10'd368+{9'd0,row};
   else result_addr=10'd512+{1'd0,row,8'd0}+{2'd0,q_head,4'd0}+{3'd0,group_index};
  end
 endfunction
 function automatic [63:0] pack_m_four;
  input [127:0] data;
  begin pack_m_four={data[111:96],data[79:64],data[47:32],data[15:0]};end
 endfunction
 function automatic [127:0] pair_rope;
  input [127:0] lo,hi;input upper;
  integer j,k;
  begin
   pair_rope=0;
   for(j=0;j<4;j=j+1)begin
    k=(upper ? 4 : 0)+j;
    pair_rope[32*j+:16]=lo[16*k+:16];pair_rope[32*j+16+:16]=hi[16*k+:16];
   end
  end
 endfunction
 function automatic [127:0] transpose_v;
  input [127:0] x0,x1;input [2:0] column;
  begin transpose_v=0;transpose_v[15:0]=x0[16*column+:16];transpose_v[31:16]=x1[16*column+:16];end
 endfunction

 assign local_req_valid=state==INPUT_REQ||state==LOCAL_REQ||state==RAW_READ_REQ||
  state==RAW_SAVE_REQ||state==OUT_READ_REQ;
 assign local_rsp_ready=state==INPUT_RSP||state==LOCAL_RSP||state==RAW_READ_RSP||
  state==RAW_SAVE_RSP||state==OUT_READ_RSP;
 assign selected_req_valid=owner==OWNER_E ? e_mem_req_valid : owner==OWNER_N ? n_mem_req_valid : local_req_valid;
 // The eight real padding writes are made once after gamma/parameter use.
 // From then on no ordinary writer may overwrite these persistent zeros.
 assign padding_address=h_req_addr>=10'd320&&h_req_addr<10'd336&&h_req_addr[1];
 assign padding_violation=padding_live&&selected_req_valid&&h_req_write&&padding_address;
 assign h_req_valid=!leaf_reset&&permit_s_req&&selected_req_valid&&!padding_violation;
 assign h_req_write=owner==OWNER_E ? e_mem_req_write : owner==OWNER_N ? n_mem_req_write :
  (state==INPUT_REQ||state==RAW_SAVE_REQ ? 1'b1 : state==RAW_READ_REQ||state==OUT_READ_REQ ? 1'b0 : local_write);
 assign h_req_addr=owner==OWNER_E ? e_mem_req_addr : owner==OWNER_N ? n_mem_req_addr :
  state==INPUT_REQ ? (input_index<9'd384 ? {1'd0,input_index} : 10'd512+({1'd0,input_index}-10'd384)) :
  state==RAW_READ_REQ ? {2'd0,raw_index[0],raw_index[7:1]} :
  state==RAW_SAVE_REQ ? 10'd258 : state==OUT_READ_REQ ?
   (output_index[7] ? 10'd384+{3'd0,output_index[6:0]} : {3'd0,output_index[6:0]}) : local_addr;
 assign h_req_data=owner==OWNER_E ? e_mem_req_data : owner==OWNER_N ? n_mem_req_data : held_data;
 assign h_rsp_ready=!leaf_reset&&(owner==OWNER_E ? e_mem_rsp_ready : owner==OWNER_N ? n_mem_rsp_ready : local_rsp_ready);
 assign e_mem_req_ready=!leaf_reset&&permit_s_req&&!padding_violation&&owner==OWNER_E&&h_req_ready;
 assign n_mem_req_ready=!leaf_reset&&permit_s_req&&!padding_violation&&owner==OWNER_N&&h_req_ready;
 assign e_mem_rsp_valid=!leaf_reset&&owner==OWNER_E&&h_rsp_valid;
 assign n_mem_rsp_valid=!leaf_reset&&owner==OWNER_N&&h_rsp_valid;
 assign s_take=helper_s_take&&permit_s_rsp;
 block_p2_s_ctrl u_s_ctrl(
  .clk(clk),.resetn(!leaf_reset),.req_valid(h_req_valid),.req_ready(h_req_ready),
  .req_write(h_req_write),.req_addr(h_req_addr),.req_data(h_req_data),
  .rsp_valid(h_rsp_valid),.rsp_ready(h_rsp_ready),.rsp_data(h_rsp_data),.rsp_error(h_rsp_error),
  .s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_ready(s_ready),
  .s_rsp_valid(s_valid&&permit_s_rsp),.s_rsp_ready(helper_s_take),.s_dout(s_dout));
 block_feed_s_macro u_s(
  .clk(clk),.reset(leaf_reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),
  .ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),
  .load_valid(load_valid),.load_ready(load_ready),.load_bank(1'b0),.load_rows(4'd2),
  .load_tiles(stage==PV ? 3'd1 : 3'd4),.load_a_wide(1'b1),.load_b_wide(!linear_stage),
  .load_reuse_b(1'b0),.load_a_base(10'd320),.load_b_base(10'd336),
  .done_valid(load_done_valid),.done_take(load_done_take),.done_error(load_done_error),.busy(loader_busy),
  .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data));
 assign load_valid=!leaf_reset&&state==LOAD_CMD&&permit_load;
 assign load_done_take=!leaf_reset&&state==LOAD_RSP;

 assign e_req_valid=!leaf_reset&&state==E_REQ&&permit_e_req;
 assign e_rsp_ready=!leaf_reset&&state==E_RSP&&permit_e_rsp;
 block_w3_e_ctrl u_e_ctrl(
  .clk(clk),.reset(leaf_reset),.req_valid(e_req_valid),.req_ready(e_req_ready),
  .req_op(stage==RESIDUAL ? 4'd0 : 4'd9),.req_shift(stage==RESIDUAL ? 5'd0 : 5'd14),.req_count(4'd8),
  .req_src_a(stage==RESIDUAL ? 10'd256+{9'd0,row_index} : 10'd374),
  .req_src_b(stage==RESIDUAL ? 10'd258 : 10'd160+{5'd0,token_index,4'd0}+{6'd0,rope_group}),
  .req_src_c(10'd0),.req_dst(e_dst),
  .rsp_valid(e_rsp_valid),.rsp_ready(e_rsp_ready),.rsp_error(e_rsp_error),.rsp_saturated(e_rsp_saturated),
  .mem_req_valid(e_mem_req_valid),.mem_req_ready(e_mem_req_ready),.mem_req_write(e_mem_req_write),
  .mem_req_addr(e_mem_req_addr),.mem_req_data(e_mem_req_data),
  .mem_rsp_valid(e_mem_rsp_valid),.mem_rsp_ready(e_mem_rsp_ready),.mem_rsp_data(h_rsp_data),.mem_rsp_error(h_rsp_error),
  .e_in_valid(e_in_valid),.e_in_ready(e_in_ready),.e_in_op(e_in_op),.e_in_shift(e_in_shift),
  .e_in_a(e_in_a),.e_in_b(e_in_b),.e_in_c(e_in_c),.e_out_valid(e_out_valid),.e_out_ready(e_out_ready),
  .e_out_data(e_out_data),.e_out_error(e_out_error),.e_out_saturated(e_out_saturated));
 block_v2_e u_e(.clk(clk),.reset(leaf_reset),.in_valid(e_in_valid),.in_ready(e_in_ready),
  .in_op(e_in_op),.in_shift(e_in_shift),.in_a(e_in_a),.in_b(e_in_b),.in_c(e_in_c),
  .out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),.out_error(e_out_error),.out_saturated(e_out_saturated));

 assign n_req_valid=!leaf_reset&&state==N_REQ&&permit_n_req;
 assign n_rsp_ready=!leaf_reset&&state==N_RSP&&permit_n_rsp;
 block_w4_n_long_ctrl u_n_ctrl(
  .clk(clk),.reset(leaf_reset),.req_valid(n_req_valid),.req_ready(n_req_ready),
  .req_mode(n_mode_hold),.req_count(n_count_hold),.req_epsilon(32'd1),
  .req_src_addr(n_src_hold),.req_gamma_addr(n_gamma_hold),.req_exp_addr(n_exp_hold),.req_dst_addr(n_dst_hold),
  .rsp_valid(n_rsp_valid),.rsp_ready(n_rsp_ready),.rsp_error(n_rsp_error),.rsp_saturated(n_rsp_saturated),.busy(n_ctrl_busy),
  .mem_req_valid(n_mem_req_valid),.mem_req_ready(n_mem_req_ready),.mem_req_write(n_mem_req_write),
  .mem_req_addr(n_mem_req_addr),.mem_req_data(n_mem_req_data),.mem_rsp_valid(n_mem_rsp_valid),
  .mem_rsp_ready(n_mem_rsp_ready),.mem_rsp_data(h_rsp_data),.mem_rsp_error(h_rsp_error),
  .n_cmd_valid(n_cmd_valid),.n_cmd_ready(n_cmd_ready),.n_cmd_op(n_cmd_op),.n_cmd_count(n_cmd_count),
  .n_cmd_param(n_cmd_param),.n_cmd_data(n_cmd_data),.n_cmd_aux(n_cmd_aux),
  .n_rsp_valid(n_native_rsp_valid),.n_rsp_ready(n_native_rsp_ready),.n_rsp_data(n_native_rsp_data),
  .n_rsp_error(n_native_rsp_error),.n_rsp_saturated(n_native_rsp_saturated));
 block_v2_n u_n(.clk(clk),.reset(leaf_reset),.cmd_valid(n_cmd_valid),.cmd_ready(n_cmd_ready),
  .cmd_op(n_cmd_op),.cmd_count(n_cmd_count),.cmd_param(n_cmd_param),.cmd_data(n_cmd_data),.cmd_aux(n_cmd_aux),
  .rsp_valid(n_native_rsp_valid),.rsp_ready(n_native_rsp_ready),.rsp_data(n_native_rsp_data),
  .rsp_error(n_native_rsp_error),.rsp_saturated(n_native_rsp_saturated),.busy(n_busy));

 assign m_cmd_valid=!leaf_reset&&state==M_CMD&&permit_m_cmd;
 assign m_rsp_ready=!leaf_reset&&state==M_RSP&&permit_m_rsp;
 assign m_cmd_op=m_phase==MC_CLEAR ? 4'd6 : m_phase==MC_SCALE ? 4'd4 : m_phase==MC_EXEC ? 4'd10 : 4'd5;
 assign m_cmd_index=m_phase!=MC_READ ? 6'd0 :
  read_slot==0 ? 6'd0 : read_slot==1 ? 6'd1 : read_slot==2 ? 6'd8 : 6'd9;
 assign m_cmd_data=m_phase==MC_SCALE ? (stage==QK ? 64'd2896 : 64'd1) :
  m_phase==MC_EXEC ? (linear_stage ? (chunk_index==0 ? 64'h14885 : 64'h14881) :
                     stage==QK ? (chunk_index==0 ? 64'h14287 : 64'h14283) : 64'h11827) :
  m_phase==MC_READ ? (linear_stage ? 64'h107 : stage==QK ? 64'h119 : 64'h10e) : 64'd0;
 block_v2_m u_m(.clk(clk),.reset(leaf_reset),
  .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data),
  .cmd_valid(m_cmd_valid),.cmd_ready(m_cmd_ready),.cmd_op(m_cmd_op),.cmd_index(m_cmd_index),.cmd_data(m_cmd_data),
  .rsp_valid(m_rsp_valid),.rsp_ready(m_rsp_ready),.rsp_data(m_rsp_data),.rsp_error(m_rsp_error),
  .rsp_saturated(m_rsp_saturated),.busy(m_busy));


 assign t_begin_valid=!leaf_reset&&permit_t_begin&&(state==RAW_BEGIN||state==OUT_BEGIN);
 assign t_write_valid=!leaf_reset&&permit_t_write&&(state==RAW_WRITE||state==OUT_WRITE);
 assign t_write_index=state==RAW_WRITE ? {2'd0,raw_index} : {1'd0,output_index};
 assign t_commit_valid=!leaf_reset&&permit_t_commit&&(state==RAW_COMMIT||state==OUT_COMMIT);
 assign t_release_valid=!leaf_reset&&permit_t_release&&(state==RAW_RELEASE||state==OUT_RELEASE);
 assign raw_meta_ok=t_owner==2'd1&&t_generation==job_generation_hold&&t_word_count==10'd256&&
  t_read_index=={2'd0,group_index,row_index}&&t_read_last==(group_index==7'd127&&row_index);
 assign out_meta_ok=t_owner==2'd2&&t_generation==job_generation_hold&&t_word_count==10'd256&&
  t_read_index=={1'd0,output_index}&&t_read_last==(output_index==9'd255);
 // No head phase consumes raw T. Its original first word and lease metadata
 // must remain visible throughout Norm, parameter move, heads and context wait.
 assign head_t_violation=raw_saved&&stage!=WO&&stage!=RESIDUAL&&stage!=OUTPUT&&
  (!t_read_valid||t_read_index!=0||t_read_last||t_owner!=2'd1||
   t_generation!=job_generation_hold||t_word_count!=10'd256);
 assign t_read_take=!leaf_reset&&!t_protocol_error&&permit_t_read&&
  ((state==RAW_CAPTURE&&t_read_valid&&raw_meta_ok)||(state==OUT_DRAIN&&out_valid&&out_ready));
 transaction6k u_t(
  .clk(clk),.reset(leaf_reset),.begin_valid(t_begin_valid),.begin_ready(t_begin_ready),
  .begin_owner(state==RAW_BEGIN ? 2'd1 : 2'd2),.begin_generation(job_generation_hold),.begin_words(10'd256),
  .write_valid(t_write_valid),.write_ready(t_write_ready),.write_index(t_write_index),.write_data(held_data),
  .commit_valid(t_commit_valid),.commit_ready(t_commit_ready),.revoke_valid(1'b0),.revoke_ready(),
  .read_valid(t_read_valid),.read_take(t_read_take),.read_index(t_read_index),.read_data(t_read_data),.read_last(t_read_last),
  .owner(t_owner),.generation(t_generation),.word_count(t_word_count),
  .release_valid(t_release_valid),.release_ready(t_release_ready),.busy(t_busy),.sealed(t_sealed),
  .committed(t_committed),.protocol_error(t_protocol_error),.debug_state(t_state));

 task automatic memory_op;
  input write_op;input [9:0] addr;input [127:0] data;input [4:0] tag;
  begin owner<=OWNER_LOCAL;local_write<=write_op;local_addr<=addr;held_data<=data;local_tag<=tag;state<=LOCAL_REQ;end
 endtask
 task automatic issue_n;
  input [1:0] mode;input [15:0] count;input [9:0] src,gamma,exp_addr,dst;
  begin owner<=OWNER_N;n_mode_hold<=mode;n_count_hold<=count;
   n_src_hold<=src;n_gamma_hold<=gamma;n_exp_hold<=exp_addr;n_dst_hold<=dst;state<=N_REQ;end
 endtask
 task automatic begin_m;
  begin owner<=OWNER_LOCAL;m_phase<=MC_CLEAR;read_slot<=0;tile_index<=0;state<=M_CMD;end
 endtask
 task automatic begin_a;
  begin tile_index<=0;memory_op(1'b0,a_source(2'd0,1'b0),128'd0,L_A_R0);end
 endtask
 task automatic begin_rope;
  begin memory_op(1'b0,10'd288+{5'd0,token_index,4'd0}+{7'd0,rope_group[3:1]},128'd0,L_ROPE_R0);end
 endtask
 task automatic empty_job;
  begin
   state<=WAIT_JOB;stage<=IN_NORM;owner<=OWNER_LOCAL;matrix<=0;group_index<=0;chunk_index<=0;
   tile_index<=0;m_phase<=0;read_slot<=0;copy_index<=0;output_index<=0;column_index<=0;
   input_index<=0;output_count<=0;token_index<=0;q_head<=0;rope_group<=0;weight_index<=0;
   frame_active<=0;frame_stored<=0;running<=0;error_latched<=0;saturation_latched<=0;
   raw_saved<=0;padding_live<=0;raw_index<=0;row_index<=0;kv_head<=0;pad_index<=0;context_words<=0;
   local_write<=0;local_addr<=0;local_tag<=0;job_generation_hold<=0;version_hold<=0;request_seq<=0;
   held_data<=0;v_hold0<=0;v_hold1<=0;m_low_half<=0;
   n_mode_hold<=0;n_count_hold<=0;n_src_hold<=0;n_gamma_hold<=0;n_exp_hold<=0;n_dst_hold<=0;
  end
 endtask
 task automatic fail_job;
  begin state<=DONE;owner<=OWNER_LOCAL;frame_stored<=0;running<=0;raw_saved<=0;
   error_latched<=1;internal_reset<=1;end
 endtask
 always @(posedge clk)begin
  if(reset)begin empty_job();internal_reset<=0;end
  else begin
   internal_reset<=0;
   if(abort)begin
    if(state==DONE)begin if(done_ready)empty_job();end
    else if(frame_active)fail_job();
    else begin empty_job();internal_reset<=1;end
   end else if(frame_active&&state!=DONE&&(t_protocol_error||padding_violation||head_t_violation))fail_job();
   else case(state)
    WAIT_JOB:if(job_valid&&job_ready)begin
     frame_active<=1;job_generation_hold<=job_generation;version_hold<=weights_version;state<=INPUT;
    end
    INPUT:if(input_fire)begin
     if(!input_meta_ok)fail_job();else begin held_data<=in_data;state<=INPUT_REQ;end
    end
    INPUT_REQ:if(h_req_valid&&h_req_ready)state<=INPUT_RSP;
    INPUT_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();
     else if(input_index==9'd447)begin frame_stored<=1;state<=STORED;end
     else begin input_index<=input_index+1'b1;state<=INPUT;end
    end
    STORED:if(start_fire)begin
     running<=1;stage<=IN_NORM;token_index<=0;group_index<=0;row_index<=0;raw_index<=0;state<=RAW_BEGIN;
    end
    LOCAL_REQ:if(h_req_valid&&h_req_ready)state<=LOCAL_RSP;
    LOCAL_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();else case(local_tag)
      L_PARAM_R:memory_op(1'b1,10'd128+{4'd0,copy_index},h_rsp_data,L_PARAM_W);
      L_PARAM_W:if(copy_index==6'd63)begin
       stage<=PAD_A;pad_index<=0;memory_op(1'b1,10'd322,128'd0,L_PAD_A);
      end else begin copy_index<=copy_index+1'b1;memory_op(1'b0,10'd513+{4'd0,copy_index},128'd0,L_PARAM_R);end
      L_A_R0:memory_op(1'b1,a_stage(tile_index,2'd0),h_rsp_data,L_A_W0);
      L_A_W0:memory_op(1'b0,a_source(tile_index,1'b1),128'd0,L_A_R1);
      L_A_R1:memory_op(1'b1,a_stage(tile_index,2'd1),h_rsp_data,L_A_W1);
      L_PAD_A:if(pad_index==3'd7)begin
       padding_live<=1;stage<=PROJECTION;matrix<=0;kv_head<=0;q_head<=0;group_index<=0;chunk_index<=0;begin_m();
      end else begin
       pad_index<=pad_index+1'b1;
       memory_op(1'b1,padding_addr(pad_index+3'd1),128'd0,L_PAD_A);
      end
      L_A_W1:if(stage!=PV&&tile_index!=2'd3)begin
       tile_index<=tile_index+1'b1;memory_op(1'b0,a_source(tile_index+2'd1,1'b0),128'd0,L_A_R0);
      end else if(linear_stage)begin weight_index<=0;state<=WEIGHT_REQ;end
      else if(stage==QK)begin
       tile_index<=0;memory_op(1'b0,10'd192+{2'd0,chunk_index,2'd0},128'd0,L_K_R0);
      end else memory_op(1'b0,10'd224+{3'd0,group_index},128'd0,L_V_R0);
      L_WEIGHT_W:if(weight_index==4'd15)begin request_seq<=request_seq+1'b1;state<=LOAD_CMD;end
       else begin weight_index<=weight_index+1'b1;state<=WEIGHT_RX;end
      L_K_R0:memory_op(1'b1,10'd336+{5'd0,tile_index,3'd0},h_rsp_data,L_K_W0);
      L_K_W0:memory_op(1'b0,10'd208+{2'd0,chunk_index,2'd0}+{8'd0,tile_index},128'd0,L_K_R1);
      L_K_R1:memory_op(1'b1,10'd337+{5'd0,tile_index,3'd0},h_rsp_data,L_K_W1);
      L_K_W1:begin column_index<=2;memory_op(1'b1,10'd338+{5'd0,tile_index,3'd0},128'd0,L_K_ZERO);end
      L_K_ZERO:if(column_index!=3'd7)begin
       column_index<=column_index+1'b1;
       memory_op(1'b1,10'd337+{5'd0,tile_index,3'd0}+{7'd0,column_index},128'd0,L_K_ZERO);
      end else if(tile_index!=2'd3)begin
       tile_index<=tile_index+1'b1;
       memory_op(1'b0,10'd193+{2'd0,chunk_index,2'd0}+{8'd0,tile_index},128'd0,L_K_R0);
      end else state<=LOAD_CMD;
      L_V_R0:begin v_hold0<=h_rsp_data;memory_op(1'b0,10'd240+{3'd0,group_index},128'd0,L_V_R1);end
      L_V_R1:begin
       v_hold1<=h_rsp_data;column_index<=0;memory_op(1'b1,10'd336,transpose_v(v_hold0,h_rsp_data,3'd0),L_V_COL);
      end
      L_V_COL:if(column_index==3'd7)state<=LOAD_CMD;
       else begin column_index<=column_index+1'b1;
        memory_op(1'b1,10'd337+{7'd0,column_index},transpose_v(v_hold0,v_hold1,column_index+3'd1),L_V_COL);end
      L_M_SAVE:begin
       if(stage==PV)context_words<=context_words+1'b1;
       if(stage==QK)begin
        if(read_slot==0)begin read_slot<=2;state<=M_CMD;end
        else begin stage<=SOFTMAX;token_index<=0;issue_n(2'd0,16'd1,10'd368,10'd0,10'd370,10'd372);end
       end else if(read_slot==1)begin read_slot<=2;state<=M_CMD;end
       else if(stage==WO)begin row_index<=0;stage<=RESIDUAL;state<=RAW_CAPTURE;end
       else if(group_index!=7'd15)begin group_index<=group_index+1'b1;chunk_index<=0;begin_m();end
       else if(stage==PROJECTION)begin
        if(matrix==1)begin matrix<=2;q_head<={kv_head,1'b0};group_index<=0;chunk_index<=0;begin_m();end
        else begin stage<=HEAD_NORM;token_index<=0;
         issue_n(2'd1,16'd128,projection_save_base,matrix==0 ? 10'd144 : 10'd128,10'd0,10'd288);end
       end else if(!q_head[0])begin
        q_head<=q_head+1'b1;matrix<=2;stage<=PROJECTION;group_index<=0;chunk_index<=0;begin_m();
       end else if(kv_head!=3'd7)begin
        kv_head<=kv_head+1'b1;q_head<=q_head+1'b1;matrix<=0;stage<=PROJECTION;group_index<=0;chunk_index<=0;begin_m();
       end else if(context_words!=10'd511)fail_job();
       else state<=CONTEXT_READY;
      end
      L_ROPE_R0:begin v_hold0<=h_rsp_data;
       memory_op(1'b0,10'd296+{5'd0,token_index,4'd0}+{7'd0,rope_group[3:1]},128'd0,L_ROPE_R1);end
      L_ROPE_R1:memory_op(1'b1,10'd374,pair_rope(v_hold0,h_rsp_data,rope_group[0]),L_ROPE_W);
      L_ROPE_W:begin owner<=OWNER_E;state<=E_REQ;end
      L_OUTPUT_R:begin held_data<=h_rsp_data;state<=OUTPUT_HOLD;end
      default:fail_job();
     endcase
    end
    N_REQ:if(n_req_valid&&n_req_ready)state<=N_RSP;
    N_RSP:if(n_rsp_valid&&n_rsp_ready)begin
     saturation_latched<=saturation_latched||n_rsp_saturated;
     if(n_rsp_error)fail_job();
     else if(stage==IN_NORM)begin
      if(!token_index)begin token_index<=1;issue_n(2'd1,16'd1024,10'd128,10'd256,10'd0,10'd0);end
      else begin stage<=PARAM_MOVE;copy_index<=0;memory_op(1'b0,10'd512,128'd0,L_PARAM_R);end
     end else if(stage==HEAD_NORM)begin
      if(!token_index)begin token_index<=1;
       issue_n(2'd1,16'd128,head_src_base+10'd16,matrix==0 ? 10'd144 : 10'd128,10'd0,10'd304);end
      else begin stage<=ROPE;token_index<=0;rope_group<=0;memory_op(1'b0,10'd288,128'd0,L_ROPE_R0);end
     end else begin
      if(!token_index)begin token_index<=1;issue_n(2'd0,16'd2,10'd369,10'd0,10'd371,10'd373);end
      else begin stage<=PV;group_index<=0;chunk_index<=0;begin_m();end
     end
    end
    E_REQ:if(e_req_valid&&e_req_ready)state<=E_RSP;
    E_RSP:if(e_rsp_valid&&e_rsp_ready)begin
     saturation_latched<=saturation_latched||e_rsp_saturated;
     if(e_rsp_error)fail_job();
     else if(stage==RESIDUAL)begin
      if(!row_index)begin row_index<=1;owner<=OWNER_LOCAL;state<=RAW_CAPTURE;end
      else if(group_index==7'd127)begin owner<=OWNER_LOCAL;state<=RAW_RELEASE;end
      else begin stage<=WO;group_index<=group_index+1'b1;chunk_index<=0;row_index<=0;begin_m();end
     end else if(rope_group!=4'd15)begin
      rope_group<=rope_group+1'b1;
      memory_op(1'b0,10'd288+{5'd0,token_index,4'd0}+(({6'd0,rope_group}+10'd1)>>1),128'd0,L_ROPE_R0);
     end else if(!token_index)begin
      token_index<=1;rope_group<=0;memory_op(1'b0,10'd304,128'd0,L_ROPE_R0);
     end else if(matrix==0)begin stage<=PROJECTION;matrix<=1;group_index<=0;chunk_index<=0;begin_m();end
     else begin stage<=QK;chunk_index<=0;group_index<=0;begin_m();end
    end
    WEIGHT_REQ:if(wreq_valid&&wreq_ready)begin weight_index<=0;state<=WEIGHT_RX;end
    WEIGHT_RX:if(w_valid&&w_ready)begin
     if(!weight_meta_ok)fail_job();else memory_op(1'b1,10'd336+{6'd0,weight_index},w_data,L_WEIGHT_W);
    end
    M_CMD:if(m_cmd_valid&&m_cmd_ready)state<=M_RSP;
    M_RSP:if(m_rsp_valid&&m_rsp_ready)begin
     saturation_latched<=saturation_latched||m_rsp_saturated;
     if(m_rsp_error||(m_phase==MC_EXEC&&m_rsp_data[7:0]!=0))fail_job();
     else case(m_phase)
      MC_CLEAR:begin m_phase<=MC_SCALE;state<=M_CMD;end
      MC_SCALE:begin_a();
      MC_EXEC:if((stage==PROJECTION&&chunk_index!=6'd31)||(stage==WO&&chunk_index!=6'd63)||(stage==QK&&chunk_index!=6'd3))begin
       chunk_index<=chunk_index+1'b1;tile_index<=0;
       // The next chunk address must use the incremented chunk, not old NBA state.
       if(stage==WO)memory_op(1'b0,10'd516+{2'd0,chunk_index,2'd0},128'd0,L_A_R0);
       else if(stage==PROJECTION)memory_op(1'b0,10'd388+{2'd0,chunk_index,2'd0},128'd0,L_A_R0);
       else memory_op(1'b0,10'd260+{2'd0,chunk_index,2'd0},128'd0,L_A_R0);
      end else begin m_phase<=MC_READ;read_slot<=0;state<=M_CMD;end
      MC_READ:if(stage==QK)begin
       memory_op(1'b1,result_addr(read_slot[1]),{96'd0,m_rsp_data[47:32],m_rsp_data[15:0]},L_M_SAVE);
      end else if(!read_slot[0])begin m_low_half<=pack_m_four(m_rsp_data);read_slot<=read_slot+1'b1;state<=M_CMD;end
      else memory_op(1'b1,result_addr(read_slot[1]),{pack_m_four(m_rsp_data),m_low_half},L_M_SAVE);
      default:fail_job();
     endcase
    end
    LOAD_CMD:if(load_valid&&load_ready)state<=LOAD_RSP;
    LOAD_RSP:if(load_done_valid&&load_done_take)begin
     if(load_done_error)fail_job();else begin m_phase<=MC_EXEC;state<=M_CMD;end
    end
    RAW_BEGIN:if(t_begin_valid&&t_begin_ready)state<=RAW_READ_REQ;
    RAW_READ_REQ:if(h_req_valid&&h_req_ready)state<=RAW_READ_RSP;
    RAW_READ_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();else begin held_data<=h_rsp_data;state<=RAW_WRITE;end
    end
    RAW_WRITE:if(t_write_valid&&t_write_ready)begin
     if(raw_index==8'd255)state<=RAW_COMMIT;
     else begin raw_index<=raw_index+1'b1;state<=RAW_READ_REQ;end
    end
    RAW_COMMIT:if(t_commit_valid&&t_commit_ready)state<=RAW_SAVED;
    RAW_SAVED:if(t_read_valid)begin
     if(!raw_meta_ok)fail_job();
     else begin raw_saved<=1;issue_n(2'd1,16'd1024,10'd0,10'd256,10'd0,10'd384);end
    end
    CONTEXT_READY:if(context_complete&&permit_context_to_wo)begin
     stage<=WO;matrix<=3;group_index<=0;chunk_index<=0;row_index<=0;begin_m();
    end
    RAW_CAPTURE:if(t_read_valid)begin
     if(!raw_meta_ok)fail_job();
     else if(t_read_take)begin held_data<=t_read_data;state<=RAW_SAVE_REQ;end
    end
    RAW_SAVE_REQ:if(h_req_valid&&h_req_ready)state<=RAW_SAVE_RSP;
    RAW_SAVE_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();else begin owner<=OWNER_E;state<=E_REQ;end
    end
    RAW_RELEASE:if(t_release_valid&&t_release_ready)begin
     raw_saved<=0;output_index<=0;stage<=OUTPUT;state<=OUT_BEGIN;
    end
    OUT_BEGIN:if(t_begin_valid&&t_begin_ready)state<=OUT_READ_REQ;
    OUT_READ_REQ:if(h_req_valid&&h_req_ready)state<=OUT_READ_RSP;
    OUT_READ_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();else begin held_data<=h_rsp_data;state<=OUT_WRITE;end
    end
    OUT_WRITE:if(t_write_valid&&t_write_ready)begin
     if(output_index==9'd255)state<=OUT_COMMIT;
     else begin output_index<=output_index+1'b1;state<=OUT_READ_REQ;end
    end
    OUT_COMMIT:if(t_commit_valid&&t_commit_ready)begin output_index<=0;state<=OUT_DRAIN;end
    OUT_DRAIN:if(t_read_valid)begin
     if(!out_meta_ok)fail_job();
     else if(out_valid&&out_ready)begin
      output_count<=output_count+1'b1;
      if(output_index==9'd255)state<=OUT_RELEASE;
      else output_index<=output_index+1'b1;
     end
    end
    OUT_RELEASE:if(t_release_valid&&t_release_ready)begin running<=0;state<=DONE;end
    DONE:if(done_valid&&done_ready)empty_job();
    default:begin if(frame_active)fail_job();else begin empty_job();internal_reset<=1;end end
   endcase
  end
 end
endmodule
