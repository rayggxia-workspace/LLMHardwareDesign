module tb_weight_credits;
localparam KEY_W=128;
reg  clk=0;
reg  reset=0;
reg  alloc_valid=0;
wire  alloc_ready;
reg [KEY_W-1:0] alloc_key=0;
reg [31:0] alloc_record=0;
reg  alloc_head16=0;
reg [3:0] alloc_n=0;
wire  alloc_ack_valid;
reg  alloc_ack_ready=0;
wire  alloc_ack_error;
wire [1:0] alloc_ack_bank;
wire [15:0] alloc_ack_generation;
wire [KEY_W-1:0] alloc_ack_key;
wire [31:0] alloc_ack_record;
reg  issue_valid=0;
wire  issue_ready;
reg [1:0] issue_bank=0;
reg [15:0] issue_generation=0;
reg [KEY_W-1:0] issue_key=0;
reg [31:0] issue_record=0;
reg [4:0] issue_beat=0;
reg  fill_valid=0;
wire  fill_ready;
reg [1:0] fill_bank=0;
reg [15:0] fill_generation=0;
reg [KEY_W-1:0] fill_key=0;
reg [31:0] fill_record=0;
reg [4:0] fill_beat=0;
reg  fill_last=0;
reg [511:0] fill_data=0;
wire  fill_ack_valid;
reg  fill_ack_ready=0;
wire [1:0] fill_ack_bank;
wire [15:0] fill_ack_generation;
wire [KEY_W-1:0] fill_ack_key;
wire [31:0] fill_ack_record;
wire  fill_ack_error;
reg  start_valid=0;
wire  start_ready;
reg [1:0] start_bank=0;
reg [15:0] start_generation=0;
reg [KEY_W-1:0] start_key=0;
reg [31:0] start_record=0;
reg [15:0] start_use=0;
reg [31:0] start_raw_tag=0;
wire  start_accepted;
wire  start_head16;
wire [3:0] start_n;
wire  w_valid;
reg  w_ready=0;
wire [KEY_W-1:0] w_key;
wire [31:0] w_record;
wire [1:0] w_bank;
wire [15:0] w_generation;
wire [15:0] w_use;
wire [31:0] w_raw_tag;
wire [7:0] w_group_k;
wire [7:0] w_offset;
wire [3:0] w_n;
wire  w_first;
wire  w_last;
wire  w_record_last;
wire [2:0] w_group_index;
wire [1023:0] w_data;
wire [127:0] w_scale;
reg  consumed_valid=0;
wire  consumed_ready;
reg [1:0] consumed_bank=0;
reg [15:0] consumed_generation=0;
reg [KEY_W-1:0] consumed_key=0;
reg [31:0] consumed_record=0;
reg [15:0] consumed_use=0;
reg  cancel_valid=0;
wire  cancel_ready;
reg [1:0] cancel_bank=0;
reg [15:0] cancel_generation=0;
reg [KEY_W-1:0] cancel_key=0;
reg [31:0] cancel_record=0;
wire  cancel_accepted;
reg  drain_valid=0;
wire  drain_ready;
reg [1:0] drain_bank=0;
reg [15:0] drain_generation=0;
reg [KEY_W-1:0] drain_key=0;
reg [31:0] drain_record=0;
wire  drain_done_valid;
reg  drain_done_ready=0;
wire [1:0] drain_done_bank;
wire [15:0] drain_done_generation;
wire [KEY_W-1:0] drain_done_key;
wire [31:0] drain_done_record;
wire  fault_valid;
reg  fault_ready=0;
wire [3:0] fault_op;
wire [1:0] fault_bank;
wire [15:0] fault_generation;
wire [KEY_W-1:0] fault_key;
wire [31:0] fault_record;
wire [6:0] outstanding;
wire [3:0] free_mask;
wire [3:0] ready_mask;
always #5 clk=~clk;
weight_records dut(.clk,.reset,.alloc_valid,.alloc_ready,.alloc_key,.alloc_record,.alloc_head16,.alloc_n,.alloc_ack_valid,.alloc_ack_ready,.alloc_ack_error,.alloc_ack_bank,.alloc_ack_generation,.alloc_ack_key,.alloc_ack_record,.issue_valid,.issue_ready,.issue_bank,.issue_generation,.issue_key,.issue_record,.issue_beat,.fill_valid,.fill_ready,.fill_bank,.fill_generation,.fill_key,.fill_record,.fill_beat,.fill_last,.fill_data,.fill_ack_valid,.fill_ack_ready,.fill_ack_bank,.fill_ack_generation,.fill_ack_key,.fill_ack_record,.fill_ack_error,.start_valid,.start_ready,.start_bank,.start_generation,.start_key,.start_record,.start_use,.start_raw_tag,.start_accepted,.start_head16,.start_n,.w_valid,.w_ready,.w_key,.w_record,.w_bank,.w_generation,.w_use,.w_raw_tag,.w_group_k,.w_offset,.w_n,.w_first,.w_last,.w_record_last,.w_group_index,.w_data,.w_scale,.consumed_valid,.consumed_ready,.consumed_bank,.consumed_generation,.consumed_key,.consumed_record,.consumed_use,.cancel_valid,.cancel_ready,.cancel_bank,.cancel_generation,.cancel_key,.cancel_record,.cancel_accepted,.drain_valid,.drain_ready,.drain_bank,.drain_generation,.drain_key,.drain_record,.drain_done_valid,.drain_done_ready,.drain_done_bank,.drain_done_generation,.drain_done_key,.drain_done_record,.fault_valid,.fault_ready,.fault_op,.fault_bank,.fault_generation,.fault_key,.fault_record,.outstanding,.free_mask,.ready_mask);

