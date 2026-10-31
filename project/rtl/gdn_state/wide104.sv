// Exact I64 by S16/U16 magnitude lowering through ONE external S32 service.
module wide104(input wire clk,reset,req,cancel,input wire signed [63:0] a,input wire signed [31:0] b,
 output wire ready,busy,valid,input wire take,output wire signed [63:0] value,output reg error,
 output wire mreq,output wire signed [31:0] ma,mb,input wire mready,mvalid,output wire mtake,input wire signed [63:0] my);
 localparam IDLE=0,REQUEST=1,WAIT=2,ADD=3,DONE=4;reg [2:0] state;reg [63:0] magnitude,acc,partial;reg [15:0] factor_magnitude;reg negative,stop;reg [1:0] digit;
 wire [5:0] sh=digit==0?0:digit==1?31:62;wire [63:0] term=partial<<sh;
 assign ready=state==IDLE;assign busy=state!=IDLE;assign valid=state==DONE;assign value=negative?-$signed(acc):$signed(acc);
 assign mreq=state==REQUEST&&!cancel&&!stop;assign ma=digit==0?{1'b0,magnitude[30:0]}:digit==1?{1'b0,magnitude[61:31]}:{31'b0,magnitude[62]};assign mb={16'b0,factor_magnitude};assign mtake=state==WAIT;
 always @(posedge clk)begin
 if(reset)begin state<=IDLE;magnitude<=0;acc<=0;partial<=0;factor_magnitude<=0;negative<=0;stop<=0;digit<=0;error<=0;end
 else if(cancel&&state!=IDLE&&state!=DONE)begin stop<=1;error<=1;if(state!=WAIT||mvalid)state<=DONE;end
 else if(stop&&state!=DONE)begin if(state!=WAIT||mvalid)state<=DONE;end
 else case(state)
 IDLE:if(req)begin magnitude<=a[63]?-a:a;factor_magnitude<=b[31]?-b:b;negative<=a[63]^b[31];acc<=0;digit<=0;stop<=0;error<=0;
 if(a==64'sh8000000000000000||b>32'sd32768||b< -32'sd32768)begin error<=1;state<=DONE;end else state<=REQUEST;end
 REQUEST:if(mready)state<=WAIT;
 WAIT:if(mvalid)begin partial<=my;state<=ADD;end
 ADD:if(partial>(64'h7fffffffffffffff>>sh)||acc>64'h7fffffffffffffff-term)begin error<=1;state<=DONE;end
 else begin acc<=acc+term;if(digit==2)state<=DONE;else begin digit<=digit+1;state<=REQUEST;end end
 DONE:if(take)begin state<=IDLE;stop<=0;end
 default:state<=IDLE;
 endcase end
endmodule
