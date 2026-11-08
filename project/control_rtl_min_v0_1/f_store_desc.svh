  localparam [31:0] F_STORE_ABI = 32'h00017903;
  localparam [31:0] F_STORE_TOPOLOGY = 32'h1764f201;
  localparam [7:0] F_BLOCK_TYPE = 8'd3;
  localparam [7:0] F_STORE_RESOURCE = 8'd3;
  localparam [15:0] F_G_STORE_OP = 16'h0082, F_GE_STORE_OP = 16'h0083;
  localparam [31:0] F_G_STORE_MASK = 32'h28, F_GE_STORE_MASK = 32'h2c;

  function automatic f_store_desc_ok(input [1023:0] desc);
    reg [9:0] src_word, add_word, dst_word;
    reg use_add;
    begin
      src_word=desc[512+:10];
      add_word=desc[522+:10];
      dst_word=desc[532+:10];
      use_add=desc[32+:16]==F_GE_STORE_OP;
      f_store_desc_ok = desc[0+:32]==32'h00030001 &&
        (use_add || desc[32+:16]==F_G_STORE_OP) && desc[48+:16]==0 &&
        desc[64+:32]==32'hffffffff && desc[96+:64]==0 &&
        desc[160+:48]==48'hffffffffffff && desc[208+:240]==0 &&
        desc[448+:32]==F_STORE_ABI && desc[480+:32]==0 && desc[542+:482]==0 &&
        src_word!=dst_word && (use_add ? (src_word!=add_word && add_word!=dst_word) : add_word==0);
    end
  endfunction
