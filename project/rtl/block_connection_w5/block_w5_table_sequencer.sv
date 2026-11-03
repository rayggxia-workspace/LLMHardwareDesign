// Issue151 H2: fixed hardware sequencer for the linear H1 A/F table slice.
// ROM and metadata are permanent product bindings, not a host program loader.
// Services must hold completion until ready and clear outstanding work on
// cohort_abort. No claim of isolation from an uncoordinated late response.
module block_w5_table_sequencer(
 input wire clk,reset,abort,
 input wire job_valid,output wire job_ready,input wire [31:0] job_generation,
 output wire busy,output wire done_valid,input wire done_ready,
 output wire done_error,output wire [31:0] done_generation,
 output reg cohort_abort,
 output wire rom_req_valid,input wire rom_req_ready,output wire [7:0] rom_req_addr,
 input wire rom_rsp_valid,output wire rom_rsp_ready,input wire [127:0] rom_rsp_data,input wire rom_rsp_error,
 output wire [4:0] meta_addr,input wire [511:0] meta_data,
 output wire svc_valid,input wire svc_ready,output wire [127:0] svc_record,
 output reg [9:0] svc_a_base,svc_b_base,
 input wire svc_done_valid,output wire svc_done_ready,input wire svc_done_error
);
 localparam [2:0] IDLE=0,FETCH_REQ=1,FETCH_RSP=2,DECODE=3,SEND=4,WAIT_SVC=5,DONE=6;
 localparam [7:0] ALLOC=1,IMPORT=2,WAIT_STORED=3,ARM=4,START=5,LOAD=6,
  WAIT_INPUT=7,PARAM=8,WAIT_PARAM=9,WAIT_SEALED=10,STORE=11,CLOSE=12,
  WAIT_RELEASE=13,WAIT_DONE=14,FREE=15,IF_OP=16,SETOUT=17,HALT=18,
  EXPORT=19,WAIT_HOST_STORED=20,CLOSE_OUTPUT=21;
 localparam [2:0] P_NONE=0,P_IMPORT=1,P_INPUT=2,P_PARAM=3,P_OUTPUT=4,P_HOST=5;
 reg [2:0] state,pending_kind;
 reg [7:0] pc;
 reg [8:0] steps;
 reg [127:0] instruction;
 reg [31:0] generation_hold;
 reg error_hold;
 reg [16:0] allocated,live;
 reg [3:0] slot_used;
 reg [1:0] object_slot[0:16],object_valid[0:16],object_kernel[0:16];
 reg [15:0] refs[0:16],producer[0:16],object_parameter[0:16];
 reg [4:0] object_source[0:16];
 reg [16:0] object_is_input;
 reg active,started,input_stored,param_stored,sealed,stored,closed,released;
 reg [1:0] active_island;
 reg active_row;
 reg [4:0] active_dest,active_source,pending_object,output_object;
 reg [1:0] pending_slot;
 reg [15:0] active_parameter;
 reg output_selected,export_started,host_stored,output_closed;
 wire [7:0] op=instruction[7:0],flags=instruction[15:8];
 wire [15:0] a=instruction[31:16],b=instruction[47:32],c=instruction[63:48];
 wire [31:0] imm=instruction[95:64];
 wire [15:0] next_pc=instruction[111:96],aux=instruction[127:112];
 reg reserved_ok,guard_ok,internal_op;
 reg free_found;
 reg [1:0] free_slot;
 integer k;
 assign job_ready=state==IDLE&&!reset&&!abort&&!cohort_abort;
 assign busy=state!=IDLE;
 assign done_valid=state==DONE&&!reset;
 assign done_error=error_hold;
 assign done_generation=generation_hold;
 assign rom_req_valid=state==FETCH_REQ&&!reset&&!abort;
 assign rom_req_addr=pc;
 assign rom_rsp_ready=state==FETCH_RSP&&!reset&&!abort;
 assign meta_addr=a<17 ? a[4:0] : 5'd0;
 assign svc_valid=state==SEND&&!reset&&!abort;
 assign svc_record=instruction;
 assign svc_done_ready=state==WAIT_SVC&&!reset&&!abort;
 always @* begin
  svc_a_base=0;svc_b_base=0;
  if(a<17&&(op==IMPORT||op==WAIT_STORED||op==LOAD||op==WAIT_INPUT||
              op==EXPORT||op==WAIT_HOST_STORED||op==CLOSE_OUTPUT))
   svc_a_base={object_slot[a[4:0]],8'd0};
  if(b<17&&(op==ARM||op==STORE))svc_b_base={object_slot[b[4:0]],8'd0};
 end
 always @* begin
  free_found=0;free_slot=0;
  for(integer j=3;j>=0;j=j-1)if(!slot_used[j])begin free_found=1;free_slot=j[1:0];end
  reserved_ok=flags==0;
  case(op)
   ALLOC,WAIT_STORED,START,WAIT_PARAM,WAIT_SEALED,CLOSE,WAIT_RELEASE,
   WAIT_DONE,FREE,SETOUT,WAIT_HOST_STORED,CLOSE_OUTPUT:
    reserved_ok=reserved_ok&&b==0&&c==0&&imm==0&&aux==0;
   IMPORT,EXPORT:reserved_ok=reserved_ok&&b==0&&c==0&&aux==0;
   ARM:reserved_ok=reserved_ok&&aux<16;
   LOAD,STORE,PARAM:reserved_ok=reserved_ok&&aux==0;
   WAIT_INPUT:reserved_ok=reserved_ok&&imm==0&&aux==0;
   HALT:reserved_ok=reserved_ok&&a==0&&b==0&&c==0&&imm==0&&aux==0&&next_pc==0;
   default:reserved_ok=0;
  endcase
  // This first slice accepts a linear program only. IF and cycles are errors.
  if(op!=HALT)reserved_ok=reserved_ok&&pc!=255&&next_pc=={8'd0,pc}+16'd1;
  guard_ok=0;internal_op=0;
  case(op)
   ALLOC:begin
    internal_op=1;
    if(a<17)guard_ok=!allocated[a[4:0]]&&free_found&&pending_kind==P_NONE&&
     meta_data[15:0]==a&&meta_data[31:16]==1&&meta_data[63:32]==4096&&
     meta_data[111:96]==2&&meta_data[127:112]==1024&&meta_data[135:128]==16&&
     meta_data[143:136]==10&&meta_data[151:144]==1&&meta_data[159:152]==1&&
     meta_data[175:160]<=16&&meta_data[223:192]==0&&meta_data[511:480]==0&&
     ((a==0&&meta_data[95:64]==1&&meta_data[191:176]==65535)||
      (a!=0&&meta_data[95:64]==0&&meta_data[191:176]>=1&&meta_data[191:176]<=16));
   end
   IMPORT:if(a<17)guard_ok=!active&&pending_kind==P_NONE&&live[a[4:0]]&&
     object_is_input[a[4:0]]&&object_valid[a[4:0]]==0&&imm==256;
   WAIT_STORED:if(a<17)guard_ok=live[a[4:0]]&&pending_object==a&&
     object_slot[a[4:0]]==pending_slot&&(pending_kind==P_IMPORT||pending_kind==P_OUTPUT);
   ARM:if(b<17)guard_ok=!active&&pending_kind==P_NONE&&live[b[4:0]]&&
     !object_is_input[b[4:0]]&&(a==1||a==2)&&c<2&&(a!=1||c==0)&&
     !object_valid[b[4:0]][c[0]]&&imm==({15'd0,producer[b[4:0]],1'b0}+{16'd0,c})&&
     ((c==0&&object_valid[b[4:0]]==0)||
      (a==2&&c==1&&object_valid[b[4:0]]==1&&object_kernel[b[4:0]]==2&&object_parameter[b[4:0]]==aux));
   LOAD:if(a<17)guard_ok=active&&!started&&!input_stored&&pending_kind==P_NONE&&
     live[a[4:0]]&&object_valid[a[4:0]]==3&&b=={14'd0,active_island}&&c=={15'd0,active_row}&&
     imm==(active_island==1?256:128)&&
     (active_island!=2||!active_row||object_source[active_dest]==a);
   WAIT_INPUT:guard_ok=active&&pending_kind==P_INPUT&&pending_object==a&&
     b=={14'd0,active_island}&&c=={15'd0,active_row};
   PARAM:guard_ok=active&&input_stored&&!param_stored&&pending_kind==P_NONE&&
     a==active_parameter&&b=={14'd0,active_island}&&c=={15'd0,active_row}&&imm==(active_island==1?192:128);
   WAIT_PARAM:guard_ok=active&&pending_kind==P_PARAM&&a=={14'd0,active_island}&&
     (active_island==2&&!active_row||refs[active_source]!=0);
   START:guard_ok=active&&a=={14'd0,active_island}&&input_stored&&param_stored&&!started&&pending_kind==P_NONE;
   WAIT_SEALED:guard_ok=active&&a=={14'd0,active_island}&&started&&param_stored&&!sealed&&pending_kind==P_NONE;
   STORE:if(b<17)guard_ok=active&&a=={14'd0,active_island}&&sealed&&!stored&&pending_kind==P_NONE&&
     b=={11'd0,active_dest}&&c=={15'd0,active_row}&&live[b[4:0]]&&imm==(active_island==1?256:128);
   CLOSE:guard_ok=active&&a=={14'd0,active_island}&&stored&&!closed&&pending_kind==P_NONE;
   WAIT_RELEASE:guard_ok=active&&a=={14'd0,active_island}&&closed&&!released&&pending_kind==P_NONE;
   WAIT_DONE:guard_ok=active&&a=={14'd0,active_island}&&released&&pending_kind==P_NONE;
   FREE:begin
    internal_op=1;
    if(a<17)guard_ok=live[a[4:0]]&&refs[a[4:0]]==0&&
     !(output_selected&&output_object==a)&&!(pending_kind!=P_NONE&&pending_object==a);
   end
   SETOUT:begin
    internal_op=1;
    if(a<17)guard_ok=!active&&pending_kind==P_NONE&&!output_selected&&live[a[4:0]]&&object_valid[a[4:0]]==3;
   end
   EXPORT:if(a<17)guard_ok=output_selected&&output_object==a&&!export_started&&
     live[a[4:0]]&&object_valid[a[4:0]]==3&&!active&&pending_kind==P_NONE&&imm==256;
   WAIT_HOST_STORED:guard_ok=pending_kind==P_HOST&&output_selected&&output_object==a;
   CLOSE_OUTPUT:guard_ok=output_selected&&output_object==a&&host_stored&&!output_closed&&pending_kind==P_NONE&&refs[output_object]==0;
   HALT:begin
    internal_op=1;guard_ok=!active&&pending_kind==P_NONE&&output_closed&&slot_used==0&&live==0;
    for(integer j=0;j<17;j=j+1)if(refs[j]!=0)guard_ok=0;
   end
   default:guard_ok=0;
  endcase
 end
 task clear_context;
  begin
   allocated<=0;live<=0;slot_used<=0;object_is_input<=0;pending_kind<=P_NONE;
   active<=0;started<=0;input_stored<=0;param_stored<=0;sealed<=0;stored<=0;closed<=0;released<=0;
   active_island<=0;active_row<=0;active_dest<=0;active_source<=0;active_parameter<=0;
   pending_object<=0;pending_slot<=0;output_object<=0;
   output_selected<=0;export_started<=0;host_stored<=0;output_closed<=0;
   for(k=0;k<17;k=k+1)begin
    object_slot[k]<=0;object_valid[k]<=0;refs[k]<=0;producer[k]<=0;
    object_kernel[k]<=0;object_parameter[k]<=0;object_source[k]<=0;
   end
  end
 endtask
 task fail_job;
  begin error_hold<=1;cohort_abort<=1;state<=DONE;end
 endtask
 task advance;
  begin pc<=next_pc[7:0];state<=FETCH_REQ;end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;pc<=0;steps<=0;instruction<=0;generation_hold<=0;error_hold<=0;cohort_abort<=0;
   clear_context();
  end else begin
   cohort_abort<=0;
   if(state==DONE)begin
    if(done_ready)begin state<=IDLE;clear_context();end
   end else if(abort&&state!=IDLE)fail_job();
   else case(state)
    IDLE:if(job_valid&&job_ready)begin
     clear_context();generation_hold<=job_generation;error_hold<=0;pc<=0;steps<=0;state<=FETCH_REQ;
    end
    FETCH_REQ:if(rom_req_valid&&rom_req_ready)state<=FETCH_RSP;
    FETCH_RSP:if(rom_rsp_valid&&rom_rsp_ready)begin
     if(rom_rsp_error)fail_job();
     else begin instruction<=rom_rsp_data;state<=DECODE;end
    end
    DECODE:begin
     if(!reserved_ok||!guard_ok||steps>=256)fail_job();
     else begin
      steps<=steps+1'b1;
      if(!internal_op)state<=SEND;
      else case(op)
       ALLOC:begin
        allocated[a[4:0]]<=1;live[a[4:0]]<=1;object_slot[a[4:0]]<=free_slot;slot_used[free_slot]<=1;
        refs[a[4:0]]<=meta_data[175:160];producer[a[4:0]]<=meta_data[191:176];
        object_is_input[a[4:0]]<=meta_data[64];object_valid[a[4:0]]<=0;advance();
       end
       FREE:begin live[a[4:0]]<=0;slot_used[object_slot[a[4:0]]]<=0;object_valid[a[4:0]]<=0;advance();end
       SETOUT:begin output_selected<=1;output_object<=a[4:0];advance();end
       HALT:begin error_hold<=0;state<=DONE;end
       default:fail_job();
      endcase
     end
    end
    SEND:if(svc_valid&&svc_ready)state<=WAIT_SVC;
    WAIT_SVC:if(svc_done_valid&&svc_done_ready)begin
     if(svc_done_error)fail_job();
     else begin
      case(op)
       IMPORT:begin pending_kind<=P_IMPORT;pending_object<=a[4:0];pending_slot<=object_slot[a[4:0]];end
       WAIT_STORED:begin
        if(pending_kind==P_IMPORT)object_valid[a[4:0]]<=3;
        else begin object_valid[a[4:0]]<=active_island==1?2'b11:(active_row?2'b11:2'b01);stored<=1;end
        pending_kind<=P_NONE;
       end
       ARM:begin
        active<=1;active_island<=a[1:0];active_dest<=b[4:0];active_row<=c[0];active_parameter<=aux;
        started<=0;input_stored<=0;param_stored<=0;sealed<=0;stored<=0;closed<=0;released<=0;
        object_kernel[b[4:0]]<=a[1:0];object_parameter[b[4:0]]<=aux;
       end
       LOAD:begin
        pending_kind<=P_INPUT;pending_object<=a[4:0];pending_slot<=object_slot[a[4:0]];
        active_source<=a[4:0];object_source[active_dest]<=a[4:0];
       end
       WAIT_INPUT:begin input_stored<=1;pending_kind<=P_NONE;end
       PARAM:pending_kind<=P_PARAM;
       WAIT_PARAM:begin
        param_stored<=1;pending_kind<=P_NONE;
        if(active_island==1||active_row)refs[active_source]<=refs[active_source]-1'b1;
       end
       START:started<=1;
       WAIT_SEALED:sealed<=1;
       STORE:begin pending_kind<=P_OUTPUT;pending_object<=b[4:0];pending_slot<=object_slot[b[4:0]];end
       CLOSE:closed<=1;
       WAIT_RELEASE:released<=1;
       WAIT_DONE:active<=0;
       EXPORT:begin pending_kind<=P_HOST;pending_object<=a[4:0];export_started<=1;end
       WAIT_HOST_STORED:begin host_stored<=1;pending_kind<=P_NONE;end
       CLOSE_OUTPUT:begin
        output_closed<=1;live[output_object]<=0;slot_used[object_slot[output_object]]<=0;object_valid[output_object]<=0;
       end
       default:begin end
      endcase
      advance();
     end
    end
    default:fail_job();
   endcase
  end
 end
endmodule
