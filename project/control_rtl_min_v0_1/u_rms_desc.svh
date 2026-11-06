  localparam [31:0] U_RMS_ABI = 32'h00017904;
  localparam [31:0] U_RMS_TOPOLOGY = 32'h1764b201;
  localparam [7:0] U_BLOCK_TYPE = 8'd1;
  localparam [7:0] U_RMS_RESOURCE = 8'd1;
  localparam [15:0] U_RMS_STORE_OP = 16'h0084;
  localparam [31:0] U_RMS_MASK = 32'h26;

  function automatic u_rms_desc_ok(input [1023:0] desc);
    reg [9:0] src0, src1, dst, dst1;
    reg [3:0] count0, count1;
    begin
      src0=desc[512+:10]; src1=desc[522+:10]; dst=desc[532+:10];
      dst1=dst+10'd1;
      count0=desc[544+:4]; count1=desc[548+:4];
      u_rms_desc_ok = desc[0+:32]==32'h00010001 &&
        desc[32+:32]=={16'b0,U_RMS_STORE_OP} &&
        desc[64+:32]==32'hffffffff && desc[96+:64]==0 &&
        desc[160+:48]==48'hffffffffffff && desc[208+:240]==0 &&
        desc[448+:32]==U_RMS_ABI && desc[480+:32]==0 &&
        desc[542+:2]==0 && desc[552+:8]==0 && desc[576+:32]!=0 && desc[608+:416]==0 &&
        count0>=1 && count0<=8 && count1>=1 && count1<=8 &&
        dst!=10'd1023 && src0!=src1 && src0!=dst && src0!=dst1 && src1!=dst && src1!=dst1;
    end
  endfunction
