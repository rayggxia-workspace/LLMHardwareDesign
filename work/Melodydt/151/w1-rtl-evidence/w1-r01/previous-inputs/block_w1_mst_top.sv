// Issue151 W1: fixed S8 DOT8 program with an eight-beat variable tensor frame.
// New active logic must be prefabricated; no runtime shape/address/op program.
// Leaf source is PR144 7078786; M/S/T bytes equal the P1 643c6012 source.
// No E/G, runtime type system, external-memory service or full-model program.
module block_w1_mst_top(
 input wire clk,reset,abort,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 output wire input_stored,
 input wire start_valid,output wire start_ready,
 output wire busy,output wire done_valid,input wire done_ready,
 output wire done_error,
 output wire out_valid,input wire out_ready,
 output wire [127:0] out_data,output wire [9:0] out_index,
 output wire out_last
);
 localparam [3:0] M_CLEAR=0,M_SCALE=1,INPUT_CHECK=2,LOAD=3,M_EXEC=4,
                  M_STORE=5,T_BEGIN=6,T_FILL=7,T_COMMIT=8,T_DRAIN=9;
 localparam IDLE=0,M_CMD=1,M_RSP=2,S_REQ=3,S_RSP=4,
            LOAD_CMD=5,LOAD_RSP=6,BEGIN_T=7,WRITE_T=8,COMMIT_T=9,
            DRAIN_T=10,RELEASE_T=11,INPUT_REQ=12,INPUT_RSP=13;
 reg [3:0] state,operation;
 reg [3:0] step;
 reg [127:0] held_data;
 // The input index advances only after the actual S write ACK is consumed.
 reg [3:0] input_index;
 reg frame_active,frame_stored,launched;
 wire mother_start_ready,mother_busy;
 wire mother_start_valid=start_valid&&frame_stored&&!launched;
 assign start_ready=!leaf_reset&&frame_stored&&!launched&&mother_start_ready;
 assign input_stored=!reset&&!abort&&frame_stored;
 // Busy spans the first accepted input through completion consumption.
 assign busy=!reset&&(frame_active||mother_busy);
 assign in_ready=!leaf_reset&&!mother_busy&&!frame_stored&&!launched&&
                  state==IDLE&&!service_rsp_valid;
 wire input_fire=in_valid&&in_ready;
 wire start_fire=start_valid&&start_ready;
 wire service_valid,service_ready,service_rsp_ready;
 wire [3:0] service_op;
 wire [9:0] service_arg;
 reg service_rsp_valid,service_rsp_error;
 wire t_protocol_error;
 // Named constant wires are TB-only force points. They are tied on in hardware.
 // Gating is symmetric on both ends of each handshake; data is never changed.
 wire permit_m_cmd=1'b1;
 wire permit_m_rsp=1'b1;
 wire permit_load=1'b1;
 wire permit_s_rsp=1'b1;
 wire permit_s_req=1'b1;
 wire fatal_service=service_rsp_valid&&service_rsp_error;
 wire fatal_native=t_protocol_error&&state!=IDLE;
 wire coordinated_abort=abort||fatal_service||fatal_native;
 wire leaf_reset=reset||coordinated_abort;

 block_w1_mother_rom u_mother(
  .clk(clk),.reset(reset),.abort(coordinated_abort),
  .start_valid(mother_start_valid),.start_ready(mother_start_ready),.busy(mother_busy),
  .done_valid(done_valid),.done_ready(done_ready),.done_error(done_error),
  .service_valid(service_valid),.service_ready(service_ready),
  .service_op(service_op),.service_arg(service_arg),
  .service_rsp_valid(service_rsp_valid),.service_rsp_ready(service_rsp_ready),
  .service_rsp_error(service_rsp_error));

 wire h_req_ready,h_rsp_valid,h_rsp_error;
 wire [127:0] h_rsp_data;
 wire h_req_valid=!leaf_reset&&(state==S_REQ||state==INPUT_REQ)&&permit_s_req;
 wire h_req_write=state==INPUT_REQ||operation!=T_FILL;
 wire [9:0] h_req_addr=state==INPUT_REQ?(10'd448+{6'd0,input_index}):
                                           (10'd456+{6'd0,step});
 wire [127:0] h_req_data;
 wire h_rsp_ready=!leaf_reset&&(state==S_RSP||state==INPUT_RSP);
 wire s_req,s_we,s_ready,s_valid,s_take;
 wire [9:0] s_addr;
 wire [127:0] s_din,s_dout;
 wire helper_s_take;
 // Beat0 carries the eight S8 A values; all A padding is written as zero.
 // Beats4..7 carry eight n-major B columns with eight S8 values each.
 function automatic [127:0] canonical_input;
  input [3:0] index;
  input [127:0] data;
  begin
   if(index==0)canonical_input={64'd0,data[63:0]};
   else if(index<4)canonical_input=128'd0;
   else canonical_input=data;
  end
 endfunction
 assign h_req_data=held_data;
 assign s_take=helper_s_take&&permit_s_rsp;
 block_p2_s_ctrl u_s_ctrl(
  .clk(clk),.resetn(!leaf_reset),
  .req_valid(h_req_valid),.req_ready(h_req_ready),
  .req_write(h_req_write),.req_addr(h_req_addr),.req_data(h_req_data),
  .rsp_valid(h_rsp_valid),.rsp_ready(h_rsp_ready),
  .rsp_data(h_rsp_data),.rsp_error(h_rsp_error),
  .s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),
  .s_ready(s_ready),.s_rsp_valid(s_valid&&permit_s_rsp),
  .s_rsp_ready(helper_s_take),.s_dout(s_dout));

 wire load_ready,load_done_valid,load_done_error,loader_busy;
 wire a_valid,a_ready,a_bank,a_wide;
 wire [2:0] a_row;
 wire [1:0] a_tile;
 wire [127:0] a_data;
 wire b_valid,b_ready,b_bank,b_wide,b_half;
 wire [1:0] b_tile;
 wire [511:0] b_data;
 wire load_valid=!leaf_reset&&state==LOAD_CMD&&permit_load;
 wire load_done_take=!leaf_reset&&state==LOAD_RSP;
 block_feed_s_macro u_s(
  .clk(clk),.reset(leaf_reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),
  .ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),
  .load_valid(load_valid),.load_ready(load_ready),
  .load_bank(1'b0),.load_rows(4'd1),.load_tiles(3'd1),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),
  .load_a_base(10'd448),.load_b_base(10'd452),
  .done_valid(load_done_valid),.done_take(load_done_take),
  .done_error(load_done_error),.busy(loader_busy),
  .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),
  .a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),
  .b_wide(b_wide),.b_half(b_half),.b_data(b_data));

 wire m_cmd_ready,m_rsp_valid,m_rsp_error,m_rsp_saturated,m_busy;
 wire [127:0] m_rsp_data;
 wire m_cmd_valid=!leaf_reset&&state==M_CMD&&permit_m_cmd;
 wire m_rsp_ready=!leaf_reset&&state==M_RSP&&permit_m_rsp;
 wire [3:0] m_cmd_op=operation==M_CLEAR?4'd6:
                        operation==M_SCALE?4'd4:
                        operation==M_EXEC?4'd10:4'd3;
 wire [5:0] m_cmd_index=operation==M_STORE?{2'd0,step}:6'd0;
 wire [63:0] m_cmd_data=operation==M_SCALE?64'd1:
                          operation==M_EXEC?64'h9884:64'd0;
 block_v2_m u_m(
  .clk(clk),.reset(leaf_reset),
  .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),
  .a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),
  .b_wide(b_wide),.b_half(b_half),.b_data(b_data),
  .cmd_valid(m_cmd_valid),.cmd_ready(m_cmd_ready),.cmd_op(m_cmd_op),
  .cmd_index(m_cmd_index),.cmd_data(m_cmd_data),
  .rsp_valid(m_rsp_valid),.rsp_ready(m_rsp_ready),.rsp_data(m_rsp_data),
  .rsp_error(m_rsp_error),.rsp_saturated(m_rsp_saturated),.busy(m_busy));

 wire t_begin_ready,t_write_ready,t_commit_ready,t_release_ready;
 wire t_read_valid,t_read_last;
 wire [9:0] t_read_index;
 wire [127:0] t_read_data;
 wire t_busy,t_sealed,t_committed;
 wire [1:0] t_owner;
 wire [31:0] t_generation;
 wire [9:0] t_word_count;
 wire [2:0] t_state;
 wire t_read_take=!leaf_reset&&state==DRAIN_T&&out_ready;
 assign out_valid=!leaf_reset&&state==DRAIN_T&&t_read_valid;
 assign out_data=t_read_data;
 assign out_index=t_read_index;
 assign out_last=out_valid&&t_read_last;
 transaction6k u_t(
  .clk(clk),.reset(leaf_reset),
  .begin_valid(!leaf_reset&&state==BEGIN_T),.begin_ready(t_begin_ready),
  .begin_owner(2'd0),.begin_generation(32'd1),.begin_words(10'd4),
  .write_valid(!leaf_reset&&state==WRITE_T),.write_ready(t_write_ready),
  .write_index({6'd0,step}),.write_data(held_data),
  .commit_valid(!leaf_reset&&state==COMMIT_T),.commit_ready(t_commit_ready),
  .revoke_valid(1'b0),.revoke_ready(),
  .read_valid(t_read_valid),.read_take(t_read_take),.read_index(t_read_index),
  .read_data(t_read_data),.read_last(t_read_last),
  .owner(t_owner),.generation(t_generation),.word_count(t_word_count),
  .release_valid(!leaf_reset&&state==RELEASE_T),.release_ready(t_release_ready),
  .busy(t_busy),.sealed(t_sealed),.committed(t_committed),
  .protocol_error(t_protocol_error),.debug_state(t_state));

 assign service_ready=!leaf_reset&&state==IDLE&&!service_rsp_valid;
 task automatic finish_service;
  input error;
  begin service_rsp_valid<=1;service_rsp_error<=error;state<=IDLE;end
 endtask
 always @(posedge clk)begin
  if(leaf_reset)begin
   state<=IDLE;operation<=M_CLEAR;step<=0;held_data<=0;
   service_rsp_valid<=0;service_rsp_error<=0;
  end else begin
   if(service_rsp_valid&&service_rsp_ready)service_rsp_valid<=0;
   case(state)
    IDLE:if(input_fire)begin
     held_data<=canonical_input(input_index,in_data);state<=INPUT_REQ;
    end else if(service_valid&&service_ready)begin
     operation<=service_op;step<=0;
     if(service_arg!=0)finish_service(1'b1);
     else case(service_op)
      M_CLEAR,M_SCALE,M_EXEC,M_STORE:state<=M_CMD;
      INPUT_CHECK:finish_service(!frame_stored||!launched);
      LOAD:state<=LOAD_CMD;
      T_BEGIN:state<=BEGIN_T;
      T_FILL:state<=S_REQ;
      T_COMMIT:state<=COMMIT_T;
      T_DRAIN:state<=DRAIN_T;
      default:finish_service(1'b1);
     endcase
    end
    // No service instruction can run until the stored frame was started.
    INPUT_REQ:if(h_req_valid&&h_req_ready)state<=INPUT_RSP;
    INPUT_RSP:if(h_rsp_valid&&h_rsp_ready)state<=IDLE;
    M_CMD:if(m_cmd_valid&&m_cmd_ready)state<=M_RSP;
    M_RSP:if(m_rsp_valid&&m_rsp_ready)begin
     if(m_rsp_error||(operation==M_EXEC&&m_rsp_data[7:0]!=0))finish_service(1'b1);
     else if(operation==M_STORE)begin held_data<=m_rsp_data;state<=S_REQ;end
     else finish_service(1'b0);
    end
    S_REQ:if(h_req_valid&&h_req_ready)state<=S_RSP;
    S_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)finish_service(1'b1);
     else case(operation)
      M_STORE:if(step==3)finish_service(1'b0);
              else begin step<=step+1'b1;state<=M_CMD;end
      T_FILL:begin held_data<=h_rsp_data;state<=WRITE_T;end
      default:finish_service(1'b1);
     endcase
    end
    LOAD_CMD:if(load_valid&&load_ready)state<=LOAD_RSP;
    LOAD_RSP:if(load_done_valid&&load_done_take)finish_service(load_done_error);
    BEGIN_T:if(t_begin_ready)finish_service(1'b0);
    WRITE_T:if(t_write_ready)begin
     if(step==3)finish_service(1'b0);
     else begin step<=step+1'b1;state<=S_REQ;end
    end
    COMMIT_T:if(t_commit_ready)finish_service(1'b0);
    DRAIN_T:if(out_valid&&out_ready&&out_last)state<=RELEASE_T;
    RELEASE_T:if(t_release_ready)finish_service(1'b0);
    default:finish_service(1'b1);
   endcase
  end
 end
 // Frame ownership is independent of the counted service child. Reset and
 // abort invalidate the marker, but cannot roll back an already accepted RAM
 // write or an output prefix already consumed by the external receiver.
 always @(posedge clk)begin
  if(reset)begin
   input_index<=0;frame_active<=0;frame_stored<=0;launched<=0;
  end else if(coordinated_abort)begin
   input_index<=0;frame_active<=0;frame_stored<=0;launched<=0;
  end else if(done_valid&&done_ready)begin
   input_index<=0;frame_active<=0;frame_stored<=0;launched<=0;
  end else begin
   if(input_fire)frame_active<=1;
   if(state==INPUT_RSP&&h_rsp_valid&&h_rsp_ready)begin
    if(input_index==7)frame_stored<=1;
    else input_index<=input_index+1'b1;
   end
   if(start_fire)launched<=1;
  end
 end
endmodule
