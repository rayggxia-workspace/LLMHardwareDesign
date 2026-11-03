// Issue151 W1: fixed SERVICE/WAIT program; slot2 verifies the stored frame.
// Input writes occur before start, through the same ordinary-S helper as RUN.
// This is the minimal MST program, not a complete model/product compiler.
module block_w1_mother_rom(
 input wire clk,reset,abort,
 input wire start_valid,output wire start_ready,
 output wire busy,output wire done_valid,input wire done_ready,
 output reg done_error,
 output wire service_valid,input wire service_ready,
 output wire [3:0] service_op,output wire [9:0] service_arg,
 input wire service_rsp_valid,output wire service_rsp_ready,
 input wire service_rsp_error
);
 localparam IDLE=0,RUN=1,DONE=2;
 localparam [1:0] SERVICE=2'b01,WAIT=2'b10,END_PROGRAM=2'b11;
 localparam [3:0] M_CLEAR=0,M_SCALE=1,INPUT_CHECK=2,LOAD=3,M_EXEC=4,
                  M_STORE=5,T_BEGIN=6,T_FILL=7,T_COMMIT=8,T_DRAIN=9;
 reg [1:0] state;
 reg [4:0] pc;
 // Constant instruction ROM: bits15:14 class,13:10 service,9:0 argument.
 // Low-address word is at the low end. All repeated work is counted locally.
 localparam [335:0] PROGRAM = {
  {END_PROGRAM,14'd0},
  {WAIT,14'd0},{SERVICE,T_DRAIN,10'd0},
  {WAIT,14'd0},{SERVICE,T_COMMIT,10'd0},
  {WAIT,14'd0},{SERVICE,T_FILL,10'd0},
  {WAIT,14'd0},{SERVICE,T_BEGIN,10'd0},
  {WAIT,14'd0},{SERVICE,M_STORE,10'd0},
  {WAIT,14'd0},{SERVICE,M_EXEC,10'd0},
  {WAIT,14'd0},{SERVICE,LOAD,10'd0},
  {WAIT,14'd0},{SERVICE,INPUT_CHECK,10'd0},
  {WAIT,14'd0},{SERVICE,M_SCALE,10'd0},
  {WAIT,14'd0},{SERVICE,M_CLEAR,10'd0}
 };
 wire [15:0] instruction = PROGRAM[16*pc+:16];
 wire [1:0] instruction_class=instruction[15:14];
 assign start_ready=!reset&&!abort&&state==IDLE;
 assign busy=!reset&&state!=IDLE;
 assign done_valid=!reset&&state==DONE;
 assign service_valid=!reset&&!abort&&state==RUN&&instruction_class==SERVICE;
 assign service_op=instruction[13:10];
 assign service_arg=instruction[9:0];
 assign service_rsp_ready=!reset&&!abort&&state==RUN&&instruction_class==WAIT;
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;pc<=0;done_error<=0;end
  else if(abort)begin
   // Abort is a coordinated reset operation on the child/leaf side.
   // An already accepted run receives one retained error completion.
   if(state==RUN)begin state<=DONE;done_error<=1;end
   else if(state==DONE&&done_ready)state<=IDLE;
  end else case(state)
   IDLE:if(start_valid&&start_ready)begin state<=RUN;pc<=0;done_error<=0;end
   RUN:case(instruction_class)
    SERVICE:if(service_valid&&service_ready)pc<=pc+1'b1;
    WAIT:if(service_rsp_valid&&service_rsp_ready)begin
     if(service_rsp_error)begin state<=DONE;done_error<=1;end
     else pc<=pc+1'b1;
    end
    END_PROGRAM:begin state<=DONE;done_error<=0;end
    default:begin state<=DONE;done_error<=1;end
   endcase
   DONE:if(done_valid&&done_ready)state<=IDLE;
   default:begin state<=DONE;done_error<=1;end
  endcase
 end
endmodule
