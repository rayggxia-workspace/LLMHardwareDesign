  localparam [9:0] CONSUMER_WORD=10'd19;
  wire r_read,r_read_ready,r_bank,r_take,r_load,r_load_ready,r_cmd,r_cmd_ready,r_role,r_rsp_valid,r_rsp_ready,r_error;
  wire [127:0] r_coefficient,r_data;
  wire [511:0] r_result;
  wire n_read_ready,n_read_valid,n_load_ready;
  wire host_r=host_valid && (host_device==2 || host_device==3);
  reg host_read_pending=0,host_load_ack=0;
  reg [127:0] host_load_data;
  wire g_valid,g_ready,g_out_valid,g_take,g_error,g_sat;
  wire [31:0] g_x,g_y;
  wire active_bank,candidate_valid,publish,receipt_reject;
  wire [31:0] generation;
  wire consumer_valid,consumer_ready,receipt_valid,receipt_ready,receipt_error;
  wire [127:0] consumer_identity,consumer_data,receipt_identity;
  int g_req_age=0,g_rsp_age=0;
  wire g_req_gate=g_req_age>=int'(stall_i)*2;
  wire g_rsp_gate=g_rsp_age>=int'(stall_i)*3;
  wire [8:0] rows=$test$plusargs("CRFAULT") && svc_rsp_job_i==7 ? 9'd0 : 9'd1;
  assign e_op=$test$plusargs("CEFAULT") && svc_rsp_job_i==7 ? 4'd14 : 4'd13;
  assign e_shift=5'd6;
  assign r_read_ready=n_read_ready && !host_r;
  assign r_load_ready=n_load_ready && !host_r;

  lc_c_state_adapter adapter(
    .clk(clk_i),.rst_n(rst_ni),.svc_valid(svc_req_valid_o && svc_req_kind_o==0),.svc_ready(svc_req_ready_i),
    .svc_resource(svc_req_resource_o),.svc_token(svc_req_token_o),.svc_sequence(svc_req_sequence_o),
    .svc_job(svc_req_job_o),.svc_epoch(svc_req_epoch_o),.svc_task_sequence(svc_req_task_sequence_o),
    .svc_desc(svc_req_descriptor_o),.rsp_valid(svc_rsp_valid_i),.rsp_ready(svc_rsp_ready_o),
    .rsp_token(svc_rsp_token_i),.rsp_sequence(svc_rsp_sequence_i),.rsp_job(svc_rsp_job_i),
    .rsp_epoch(svc_rsp_epoch_i),.rsp_task_sequence(svc_rsp_task_sequence_i),.rsp_status(svc_rsp_status_i),
    .rsp_read_bytes(svc_rsp_read_bytes_i),.rsp_write_bytes(svc_rsp_write_bytes_i),.rsp_saturated(svc_rsp_saturated_i),
    .r_read(r_read),.r_read_ready(r_read_ready),.r_bank(r_bank),.r_read_rsp(n_read_valid && !host_read_pending),
    .r_read_take(r_take),.r_data(r_data),.r_load(r_load),.r_load_ready(r_load_ready),.r_coefficient(r_coefficient),
    .r_cmd(r_cmd),.r_cmd_ready(r_cmd_ready),.r_role(r_role),.r_rsp_valid(r_rsp_valid),.r_rsp_ready(r_rsp_ready),.r_error(r_error),
    .e_valid(e_valid),.e_ready(e_ready && e_req_gate),.e_a(e_a),
    .e_rsp_valid(e_out_valid && e_rsp_gate),.e_rsp_ready(e_take),.e_result(e_y),.e_error(e_error),.e_saturated(e_sat),
    .g_valid(g_valid),.g_ready(g_ready && g_req_gate),.g_x(g_x),
    .g_rsp_valid(g_out_valid && g_rsp_gate),.g_rsp_ready(g_take),.g_result(g_y),.g_error(g_error),.g_saturated(g_sat),
    .s_valid(s_valid),.s_ready(s_ready),.s_write(s_write),.s_word(s_word),.s_data(s_data),
    .s_rsp_valid(native_s_rsp_valid),.s_rsp_ready(s_take),.s_rsp_data(native_s_rsp_data),
    .consumer_valid(consumer_valid),.consumer_ready(consumer_ready),.consumer_identity(consumer_identity),
    .consumer_data(consumer_data),.receipt_valid(receipt_valid),.receipt_ready(receipt_ready),
    .receipt_identity(receipt_identity),.receipt_error(receipt_error),.active_bank(active_bank),
    .generation(generation),.candidate_valid(candidate_valid),.publish(publish),.receipt_reject(receipt_reject));
  assign e_b=0;

  r_stream_local #(.WORDS(256)) macro_r(
    .clk(clk_i),.reset(!rst_ni),.load_valid((host_r && host_write) || r_load),.load_ready(n_load_ready),
    .load_target(host_r ? {2'b0,host_device[0]} : 3'd5),.load_index(host_r ? host_word : 10'd0),
    .load_data(host_r ? host_data : r_coefficient),.rd_bank(host_r ? host_device[0] : r_bank),
    .rd_index(host_r ? host_word : 10'd0),.rd_valid((host_r && !host_write) || r_read),
    .rd_ready(n_read_ready),.rd_rsp_valid(n_read_valid),.rd_rsp_ready(host_read_pending || r_take),.rd_data(r_data),
    .cmd_valid(r_cmd),.cmd_ready(r_cmd_ready),.cmd_op(3'd0),.cmd_rows(rows),.cmd_role(r_role),
    .cmd_clear(1'b0),.cmd_mode(2'b0),.rsp_valid(r_rsp_valid),.rsp_ready(r_rsp_ready),.rsp_error(r_error),.rsp_data(r_result));
  block_v2_g macro_g(.clk(clk_i),.reset(!rst_ni),
    .in_valid(g_valid && g_req_gate),.in_ready(g_ready),.in_fn(3'd0),.in_gated(1'b0),.in_x(g_x),.in_gate(32'b0),
    .out_valid(g_out_valid),.out_ready(g_take && g_rsp_gate),.out_data(g_y),.out_error(g_error),.out_saturated(g_sat));

  // Fixed one-consumer fixture. It must receive an actual S write response
  // before forwarding a receipt. Fault injection affects only that receipt.
  typedef enum logic [2:0] {PEER_IDLE,PEER_WRITE,PEER_STORE,PEER_WRONG,PEER_ACK} peer_t;
  peer_t peer;
  reg [127:0] peer_identity,peer_data,stale_identity;
  reg [31:0] receipt_age;
  wire [1:0] peer_s_ready,peer_s_valid;
  wire [255:0] peer_s_data;
  wire drop_first=$test$plusargs("CLOST") && peer_identity[127:96]==7;
  wire replay_old=$test$plusargs("CLOST") && peer_identity[127:96]==8;
  wire send_wrong=$test$plusargs("CWRONG") || replay_old;
  assign consumer_ready=peer==PEER_IDLE;
  assign receipt_valid=peer==PEER_WRONG || (peer==PEER_ACK && receipt_age>=stall_i*3);
  assign receipt_identity=peer==PEER_WRONG ?
       (replay_old ? stale_identity : peer_identity ^ (128'd1<<64)) : peer_identity;
  assign receipt_error=peer==PEER_ACK && $test$plusargs("CREJECT") && peer_identity[127:96]==7;
  block_local_s_macro #(.CLIENTS(2)) consumer_s(
    .clk(clk_i),.reset(!rst_ni),.req_valid({host_valid && host_device==1,peer==PEER_WRITE}),
    .req_write({host_write,1'b1}),.req_addr({host_word,CONSUMER_WORD}),.req_data({host_data,peer_data}),
    .req_ready(peer_s_ready),.rsp_valid(peer_s_valid),.rsp_ready(2'b11),.rsp_data(peer_s_data),
    .load_valid(1'b0),.load_ready(),.load_bank(1'b0),.load_rows(4'b0),.load_tiles(3'b0),
    .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(10'b0),.load_b_base(10'b0),
    .done_valid(),.done_take(1'b0),.done_error(),.busy(),
    .a_valid(),.a_ready(1'b0),.a_bank(),.a_row(),.a_tile(),.a_wide(),.a_data(),
    .b_valid(),.b_ready(1'b0),.b_bank(),.b_tile(),.b_wide(),.b_half(),.b_data());

  assign extra_ready=host_device==1 ? peer_s_ready[1] : host_write ? n_load_ready : n_read_ready;
  assign extra_ack=host_device==1 ? peer_s_valid[1] : host_load_ack || (host_read_pending && n_read_valid);
  assign extra_result=host_device==1 ? peer_s_data[128+:128] : host_load_ack ? host_load_data : r_data;
  reg prev_bank=0;
  reg [31:0] prev_generation=0;
  always @(posedge clk_i) begin
    if(!rst_ni) begin
      peer<=PEER_IDLE; peer_identity<=0; peer_data<=0; stale_identity<=0; receipt_age<=0;
      host_read_pending<=0; host_load_ack<=0; host_load_data<=0;
      prev_bank<=0; prev_generation<=0;
    end else begin
      host_load_ack<=host_r && host_write && n_load_ready;
      if(host_r && host_write && n_load_ready) host_load_data<=host_data;
      if(host_r && !host_write && n_read_ready) host_read_pending<=1;
      if(host_read_pending && n_read_valid) host_read_pending<=0;
      if(r_read && r_read_ready) $display("JC %0d RREAD %0d",cycle_i,r_bank);
      if(r_take && n_read_valid && !host_read_pending) $display("JC %0d RREAD_RSP %032h",cycle_i,r_data);
      if(r_load && r_load_ready) $display("JC %0d RLOAD %08h",cycle_i,r_coefficient[31:0]);
      if(r_cmd && r_cmd_ready) $display("JC %0d RCMD %0d %0d",cycle_i,r_role,rows);
      if(r_rsp_valid && r_rsp_ready) $display("JC %0d RRSP %0d %0128h",cycle_i,r_error,r_result);
      if(g_valid && !g_req_gate) begin
        g_req_age<=g_req_age+1; $display("JC %0d GIN_H %08h",cycle_i,g_x);
      end
      if(g_valid && g_ready && g_req_gate) begin
        g_req_age<=0; $display("JC %0d GIN %08h",cycle_i,g_x);
      end
      if(g_out_valid && !g_rsp_gate) begin
        g_rsp_age<=g_rsp_age+1; $display("JC %0d GOUT_H %0d %0d %08h",cycle_i,g_error,g_sat,g_y);
      end
      if(g_out_valid && g_take && g_rsp_gate) begin
        g_rsp_age<=0; $display("JC %0d GOUT %0d %0d %08h",cycle_i,g_error,g_sat,g_y);
      end
      if((active_bank!=prev_bank || generation!=prev_generation) && !publish)
        $fatal(1,"C active state changed without publication");
      if(publish) $display("JC %0d PUBLISH %0d %0d",cycle_i,active_bank,generation);
      if(svc_rsp_valid_i && svc_rsp_ready_o)
        $display("JC %0d CSTATE %0d %0d %0d",cycle_i,active_bank,generation,candidate_valid);
      prev_bank<=active_bank; prev_generation<=generation;
      if(receipt_valid && receipt_ready)
        $display("JC %0d RECEIPT %032h %0d %0d",cycle_i,receipt_identity,receipt_error,receipt_reject);
      case(peer)
        PEER_IDLE: if(consumer_valid) begin
          if(!candidate_valid) $fatal(1,"consumer offered without a candidate");
          peer_identity<=consumer_identity; peer_data<=consumer_data; peer<=PEER_WRITE;
          $display("JC %0d CONS %032h %032h",cycle_i,consumer_identity,consumer_data);
        end
        PEER_WRITE: if(peer_s_ready[0]) begin
          peer<=PEER_STORE; $display("JC %0d CWRITE %032h",cycle_i,peer_data);
        end
        PEER_STORE: if(peer_s_valid[0]) begin
          if(peer_s_data[0+:128]!=peer_data) $fatal(1,"consumer S acknowledged different bytes");
          $display("JC %0d CACK %032h",cycle_i,peer_data);
          receipt_age<=0;
          if(drop_first) begin
            stale_identity<=peer_identity; peer<=PEER_IDLE;
            $display("JC %0d CONS_DROP %032h",cycle_i,peer_identity);
          end else peer<=send_wrong ? PEER_WRONG : PEER_ACK;
        end
        PEER_WRONG: if(receipt_ready) peer<=PEER_ACK;
        PEER_ACK: begin
          if(receipt_valid && receipt_ready) peer<=PEER_IDLE;
          else if(!receipt_valid) receipt_age<=receipt_age+1;
        end
        default: peer<=PEER_IDLE;
      endcase
    end
  end
