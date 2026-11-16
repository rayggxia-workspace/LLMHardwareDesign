`timescale 1ns/1ps
// ONE live scope; exactly128B parameter registers are the fetched storage.
// Two real64B requests share MC's ordinary per-channel descriptor/beat credits
// with W traffic. No descriptor-response FIFO and no host side-load shortcut.
// CRC is verified here; a typed provider decoder must validate these SAME
// registers before executing. A CRC pass alone is not typed admission.
module lc_scope_fetch128(
  input logic clk,reset,
  input logic init_valid,output logic init_ready,
  input logic [31:0] init_generation,input logic transport_drained,
  input logic start_valid,output logic start_ready,
  input logic [127:0] start_owner,input logic [31:0] start_ticket,
  input logic [63:0] start_reference,input logic [15:0] start_bytes,
  input logic cancel_valid,input logic [127:0] cancel_owner,input logic [31:0] cancel_ticket,
  input logic release_valid,output logic release_ready,
  input logic [127:0] release_owner,input logic [31:0] release_ticket,
  output logic fetch_valid,input logic fetch_ready,
  output logic [7:0] fetch_status,
  output logic [127:0] fetch_owner,output logic [31:0] fetch_ticket,
  output logic [1023:0] descriptor_data,
  output logic mc_req_valid,input logic mc_req_ready,
  output logic [63:0] mc_req_address,output logic [31:0] mc_req_tag,
  output logic mc_req_channel,output logic [4:0] mc_req_record_beats,
  output logic mc_close_valid,input logic mc_close_ready,
  output logic [31:0] mc_close_tag_base,
  input logic mc_rsp_valid,output logic mc_rsp_ready,
  input logic [31:0] mc_rsp_tag,input logic [511:0] mc_rsp_data,
  output logic busy,cancelled,output logic [1:0] outstanding_beats,
  output logic [1:0] confirmed_beats,
  output logic [31:0] protocol_fault_cycles
);
  typedef enum logic [1:0] {IDLE,FETCH,CRC,DONE} state_t;
  state_t state;
  logic configured,delivered,offered,held_half,close_sent;
  logic [31:0] generation;
  logic [30:0] serial_counter,serial;
  logic [63:0] reference;
  logic [1:0] issued,received;
  logic [6:0] scan_address;
  logic [31:0] scan_crc;
  wire [7:0] scan_byte=descriptor_data[8*scan_address+:8];
  wire selected_half=offered?held_half:issued[0];
  wire cancel_match=cancel_valid&&busy&&cancel_owner==fetch_owner&&cancel_ticket==fetch_ticket;
  wire stop_now=cancelled||cancel_match;
  wire response_good=busy&&mc_rsp_tag[31:1]==serial&&issued[mc_rsp_tag[0]]&&!received[mc_rsp_tag[0]];
  wire [1:0] response_mask=(mc_rsp_valid&&mc_rsp_ready&&response_good)?(2'b01<<mc_rsp_tag[0]):2'b0;
  wire request_fire=mc_req_valid&&mc_req_ready;
  wire [1:0] next_issued=issued|(request_fire?(2'b01<<selected_half):2'b0);
  wire [1:0] next_received=received|response_mask;
  wire release_match=release_owner==fetch_owner&&release_ticket==fetch_ticket;
  function automatic logic [31:0] crc_byte(input logic [31:0] crc,input logic [7:0] value);
    logic [31:0] c;
    c=crc^{24'b0,value};
    for(integer b=0;b<8;b=b+1)c=c[0]?(c>>1)^32'hedb88320:(c>>1);
    return c;
  endfunction
  wire [31:0] next_crc=crc_byte(scan_crc,scan_byte);
  assign busy=state!=IDLE;
  assign init_ready=!reset&&state==IDLE&&transport_drained&&init_generation>generation;
  assign start_ready=!reset&&configured&&state==IDLE&&!init_valid&&serial_counter!=31'h7fffffff;
  assign fetch_valid=!reset&&state==DONE&&!delivered;
  assign release_ready=!reset&&state==DONE&&delivered&&release_match;
  assign mc_req_valid=!reset&&state==FETCH&&issued!=2'b11&&(!stop_now||offered);
  assign mc_req_address=reference+(selected_half?64'd64:64'd0);
  assign mc_req_tag={serial,selected_half};
  assign mc_req_channel=reference[11];
  assign mc_req_record_beats=5'd2;
  // Partial cancelled descriptor: no more source offers, but the accepted
  // beats still drain. ready means the global descriptor table REALLY
  // registered this close, not just queued an unbounded future operation.
  assign mc_close_valid=!reset&&state==FETCH&&stop_now&&!offered&&!mc_req_valid&&issued!=0&&issued!=2'b11&&!close_sent;
  assign mc_close_tag_base={serial,1'b0};
  assign mc_rsp_ready=!reset;
  assign outstanding_beats={1'b0,(issued[0]&&!received[0])}+{1'b0,(issued[1]&&!received[1])};
  assign confirmed_beats={1'b0,received[0]}+{1'b0,received[1]};
  always_ff @(posedge clk) begin
    if(reset) begin
      state<=IDLE;configured<=0;generation<=0;serial_counter<=0;serial<=0;delivered<=0;
      offered<=0;held_half<=0;close_sent<=0;reference<=0;issued<=0;received<=0;
      scan_address<=0;scan_crc<=0;fetch_status<=0;fetch_owner<=0;fetch_ticket<=0;
      descriptor_data<=0;cancelled<=0;protocol_fault_cycles<=0;
    end else begin
      if((mc_rsp_valid&&!response_good)||(cancel_valid&&!cancel_match)||(release_valid&&!release_ready)||
         (init_valid&&!init_ready)) protocol_fault_cycles<=protocol_fault_cycles+1'b1;
      if(init_valid&&init_ready)begin configured<=1;generation<=init_generation;serial_counter<=0;end
      if(start_valid&&start_ready)begin
        fetch_owner<=start_owner;fetch_ticket<=start_ticket;reference<=start_reference;
        serial_counter<=serial_counter+1'b1;serial<=serial_counter+1'b1;
        issued<=0;received<=0;offered<=0;close_sent<=0;delivered<=0;cancelled<=0;scan_address<=0;scan_crc<=32'hffffffff;
        if(start_bytes!=128||start_reference[6:0]!=0||start_reference>64'hffffffffffffff80||start_owner==0)begin state<=DONE;fetch_status<=1;end
        else begin state<=FETCH;fetch_status<=0;end
      end
      if(cancel_match) cancelled<=1;
      if(mc_req_valid&&!mc_req_ready)begin offered<=1;held_half<=selected_half;end
      if(request_fire)begin issued<=next_issued;offered<=0;end
      if(mc_close_valid&&mc_close_ready)close_sent<=1;
      if(mc_rsp_valid&&response_good)begin
        received<=next_received;
        if(!stop_now)descriptor_data[512*mc_rsp_tag[0]+:512]<=mc_rsp_data;
      end
      if(state==FETCH)begin
        if(stop_now&&next_issued==next_received&&(!offered||request_fire)&&
           (next_issued==0||next_issued==2'b11||close_sent||(mc_close_valid&&mc_close_ready)))begin state<=DONE;fetch_status<=3;end
        else if(!stop_now&&next_received==2'b11)begin state<=CRC;scan_address<=0;scan_crc<=32'hffffffff;end
      end
      if(state==CRC)begin
        if(stop_now)begin state<=DONE;fetch_status<=3;end
        else begin
          scan_crc<=next_crc;
          // Bytes124..127 carry this entry's CRC32; they are not included
          // in the CRC. Deployment table identity is bound separately by SHA.
          if(scan_address==123)begin state<=DONE;fetch_status<=((~next_crc)==descriptor_data[1023:992])?8'd0:8'd2;end
          else scan_address<=scan_address+1'b1;
        end
      end
      if(fetch_valid&&fetch_ready)delivered<=1;
      if(release_valid&&release_ready)state<=IDLE;
    end
  end
endmodule
