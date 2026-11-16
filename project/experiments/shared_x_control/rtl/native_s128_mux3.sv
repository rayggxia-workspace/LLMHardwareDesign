`timescale 1ns/1ps
// Copy-source read, copy-destination write, and A read share ONE ordinary
// S128 port. Two owner/tag records correspond to the unchanged S response
// capacity. There is no third data buffer or independent source read port.
module native_s128_mux3(
  input logic clk,reset,
  input logic [2:0] c_valid,c_write,
  input logic [29:0] c_address,
  input logic [383:0] c_data,
  input logic [95:0] c_tag,
  output logic [2:0] c_ready,c_response_valid,
  input logic [2:0] c_response_ready,
  output logic [127:0] c_response_data,
  output logic [95:0] c_response_tag,
  output logic req_valid,req_write,
  output logic [9:0] req_address,
  output logic [127:0] req_data,
  input logic req_ready,rsp_valid,
  output logic rsp_ready,
  input logic [127:0] rsp_data,
  output logic [1:0] owners_occupied
);
  logic [1:0] owner[2];
  logic [31:0] tag[2];
  logic head,tail,stalled,found,push,pop,space;
  logic [1:0] count,round_robin,selected,held_selection;
  assign owners_occupied=count;
  always_comb begin
    selected=round_robin;found=0;
    for(integer step=0;step<3;step=step+1)
      if(!found&&c_valid[(int'(round_robin)+step)%3]) begin
        selected=2'((int'(round_robin)+step)%3);found=1;
      end
    if(stalled) selected=held_selection;
  end
  assign c_response_valid=(!reset&&count!=0&&rsp_valid)?(3'b001<<owner[head]):3'b0;
  assign c_response_tag={3{tag[head]}};
  assign c_response_data=rsp_data;
  assign rsp_ready=!reset&&count!=0&&c_response_ready[owner[head]];
  assign pop=rsp_valid&&rsp_ready;
  assign space=count<2||pop;
  assign req_valid=!reset&&space&&c_valid[selected];
  assign req_write=c_write[selected];
  assign req_address=c_address[10*selected+:10];
  assign req_data=c_data[128*selected+:128];
  assign c_ready=(!reset&&space&&req_ready)?(3'b001<<selected):3'b0;
  assign push=req_valid&&req_ready;
  always_ff @(posedge clk) begin
    if(reset) begin
      head<=0;tail<=0;count<=0;round_robin<=0;stalled<=0;held_selection<=0;
      owner[0]<=0;owner[1]<=0;tag[0]<=0;tag[1]<=0;
    end else begin
`ifndef SYNTHESIS
      assert(count<=2) else $fatal(1,"S mux3 owner overflow");
      assert(!rsp_valid||count!=0) else $fatal(1,"S mux3 orphan response");
`endif
      if(req_valid&&!req_ready) begin stalled<=1;held_selection<=selected;end
      if(push) begin
        owner[tail]<=selected;tag[tail]<=c_tag[32*selected+:32];tail<=!tail;
        round_robin<=selected==2?2'd0:selected+1'b1;stalled<=0;
      end
      if(pop) head<=!head;
      case({push,pop})
        2'b10:count<=count+1'b1;
        2'b01:count<=count-1'b1;
        default:begin end
      endcase
    end
  end
endmodule