integer peak=0;
always @(posedge clk) if(!reset)begin
 if(outstanding>peak)peak=outstanding;
 if(outstanding>32)$fatal(1,"credit overflow");
 if(fault_valid)$fatal(1,"unexpected protocol fault %0d",fault_op);
end
task tick; @(posedge clk);#1;@(negedge clk);endtask
task issue_one(input integer n);
 issue_bank=n%4;issue_record=n%4;issue_generation=1;issue_key=1;issue_beat=n/4;issue_valid=1;
 #1;while(!issue_ready)tick();
 tick();issue_valid=0;
endtask
task fill_one(input integer n);
 fill_bank=n%4;fill_record=n%4;fill_generation=1;fill_key=1;fill_beat=n/4;fill_last=n/4==17;
 fill_data=n/4<16?{64{8'(n/4+1)}}:{32{16'h3c00}};
 fill_valid=1;#1;while(!fill_ready)tick();tick();fill_valid=0;
endtask
initial begin
 reset=1;repeat(3)tick();reset=0;
 alloc_ack_ready=1;fill_ack_ready=1;fault_ready=1;drain_done_ready=1;
 for(integer b=0;b<4;b++)begin
 alloc_valid=1;alloc_key=1;alloc_record=b;alloc_head16=1;alloc_n=8;
 tick();alloc_valid=0;
 if(!alloc_ack_valid||alloc_ack_error||alloc_ack_bank!=b||alloc_ack_generation!=1)$fatal(1,"alloc");
 tick();
 end
 for(integer n=0;n<32;n++)issue_one(n);
 if(outstanding!=32||ready_mask!=0)$fatal(1,"initial credit/visibility");
 issue_bank=0;issue_record=0;issue_generation=1;issue_key=1;issue_beat=8;issue_valid=1;
 repeat(4)begin #1;if(issue_ready)$fatal(1,"33rd request admitted");tick();end
 issue_valid=0;
 for(integer n=31;n>=0;n--)fill_one(n);
 for(integer n=32;n<64;n++)issue_one(n);
 for(integer n=63;n>=32;n--)fill_one(n);
 for(integer n=64;n<72;n++)issue_one(n);
 if(ready_mask!=0)$fatal(1,"partial record visible");
 for(integer n=71;n>=64;n--)fill_one(n);
 repeat(12)tick();
 if(outstanding!=0||ready_mask!=15||peak!=32)$fatal(1,"completion");
 for(integer b=0;b<4;b++)begin
 start_bank=b;start_record=b;start_generation=1;start_key=1;start_use=1;start_raw_tag=0;start_valid=1;
 #1;if(!start_accepted)$fatal(1,"start");tick();start_valid=0;
 for(integer k=0;k<8;k++)begin
 w_ready=0;repeat(2)begin
 #1;if(!w_valid||w_data!={{64{8'(2*k+2)}},{64{8'(2*k+1)}}}||w_scale!={8{16'h3c00}})$fatal(1,"reordered payload/backpressure");
 tick();end
 w_ready=1;tick();w_ready=0;
 end
 consumed_bank=b;consumed_record=b;consumed_generation=1;consumed_key=1;consumed_use=1;consumed_valid=1;tick();consumed_valid=0;
 end
 if(free_mask!=15||outstanding!=0)$fatal(1,"release");
 $display("PASS weight_records peak=32 records=4 returned=72 free=15 reordered/backpressured");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
