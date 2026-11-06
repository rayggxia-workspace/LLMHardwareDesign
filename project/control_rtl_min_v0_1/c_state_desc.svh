  localparam [31:0] C_STATE_ABI = 32'h00017906;
  localparam [31:0] C_STATE_TOPOLOGY = 32'h1764c201;
  localparam [7:0] C_BLOCK_TYPE = 8'd2;
  localparam [2:0] C_STATE_RESOURCE = 3'd4;
  localparam [15:0] C_STATE_OP = 16'h0086;
  localparam [31:0] C_STATE_MASK = 32'h3c;

  function automatic c_state_desc_ok(input [1023:0] desc);
    begin
      c_state_desc_ok=desc[0+:32]==32'h00040001 && desc[32+:32]=={16'b0,C_STATE_OP} &&
        desc[64+:32]==32'hffffffff && desc[96+:64]==0 &&
        desc[160+:48]==48'hffffffffffff && desc[208+:240]==0 &&
        desc[448+:32]==C_STATE_ABI && desc[480+:32]==0 &&
        desc[522+:22]==0 && desc[544+:32]!=0 && !desc[575] && desc[576+:448]==0;
    end
  endfunction
