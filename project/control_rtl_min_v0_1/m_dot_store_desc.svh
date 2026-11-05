  localparam [31:0] M_DOT_STORE_ABI = 32'h00017901;
  localparam [31:0] M_DOT_STORE_TOPOLOGY = 32'h1764a201;
  localparam [15:0] M_DOT_STORE_OP = 16'h0080;

  // native0 holds A, B, destination as three 10-bit S word addresses.
  // A and B each reserve one aligned 64-byte feeder line. Destination is one word.
  function automatic m_dot_store_desc_ok(input [1023:0] desc);
    reg [9:0] a_word, b_word, dst_word;
    begin
      a_word=desc[512+:10];
      b_word=desc[522+:10];
      dst_word=desc[532+:10];
      m_dot_store_desc_ok =
        desc[0+:32]==32'd1 && desc[32+:32]=={16'd0,M_DOT_STORE_OP} &&
        desc[64+:32]==32'hffffffff && desc[96+:64]==0 &&
        desc[160+:48]==48'hffffffffffff && desc[208+:240]==0 &&
        desc[448+:32]==M_DOT_STORE_ABI && desc[480+:32]==0 &&
        desc[542+:482]==0 && a_word[1:0]==0 && b_word[1:0]==0 &&
        a_word[9:2]!=b_word[9:2] && dst_word[9:2]!=a_word[9:2] &&
        dst_word[9:2]!=b_word[9:2];
    end
  endfunction
