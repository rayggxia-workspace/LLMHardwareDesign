`timescale 1ns/1ps
// Candidate mutable LC PM: exactly 64x128 register bits (1024 bytes), ONE
// ordinary program port. It is not a zero-area ROM or an existing data S bank.
// BEGIN/WRITE/SEAL belong to boot configuration, not new LC opcodes.
module lc_program_store_1k #(
  parameter logic [31:0] ABI_ID=32'h02500002,CAPACITY_ID=32'h02510001
)(
  input logic clk,reset,
  input logic lc_idle,transport_drained,
  input logic cfg_valid,output logic cfg_ready,input logic [1:0] cfg_op,
  input logic [31:0] cfg_generation,cfg_abi,cfg_capacity,cfg_crc,
  input logic [15:0] cfg_bytes,input logic [13:0] cfg_address,
  input logic [127:0] cfg_data,
  output logic cfg_rsp_valid,input logic cfg_rsp_ready,
  output logic [7:0] cfg_status,output logic [31:0] cfg_actual_crc,
  output logic certified,boot_busy,output logic [31:0] generation,
  output logic [15:0] image_bytes,
  input logic pm_valid,output logic pm_ready,input logic [13:0] pm_address,
  output logic pm_rsp_valid,input logic pm_rsp_ready,
  output logic [127:0] pm_data,output logic pm_error
);
  logic [127:0] words[64];
  logic programming;
  logic [15:0] written;
  logic [9:0] scan_address;
  logic [31:0] scan_crc,expected_crc;
  wire [7:0] scan_byte=words[scan_address[9:4]][8*scan_address[3:0]+:8];
  function automatic logic [31:0] crc_byte(input logic [31:0] crc,input logic [7:0] value);
    logic [31:0] next_crc;
    next_crc=crc^{24'b0,value};
    for(integer b=0;b<8;b=b+1) next_crc=next_crc[0]?(next_crc>>1)^32'hedb88320:(next_crc>>1);
    return next_crc;
  endfunction
  wire [31:0] next_crc=crc_byte(scan_crc,scan_byte);
  wire header_ok=words[0][63:0]==64'h313041534943424c&&words[0][79:64]==2&&
      words[0][87:80]==1&&words[0][127:96]=={16'b0,image_bytes}&&
      words[1][31:0]==0&&words[4][63:32]==ABI_ID&&words[5][63:32]==CAPACITY_ID;
  assign cfg_ready=!reset&&!boot_busy&&(!cfg_rsp_valid||cfg_rsp_ready);
  // Config uses the same array and wins arbitration. A held runtime response
  // is never overwritten; a new boot is refused while that response exists.
  assign pm_ready=!reset&&!boot_busy&&!cfg_valid&&(!pm_rsp_valid||pm_rsp_ready);
  always_ff @(posedge clk) begin
    if(reset) begin
      cfg_rsp_valid<=0;cfg_status<=0;cfg_actual_crc<=0;certified<=0;boot_busy<=0;generation<=0;
      image_bytes<=0;programming<=0;written<=0;scan_address<=0;scan_crc<=0;expected_crc<=0;
      pm_rsp_valid<=0;pm_data<=0;pm_error<=0;
    end else begin
      if(cfg_rsp_valid&&cfg_rsp_ready) cfg_rsp_valid<=0;
      if(pm_rsp_valid&&pm_rsp_ready) pm_rsp_valid<=0;
      if(pm_valid&&pm_ready) begin
        pm_rsp_valid<=1;
        if(!certified||pm_address[3:0]!=0||{2'b0,pm_address}>=image_bytes) begin pm_data<=0;pm_error<=1;end
        else begin pm_data<=words[pm_address[9:4]];pm_error<=0;end
      end
      if(cfg_valid&&cfg_ready) begin
        cfg_rsp_valid<=1;cfg_status<=0;
        if(!lc_idle||!transport_drained||pm_rsp_valid||(pm_valid&&pm_ready)) cfg_status<=5;
        else case(cfg_op)
          0:begin // BEGIN: revoke old certification and burn this generation.
            if(cfg_generation<=generation||cfg_bytes<128||cfg_bytes>1024||cfg_bytes[3:0]!=0||cfg_abi!=ABI_ID||cfg_capacity!=CAPACITY_ID)
              cfg_status<=2;
            else begin generation<=cfg_generation;image_bytes<=cfg_bytes;written<=0;programming<=1;certified<=0;end
          end
          1:begin // WRITE: exact sequential words, receipt after actual write.
            if(!programming||certified) cfg_status<=1;
            else if(cfg_generation!=generation||cfg_address[3:0]!=0||{2'b0,cfg_address}!=written||written>=image_bytes||cfg_address>=1024)
              cfg_status<=3;
            else begin words[cfg_address[9:4]]<=cfg_data;written<=written+16'd16;end
          end
          2:begin // SEAL: independently read every actual programmed byte.
            if(!programming||written!=image_bytes||cfg_generation!=generation) cfg_status<=1;
            else begin
              cfg_rsp_valid<=0;boot_busy<=1;scan_address<=0;scan_crc<=32'hffffffff;expected_crc<=cfg_crc;
            end
          end
          3:begin certified<=0;programming<=0;end
          default:cfg_status<=1;
        endcase
      end
      if(boot_busy) begin
        scan_crc<=next_crc;
        if({6'b0,scan_address}+16'd1==image_bytes) begin
          boot_busy<=0;cfg_rsp_valid<=1;cfg_actual_crc<=~next_crc;
          if((~next_crc)!=expected_crc) begin cfg_status<=4;certified<=0;end
          else if(!header_ok) begin cfg_status<=6;certified<=0;end
          else begin cfg_status<=0;certified<=1;programming<=0;end
        end else scan_address<=scan_address+1'b1;
      end
    end
  end
endmodule
