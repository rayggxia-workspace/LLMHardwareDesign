  localparam [31:0] J_LEASE_ABI = 32'h00017905;
  localparam [31:0] J_LEASE_TOPOLOGY = 32'h1764e201;
  localparam [7:0] J_BLOCK_TYPE = 8'd4;
  localparam [2:0] J_LEASE_RESOURCE = 3'd6;
  localparam [15:0] J_LEASE_OP = 16'h0085;
  localparam [31:0] J_LEASE_MASK = 32'h64;

  function automatic j_lease_desc_ok(input [1023:0] desc);
    reg [9:0] input_word, add_word, scratch_word, dst_word;
    begin
      input_word=desc[512+:10]; add_word=desc[522+:10];
      scratch_word=desc[532+:10]; dst_word=desc[544+:10];
      j_lease_desc_ok=desc[0+:32]==32'h00060001 && desc[32+:32]=={16'b0,J_LEASE_OP} &&
        desc[64+:32]==32'hffffffff && desc[96+:64]==0 &&
        desc[160+:48]==48'hffffffffffff && desc[208+:240]==0 &&
        desc[448+:32]==J_LEASE_ABI && desc[480+:32]==0 &&
        desc[542+:2]==0 && desc[554+:470]==0 &&
        !input_word[0] && !add_word[0] && !scratch_word[0] && !dst_word[0] &&
        input_word!=add_word && input_word!=scratch_word && input_word!=dst_word &&
        add_word!=scratch_word && add_word!=dst_word && scratch_word!=dst_word;
    end
  endfunction
